from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher

from .daily_batch import validate_normal_candidate, validate_quiz_candidate

TARGET_CATEGORIES = {
    "grammar_usage": 15,
    "visual_vocabulary": 8,
    "natural_choice": 6,
    "situation": 11,
    "review": 2,
}
TARGET_DIFFICULTIES = {"very_easy": 13, "easy": 21, "easy_plus": 8}
TARGET_CHOICES = {2: 17, 4: 25}
TARGET_VISUALS = 14
TARGET_SEASONAL = 6
NORMAL_CATEGORIES = {
    "learning_habit", "study_method", "english_trivia", "common_mistake",
    "memory_tip", "practical_expression", "skill_practice",
}
SHORT_AFFIRMATIVE_FAMILY = "short_affirmative_response"
MAX_SHORT_AFFIRMATIVE_PER_WEEK = 5
MAX_SAME_SITUATION_PURPOSE = 2


def difficulty_bucket(value: str) -> str:
    return {"beginner": "easy", "intermediate": "easy_plus"}.get(value, value)


def _normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _too_similar(left: str, right: str) -> bool:
    a, b = _normalized(left), _normalized(right)
    return bool(a and b and SequenceMatcher(None, a, b).ratio() >= .9)


def validate_weekly_batch(week: dict, existing: list[dict]) -> dict:
    quizzes = week.get("quizzes")
    normals = week.get("normals")
    if not isinstance(quizzes, list) or len(quizzes) != 42:
        raise ValueError("weekly batch requires exactly 42 quizzes")
    if not isinstance(normals, list) or len(normals) != 7:
        raise ValueError("weekly batch requires exactly 7 normal items")
    for item in quizzes:
        validate_quiz_candidate(item)
    for item in normals:
        validate_normal_candidate(item)

    categories = Counter(item["production_category"] for item in quizzes)
    difficulties = Counter(difficulty_bucket(item["difficulty"]) for item in quizzes)
    choices = Counter(len(item["choices"]) for item in quizzes)
    if categories != Counter(TARGET_CATEGORIES):
        raise ValueError(f"weekly category distribution mismatch: {dict(categories)}")
    if difficulties != Counter(TARGET_DIFFICULTIES):
        raise ValueError(f"weekly difficulty distribution mismatch: {dict(difficulties)}")
    if choices != Counter(TARGET_CHOICES):
        raise ValueError(f"weekly choice distribution mismatch: {dict(choices)}")
    if sum(item["visual_required"] for item in quizzes) != TARGET_VISUALS:
        raise ValueError("weekly visual count must be 14")
    if sum(item["seasonal"] for item in quizzes) != TARGET_SEASONAL:
        raise ValueError("weekly seasonal count must be 6")

    situations = [item for item in quizzes if item["production_category"] == "situation"]
    for item in situations:
        if not isinstance(item.get("situation_purpose"), str) or not item["situation_purpose"].strip():
            raise ValueError(f"situation_purpose is required: {item['content_id']}")
        if not isinstance(item.get("response_family"), str) or not item["response_family"].strip():
            raise ValueError(f"response_family is required: {item['content_id']}")
    purposes = Counter(item["situation_purpose"] for item in situations)
    repeated = {key: value for key, value in purposes.items() if value > MAX_SAME_SITUATION_PURPOSE}
    if repeated:
        raise ValueError(f"situation learning purpose is overrepresented: {repeated}")
    affirmative_count = sum(item["response_family"] == SHORT_AFFIRMATIVE_FAMILY for item in situations)
    if affirmative_count > MAX_SHORT_AFFIRMATIVE_PER_WEEK:
        raise ValueError("short affirmative situation responses are overrepresented")

    normal_categories = []
    for item in normals:
        category = item.get("normal_category")
        if category not in NORMAL_CATEGORIES:
            raise ValueError(f"invalid normal_category: {item['content_id']}")
        normal_categories.append(category)
    if len(set(normal_categories)) < 4:
        raise ValueError("weekly normal posts require at least four content categories")
    if sum(category in {"learning_habit", "study_method"} for category in normal_categories) > 3:
        raise ValueError("weekly normal posts are overconcentrated on habits and study methods")

    for day in range(7):
        daily = quizzes[day * 6:(day + 1) * 6]
        if max(Counter(item["production_category"] for item in daily).values()) > 3:
            raise ValueError("a daily category is excessively concentrated")

    ids = [item["content_id"] for item in quizzes + normals]
    if len(ids) != len(set(ids)):
        raise ValueError("weekly content_id duplication")
    existing_ids = {item.get("content_id") for item in existing}
    if any(content_id in existing_ids for content_id in ids):
        raise ValueError("weekly content_id collides with an existing master")

    old_quizzes = [item for item in existing if item.get("question")]
    for index, item in enumerate(quizzes):
        others = old_quizzes + quizzes[:index]
        if any(_too_similar(item["question"], other["question"]) for other in others):
            raise ValueError(f"duplicate or near-duplicate question: {item['content_id']}")
        if any(item.get("examples") and item["examples"] == other.get("examples") for other in others):
            raise ValueError(f"duplicate example: {item['content_id']}")
        if any(item["answer_hint"] == other.get("answer_hint") for other in others):
            raise ValueError(f"duplicate hint: {item['content_id']}")

    old_normals = [item for item in existing if item.get("content_type") == "normal"]
    for index, item in enumerate(normals):
        if any(item["theme"] == other.get("theme") or
               _too_similar(item["story_headline"], other.get("story_headline", ""))
               for other in old_normals + normals[:index]):
            raise ValueError(f"duplicate normal theme or conclusion: {item['content_id']}")

    return {
        "quiz_total": 42,
        "normal_total": 7,
        "categories": dict(categories),
        "difficulties": dict(difficulties),
        "choice_counts": {str(key): value for key, value in sorted(choices.items())},
        "visual_required": sum(item["visual_required"] for item in quizzes),
        "seasonal": sum(item["seasonal"] for item in quizzes),
        "short_affirmative_situations": affirmative_count,
        "situation_purposes": dict(purposes),
        "normal_categories": dict(Counter(normal_categories)),
        "initial_pass": 49,
        "reject": 0,
        "replacements": 0,
        "duplicate_reject": 0,
    }


def build_weekly_review_payload(week: dict) -> dict:
    items = []
    for item in week["quizzes"]:
        visual = None
        if item["visual_required"]:
            visual = {
                "status": "READY" if item.get("problem_image_path") else "PENDING",
                "description": item["visual_description"],
                "source_image_path": item.get("problem_image_path"),
            }
        items.append({
            "content_id": item["content_id"],
            "content_type": "quiz",
            "english": {key: item[key] for key in ("question_role", "question", "choices", "answer_type", "best_answer", "examples")},
            "japanese": {key: item.get(key) for key in ("question_guide_ja", "answer_hint", "answer_point", "explanation", "example_translations", "key_difference", "also_natural")},
            "visual": visual,
        })
    for item in week["normals"]:
        items.append({"content_id": item["content_id"], "content_type": "normal",
                      "japanese": {key: item[key] for key in ("normal_category", "theme", "threads_text", "story_headline", "story_body")}})
    return {
        "schema_version": 1,
        "single_batch_review": True,
        "quality_profile": "restart_adult_jp",
        "checks": ["英語・正解", "日本語", "画像", "挫折者向けとして3〜5秒で理解できるか"],
        "on_reject": "discard_and_replace_without_repair",
        "items": items,
    }
