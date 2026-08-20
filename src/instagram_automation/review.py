from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .answer_renderer import _sections, _top_section
from .paths import (IMAGE_DIR, MASTER_DIR, REPO_ROOT, REVIEW_DECISION_DIR,
                    REVIEW_PAYLOAD_DIR, REVIEW_RESULT_DIR, SOURCE_IMAGE_DIR,
                    require_file)
from .validation import validate

MAX_LENGTHS = {
    "question": 180,
    "choice": 80,
    "explanation": 500,
    "answer_hint": 240,
    "example": 240,
    "example_translation": 240,
    "instagram_caption": 2200,
    "question_guide_ja": 30,
    "threads_parent_text": 500,
    "threads_answer_text": 500,
}
REVIEW_LABELS = {"PASS", "REJECT"}


@dataclass(frozen=True)
class MachineCheckResult:
    content_id: str
    status: str
    reason: str | None
    item: dict | None

    def compact(self) -> dict:
        return {"content_id": self.content_id, "status": self.status, "reason": self.reason}


def _read_master(master_path: Path) -> dict:
    source = require_file(master_path)
    try:
        content = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(content, dict):
        raise ValueError("master JSON root must be an object")
    return content


def _check_length(value: object, limit: int, field: str) -> None:
    if isinstance(value, str) and len(value) > limit:
        raise ValueError(f"{field} exceeds {limit} characters")


def _check_lengths(content: dict) -> None:
    for field in ("question", "explanation", "answer_hint", "instagram_caption",
                  "question_guide_ja", "threads_parent_text", "threads_answer_text"):
        _check_length(content.get(field), MAX_LENGTHS[field], field)
    for index, choice in enumerate(content.get("choices", [])):
        _check_length(choice, MAX_LENGTHS["choice"], f"choices[{index}]")
    for index, example in enumerate(content.get("examples", [])):
        _check_length(example, MAX_LENGTHS["example"], f"examples[{index}]")
    for index, translation in enumerate(content.get("example_translations", [])):
        _check_length(translation, MAX_LENGTHS["example_translation"], f"example_translations[{index}]")


def _check_source_image(content: dict) -> str | None:
    if content["visual_required"] is False:
        return None
    value = content.get("problem_image_path")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("problem_image_path is required when visual_required is true")
    source = (REPO_ROOT / value).resolve()
    if source.parent != SOURCE_IMAGE_DIR.resolve():
        raise ValueError(f"problem image must be directly under {SOURCE_IMAGE_DIR}")
    if not source.is_file():
        raise ValueError(f"problem image not found: {value}")
    return source.relative_to(REPO_ROOT).as_posix()


def _check_rendered_image(content_id: str, role: str) -> None:
    path = IMAGE_DIR / f"{content_id}-{role}.png"
    if not path.is_file():
        raise ValueError(f"rendered {role} image not found")
    try:
        with Image.open(path) as image:
            if image.format != "PNG":
                raise ValueError(f"rendered {role} image must be PNG")
            if image.size != (1080, 1350):
                raise ValueError(f"rendered {role} image must be 1080x1350")
            if image.mode != "RGB":
                raise ValueError(f"rendered {role} image must be RGB")
    except OSError as exc:
        raise ValueError(f"rendered {role} image is unreadable") from exc


def _platform_records(content: dict) -> dict:
    record = {"content_id": content["content_id"], "best_answer": content["best_answer"]}
    return {"instagram": dict(record), "threads": dict(record)}


def check_platform_consistency(platforms: dict) -> None:
    instagram = platforms.get("instagram")
    threads = platforms.get("threads")
    if not isinstance(instagram, dict) or not isinstance(threads, dict):
        raise ValueError("instagram and threads platform records are required")
    if instagram.get("content_id") != threads.get("content_id"):
        raise ValueError("Instagram/Threads content_id mismatch")
    if instagram.get("best_answer") != threads.get("best_answer"):
        raise ValueError("Instagram/Threads best_answer mismatch")


def _review_item(content: dict, source_image: str | None, platforms: dict) -> dict:
    return {
        "content_id": content["content_id"],
        "review_scope": {"english": True, "japanese": True, "image": content["visual_required"]},
        "english": {
            "question": content["question"],
            "choices": content["choices"],
            "answer_type": content["answer_type"],
            "best_answer": content["best_answer"],
            "acceptable_answers": content["acceptable_answers"],
            "examples": content["examples"],
        },
        "japanese": {
            "explanation": content["explanation"],
            "answer_hint": content.get("answer_hint"),
            "answer_hint_approved": content.get("answer_hint_approved"),
            "example_translations": content.get("example_translations", []),
            "key_difference": content.get("key_difference"),
            "also_natural": content.get("also_natural"),
            "tip": content.get("tip"),
        },
        "image": ({"source_image_path": source_image,
                   "visual_description": content["visual_description"]}
                  if content["visual_required"] else None),
        "platforms": platforms,
    }


def machine_check(master_path: Path, platforms: dict | None = None) -> MachineCheckResult:
    content_id = master_path.stem
    try:
        content = _read_master(master_path)
        content_id = str(content.get("content_id", content_id))
        validate(content)
        _top_section(content)
        _sections(content)
        _check_lengths(content)
        source_image = _check_source_image(content)
        _check_rendered_image(content["content_id"], "question")
        _check_rendered_image(content["content_id"], "answer")
        records = platforms if platforms is not None else _platform_records(content)
        check_platform_consistency(records)
        return MachineCheckResult(content_id, "PASS", None, _review_item(content, source_image, records))
    except (FileNotFoundError, TypeError, ValueError) as exc:
        reason = str(exc).split(";", 1)[0].strip()[:160]
        return MachineCheckResult(content_id, "REJECT", reason, None)


def build_review_batch(results: list[MachineCheckResult]) -> dict:
    rejected = [result for result in results if result.status == "REJECT"]
    if rejected:
        raise ValueError("review batch cannot include machine-rejected content")
    return {
        "schema_version": 1,
        "review_policy": {
            "single_pass": True,
            "on_reject": "discard",
            "allow_repair": False,
            "response": {"status": "PASS or REJECT", "reason": "null or concise rejection reason"},
        },
        "review_checks": {
            "english": ["natural and grammatical question", "specified answer is valid and unambiguous",
                        "examples are natural", "answer and explanation do not conflict"],
            "japanese": ["natural concise Japanese for adult learners", "hint does not reveal the answer",
                         "hint and explanation are not repetitive", "no translation-manual tone"],
            "image": ["source image matches the question", "required subject, state, or action is visible",
                      "no contradiction, obvious generation failure, or unwanted text"],
        },
        "items": [result.item for result in results],
    }


def write_review_batch(results: list[MachineCheckResult], name: str = "review-batch") -> Path:
    batch = build_review_batch(results)
    REVIEW_PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = REVIEW_PAYLOAD_DIR / f"{name}.json"
    target.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def validate_decisions(batch: dict, decisions: list[dict]) -> list[dict]:
    expected = [item["content_id"] for item in batch.get("items", [])]
    if len(decisions) != len(expected):
        raise ValueError("one decision is required for every review item")
    normalized: list[dict] = []
    seen: set[str] = set()
    for decision in decisions:
        content_id = decision.get("content_id")
        status = decision.get("status")
        reason = decision.get("reason")
        if content_id not in expected or content_id in seen:
            raise ValueError("decision content_id is missing, duplicated, or unexpected")
        if status not in REVIEW_LABELS:
            raise ValueError("decision status must be PASS or REJECT")
        if status == "PASS" and reason is not None:
            raise ValueError("PASS reason must be null")
        if status == "REJECT" and (not isinstance(reason, str) or not reason.strip()):
            raise ValueError("REJECT requires a concise reason")
        if isinstance(reason, str) and len(reason) > 160:
            raise ValueError("REJECT reason exceeds 160 characters")
        normalized.append({"content_id": content_id, "status": status,
                           "reason": reason.strip() if isinstance(reason, str) else None})
        seen.add(content_id)
    return normalized


def write_review_results(batch_path: Path, decision_path: Path) -> list[Path]:
    if batch_path.resolve().parent != REVIEW_PAYLOAD_DIR.resolve():
        raise ValueError(f"batch must be directly under {REVIEW_PAYLOAD_DIR}")
    if decision_path.resolve().parent != REVIEW_DECISION_DIR.resolve():
        raise ValueError(f"decisions must be directly under {REVIEW_DECISION_DIR}")
    if not batch_path.is_file() or not decision_path.is_file():
        raise FileNotFoundError("required batch or decision file not found")
    batch = json.loads(batch_path.read_text(encoding="utf-8"))
    raw = json.loads(decision_path.read_text(encoding="utf-8"))
    decisions = raw.get("results") if isinstance(raw, dict) else None
    if not isinstance(decisions, list):
        raise ValueError("decision file must contain a results array")
    results = validate_decisions(batch, decisions)
    REVIEW_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for result in results:
        target = REVIEW_RESULT_DIR / f"{result['content_id']}.json"
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        paths.append(target)
    return paths


def save_machine_reject(result: MachineCheckResult) -> Path:
    if result.status != "REJECT":
        raise ValueError("only REJECT results may be saved here")
    REVIEW_RESULT_DIR.mkdir(parents=True, exist_ok=True)
    target = REVIEW_RESULT_DIR / f"{result.content_id}.json"
    target.write_text(json.dumps(result.compact(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
