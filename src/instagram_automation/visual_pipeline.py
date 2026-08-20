from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from .paths import REPO_ROOT, SOURCE_IMAGE_DIR

VISUAL_CHECKS = (
    "問題内容と一致",
    "状態・動作が視認可能",
    "生成崩れなし",
    "不要な文字なし",
)


def source_path(master: dict) -> Path:
    value = master.get("problem_image_path")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("problem_image_path is required for a completed visual")
    path = (REPO_ROOT / value).resolve()
    if path.parent != SOURCE_IMAGE_DIR.resolve():
        raise ValueError("problem image must be directly under assets/source")
    if "placeholder" in path.name.casefold():
        raise ValueError("placeholder fixtures cannot be production visuals")
    if not path.is_file():
        raise FileNotFoundError(f"visual source not found: {path}")
    return path


def machine_check_visual(master: dict) -> dict:
    content_id = master.get("content_id")
    try:
        if master.get("visual_required") is not True:
            raise ValueError("visual check requires visual_required=true")
        path = source_path(master)
        with Image.open(path) as image:
            image.load()
            if image.format != "PNG":
                raise ValueError("visual source must be PNG")
            if image.mode not in {"RGB", "RGBA"}:
                raise ValueError("visual source must be RGB or RGBA")
            if image.width < 1024 or image.height < 600:
                raise ValueError("visual source resolution is too small")
        return {"content_id": content_id, "status": "PASS", "reason": None,
                "source_image": path.relative_to(REPO_ROOT).as_posix()}
    except (OSError, TypeError, ValueError, FileNotFoundError) as exc:
        return {"content_id": content_id, "status": "REJECT", "reason": str(exc)[:160],
                "source_image": None}


def validate_visual_review(machine_result: dict, review: dict) -> dict:
    if machine_result.get("status") != "PASS":
        raise ValueError("AI visual review cannot follow a failed machine check")
    if review.get("content_id") != machine_result.get("content_id"):
        raise ValueError("visual review content_id mismatch")
    if review.get("status") not in {"PASS", "REJECT"}:
        raise ValueError("visual review status must be PASS or REJECT")
    reason = review.get("reason")
    if review["status"] == "PASS" and reason is not None:
        raise ValueError("PASS reason must be null")
    if review["status"] == "REJECT" and (not isinstance(reason, str) or not reason.strip()):
        raise ValueError("REJECT requires a concise reason")
    return {"content_id": review["content_id"], "status": review["status"],
            "reason": reason, "checks": list(VISUAL_CHECKS)}


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value
