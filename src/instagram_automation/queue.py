import json
from pathlib import Path

from .paths import IMAGE_DIR, QUEUE_DIR, REPO_ROOT, require_file
from .schedule import ALLOWED_STATUSES
from .validation import validate


def build_queue(master_path: Path, execution_eligibility: str = "scheduled") -> dict:
    source = require_file(master_path)
    try:
        content = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {source}: {exc}") from exc
    if not isinstance(content, dict):
        raise ValueError("Master JSON root must be an object")
    validate(content)
    content_id = content["content_id"]
    return {
        "content_id": content_id,
        "platform": "instagram",
        "content_type": "quiz",
        "channel": "feed",
        "publish_at": content["publish_at"],
        "status": "pending",
        "execution_eligibility": execution_eligibility,
        "carousel": [
            {"order": 1, "role": "question", "image_path": str(IMAGE_DIR / f"{content_id}-question.png")},
            {"order": 2, "role": "answer", "image_path": str(IMAGE_DIR / f"{content_id}-answer.png")},
        ],
        "caption": content["instagram_caption"],
    }


def build_story_queue(content: dict, execution_eligibility: str = "scheduled") -> dict:
    required = {"content_id", "content_type", "publish_at"}
    if not required.issubset(content) or content["content_type"] != "normal":
        raise ValueError("invalid normal master for Stories queue")
    content_id = content["content_id"]
    return {
        "content_id": content_id,
        "platform": "instagram",
        "content_type": "normal",
        "channel": "stories",
        "publish_at": content["publish_at"],
        "status": "pending",
        "execution_eligibility": execution_eligibility,
        "story_image": f"artifacts/stories/{content_id}-story.png",
    }


def validate_queue_state(queue: dict) -> None:
    if queue.get("status") not in ALLOWED_STATUSES:
        raise ValueError("invalid queue status")
    if queue.get("platform") != "instagram":
        raise ValueError("Instagram queue platform mismatch")
    if queue.get("content_type") == "quiz":
        roles = [(item.get("order"), item.get("role")) for item in queue.get("carousel", [])]
        if roles != [(1, "question"), (2, "answer")]:
            raise ValueError("Instagram carousel must be question then answer")
    elif queue.get("content_type") != "normal":
        raise ValueError("invalid Instagram queue content_type")


def write_queue(master_path: Path) -> Path:
    queue = build_queue(master_path)
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    target = QUEUE_DIR / f"{queue['content_id']}.json"
    target.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
