from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .answer_renderer import _sections, _top_section
from .paths import IMAGE_DIR, REPO_ROOT, require_file
from .review import _check_lengths
from .validation import validate

EXPECTED_MIX = {
    "grammar_usage": 2,
    "visual_vocabulary": 1,
    "natural_choice": 1,
    "situation": 2,
}
MAX_VISUALS = 2
MAX_REPLACEMENTS = 3


def _read_json(path: Path) -> dict:
    source = require_file(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("daily batch JSON root must be an object")
    return value


def _duplicate_key(item: dict) -> tuple[str, str]:
    question = " ".join(item["question"].casefold().split())
    answer = " ".join(item["best_answer"].casefold().split())
    return question, answer


def validate_quiz_candidate(item: dict) -> None:
    validate(item)
    _check_lengths(item)
    _top_section(item)
    _sections(item)
    production_category = item.get("production_category")
    if production_category not in EXPECTED_MIX:
        raise ValueError("production_category is invalid")
    hashtags = item.get("instagram_hashtags")
    if not isinstance(hashtags, list) or any(not isinstance(tag, str) for tag in hashtags):
        raise ValueError("instagram_hashtags must be a list of strings")
    if item["visual_required"]:
        if item.get("problem_image_path") is not None:
            raise ValueError("Phase 3 visual candidates must not claim an ungenerated asset")
    elif item.get("problem_image_path") is not None:
        raise ValueError("problem_image_path must be null when visual_required is false")


def validate_normal_candidate(item: dict) -> None:
    required = {"content_id", "content_type", "theme", "threads_text",
                "story_headline", "story_body", "publish_at"}
    missing = sorted(required - item.keys())
    if missing:
        raise ValueError(f"missing normal fields: {', '.join(missing)}")
    if item.get("content_type") != "normal":
        raise ValueError("normal content_type must be normal")
    for field, limit in (("theme", 80), ("threads_text", 500),
                         ("story_headline", 80), ("story_body", 240)):
        value = item.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"{field} must be a non-empty string of at most {limit} characters")


def validate_daily_batch(batch: dict, existing: list[dict] | None = None) -> None:
    quizzes = batch.get("quizzes")
    normal = batch.get("normal")
    if not isinstance(quizzes, list) or len(quizzes) != 6:
        raise ValueError("daily batch requires exactly 6 quizzes")
    if not isinstance(normal, dict):
        raise ValueError("daily batch requires exactly 1 normal item")
    for quiz in quizzes:
        validate_quiz_candidate(quiz)
    validate_normal_candidate(normal)
    counts = Counter(item["production_category"] for item in quizzes)
    if counts != Counter(EXPECTED_MIX):
        raise ValueError(f"invalid daily category mix: {dict(counts)}")
    if sum(item["seasonal"] is True for item in quizzes) != 1:
        raise ValueError("daily batch requires exactly one seasonal quiz")
    if sum(item["visual_required"] is True for item in quizzes) > MAX_VISUALS:
        raise ValueError("daily batch exceeds the visual_required limit")
    ids = [item["content_id"] for item in quizzes] + [normal["content_id"]]
    if len(ids) != len(set(ids)):
        raise ValueError("daily batch contains duplicate content_id")
    previous = existing or []
    existing_ids = {item.get("content_id") for item in previous}
    if any(content_id in existing_ids for content_id in ids):
        raise ValueError("daily batch content_id collides with an existing master")
    keys = [_duplicate_key(item) for item in quizzes]
    old_keys = {_duplicate_key(item) for item in previous if "question" in item}
    if len(keys) != len(set(keys)) or any(key in old_keys for key in keys):
        raise ValueError("daily batch duplicates an existing or same-batch question")
    old_normal = {(item.get("theme"), item.get("story_headline")) for item in previous
                  if item.get("content_type") == "normal"}
    if (normal["theme"], normal["story_headline"]) in old_normal:
        raise ValueError("daily normal content duplicates an existing theme and conclusion")


def apply_review_decisions(batch: dict, decisions: list[dict], replacements: list[dict] | None = None,
                           max_replacements: int = MAX_REPLACEMENTS) -> dict:
    quizzes = {item["content_id"]: item for item in batch["quizzes"]}
    normal = {batch["normal"]["content_id"]: batch["normal"]}
    candidates = {**quizzes, **normal}
    if len(decisions) != len(candidates):
        raise ValueError("one review decision is required for each daily item")
    accepted: list[dict] = []
    rejected: list[dict] = []
    for decision in decisions:
        content_id = decision.get("content_id")
        status = decision.get("status")
        if content_id not in candidates or status not in {"PASS", "REJECT"}:
            raise ValueError("invalid review decision")
        if status == "REJECT":
            reason = decision.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("REJECT requires a concise reason")
            rejected.append({"content_id": content_id, "status": "REJECT", "reason": reason[:160]})
        else:
            accepted.append(candidates[content_id])
    supplied = replacements or []
    if len(rejected) > max_replacements or len(supplied) < len(rejected):
        raise ValueError("replacement limit reached before a complete PASS batch was available")
    accepted.extend(supplied[:len(rejected)])
    return {"accepted": accepted, "discarded": rejected}


def build_daily_status(batch: dict) -> dict:
    items = []
    for quiz in batch["quizzes"]:
        content_id = quiz["content_id"]
        if quiz["visual_required"]:
            question_status = "WAITING_FOR_VISUAL"
            question_image = None
        else:
            question_status = "READY"
            question_image = (IMAGE_DIR / f"{content_id}-question.png").relative_to(REPO_ROOT).as_posix()
        items.append({
            "content_id": content_id,
            "content_type": "quiz",
            "question_status": question_status,
            "question_image": question_image,
            "answer_image": (IMAGE_DIR / f"{content_id}-answer.png").relative_to(REPO_ROOT).as_posix(),
            "caption": quiz["instagram_caption"],
            "hashtags": quiz["instagram_hashtags"],
            "publish_at": quiz["publish_at"],
        })
    normal = batch["normal"]
    items.append({
        "content_id": normal["content_id"],
        "content_type": "normal",
        "story_image": f"artifacts/stories/{normal['content_id']}-story.png",
        "publish_at": normal["publish_at"],
        "status": "READY",
    })
    return {"production_date": batch["production_date"], "items": items}


def build_daily_review_payload(batch: dict) -> dict:
    items = []
    for quiz in batch["quizzes"]:
        items.append({
            "content_id": quiz["content_id"],
            "content_type": "quiz",
            "english": {
                "question": quiz["question"],
                "choices": quiz["choices"],
                "answer_type": quiz["answer_type"],
                "best_answer": quiz["best_answer"],
                "examples": quiz["examples"],
            },
            "japanese": {
                "hint": quiz["answer_hint"],
                "explanation": quiz["explanation"],
                "example_translations": quiz.get("example_translations", []),
            },
            "visual_plan": ({"visual_type": quiz["visual_type"],
                             "visual_description": quiz["visual_description"]}
                            if quiz["visual_required"] else None),
        })
    normal = batch["normal"]
    items.append({
        "content_id": normal["content_id"],
        "content_type": "normal",
        "japanese": {
            "threads_text": normal["threads_text"],
            "story_headline": normal["story_headline"],
            "story_body": normal["story_body"],
        },
    })
    return {
        "schema_version": 1,
        "single_batch_review": True,
        "image_review": False,
        "checks": ["英語・文法・正解", "日本語・ヒント", "教材として明らかな問題がないか"],
        "on_reject": "discard_and_replace_without_repair",
        "max_replacements": MAX_REPLACEMENTS,
        "response_format": "PASS or REJECT: concise reason",
        "items": items,
    }


def format_daily_dry_run(status: dict) -> str:
    lines = [f"DRY RUN Instagram daily | {status['production_date']}"]
    for item in status["items"]:
        if item["content_type"] == "quiz":
            lines.extend([
                f"{item['content_id']} | {item['publish_at']} | {item['question_status']}",
                f"question_image: {item['question_image']}",
                f"answer_image: {item['answer_image']}",
                f"caption: {item['caption']}",
            ])
        else:
            lines.extend([
                f"{item['content_id']} | {item['publish_at']} | {item['status']}",
                f"story_image: {item['story_image']}",
            ])
    return "\n".join(lines)
