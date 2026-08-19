import re
from datetime import datetime

CONTENT_ID = re.compile(r"^ENG-\d{6}$")
ANSWER_TYPES = {"single", "best", "multiple"}
REQUIRED = {
    "content_id", "category", "difficulty", "seasonal", "question", "choices",
    "answer_type", "best_answer", "acceptable_answers", "explanation",
    "key_difference", "examples", "tip", "visual_required", "visual_type",
    "visual_description", "instagram_caption", "threads_parent_text",
    "threads_answer_text", "publish_at",
}


class ValidationError(ValueError):
    pass


def validate(content: dict) -> None:
    missing = sorted(REQUIRED - content.keys())
    errors = [f"missing fields: {', '.join(missing)}"] if missing else []
    content_id = content.get("content_id")
    if not isinstance(content_id, str) or not CONTENT_ID.fullmatch(content_id):
        errors.append("content_id must match ENG-000001")
    if not isinstance(content.get("question"), str) or not content.get("question", "").strip():
        errors.append("question must be a non-empty string")
    choices = content.get("choices")
    if not isinstance(choices, list) or len(choices) < 2 or any(not isinstance(x, str) or not x.strip() for x in choices):
        errors.append("choices must contain at least two non-empty strings")
        choices = []
    answer_type = content.get("answer_type")
    if answer_type not in ANSWER_TYPES:
        errors.append("answer_type must be single, best, or multiple")
    best = content.get("best_answer")
    acceptable = content.get("acceptable_answers")
    if not isinstance(best, str) or best not in choices:
        errors.append("best_answer must exactly match one choice")
    if not isinstance(acceptable, list) or not acceptable or any(x not in choices for x in acceptable):
        errors.append("acceptable_answers must be a non-empty subset of choices")
    elif answer_type in {"single", "best"} and len(acceptable) != 1:
        errors.append(f"answer_type {answer_type} requires exactly one acceptable answer")
    elif answer_type == "multiple" and len(acceptable) < 2:
        errors.append("answer_type multiple requires at least two acceptable answers")
    if isinstance(best, str) and isinstance(acceptable, list) and best not in acceptable:
        errors.append("best_answer must be included in acceptable_answers")
    if content.get("visual_required") is not False and content.get("visual_required") is not True:
        errors.append("visual_required must be boolean")
    if content.get("visual_required") is True:
        if not isinstance(content.get("visual_type"), str) or not content.get("visual_type", "").strip():
            errors.append("visual_type is required when visual_required is true")
        if not isinstance(content.get("visual_description"), str) or not content.get("visual_description", "").strip():
            errors.append("visual_description is required when visual_required is true")
    try:
        value = content.get("publish_at")
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else None
        if parsed is None or parsed.tzinfo is None:
            raise ValueError
    except ValueError:
        errors.append("publish_at must be an ISO 8601 datetime with timezone")
    for field in ("instagram_caption", "threads_parent_text", "threads_answer_text"):
        if not isinstance(content.get(field), str) or not content.get(field, "").strip():
            errors.append(f"{field} must be a non-empty string")
    if errors:
        raise ValidationError("; ".join(errors))
