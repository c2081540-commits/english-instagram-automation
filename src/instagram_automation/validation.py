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
GUIDE_INDEPENDENT = {
    "こう聞かれたら、どう返す？", "こう頼まれたら、どう返す？",
    "こんなとき、英語でどう言う？", "この英語、どういう意味？",
    "正しい英文はどれ？", "「休憩する」の意味になるのはどれ？",
}
GUIDE_FORBIDDEN = ("前置詞", "動名詞", "三単現", "過去形", "現在完了", "不定詞", "原形", "受動態")
QUESTION_ROLES = {"learning_sentence", "meta_instruction"}
META_INSTRUCTION = re.compile(
    r"^(?:Which\b.*\?|Choose\b.*|Select\b.*)", re.IGNORECASE
)


def _validate_question_guide(content: dict, choices: list[str], errors: list[str]) -> None:
    guide = content.get("question_guide_ja")
    if content.get("visual_required") is True:
        if guide not in (None, ""):
            errors.append("question_guide_ja is prohibited when visual_required is true")
        if content.get("question_role") not in (None, ""):
            errors.append("question_role is prohibited when visual_required is true")
        return
    if not isinstance(guide, str) or not guide.strip():
        errors.append("question_guide_ja is required when visual_required is false")
        return
    if guide != guide.strip() or "\n" in guide or "\r" in guide or len(guide) > 30:
        errors.append("question_guide_ja must be one trimmed line of at most 30 characters")
    if any(term in guide for term in GUIDE_FORBIDDEN):
        errors.append("question_guide_ja must not reveal a grammar rule")
    role = content.get("question_role")
    if role not in QUESTION_ROLES:
        errors.append("question_role must be learning_sentence or meta_instruction for text quizzes")
    is_meta = bool(META_INSTRUCTION.match(content.get("question", "").strip()))
    if role == "meta_instruction" and not is_meta:
        errors.append("meta_instruction requires an English meta question")
    if role == "learning_sentence" and is_meta:
        errors.append("English meta question must use meta_instruction")
    count = len(choices)
    dependent = bool(re.fullmatch(r"「.+」なら(?:どっち|どれ)？", guide))
    natural = guide in {"自然なのはどっち？", "一番自然なのはどれ？"}
    if guide not in GUIDE_INDEPENDENT and not dependent and not natural:
        errors.append("question_guide_ja must use an approved fixed pattern")
    if role == "meta_instruction" and guide not in {
            "正しい英文はどれ？", "「休憩する」の意味になるのはどれ？"}:
        errors.append("meta_instruction requires a content-specific Japanese instruction")
    if count == 2 and ("どれ？" in guide or guide == "一番自然なのはどれ？"):
        errors.append("two-choice question_guide_ja must use どっち")
    if count == 4 and ("どっち？" in guide or guide == "自然なのはどっち？"):
        errors.append("four-choice question_guide_ja must use どれ")


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
    _validate_question_guide(content, choices, errors)
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
