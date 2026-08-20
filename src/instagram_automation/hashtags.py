from __future__ import annotations

import json
from pathlib import Path

from .paths import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "config" / "instagram_hashtags.json"


class HashtagConfigError(ValueError):
    pass


def load_hashtag_config(path: Path = CONFIG_PATH) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    common = value.get("common")
    categories = value.get("categories")
    if not isinstance(common, list) or len(common) != 2:
        raise HashtagConfigError("Exactly two common hashtags are required")
    if not isinstance(categories, dict):
        raise HashtagConfigError("Hashtag categories must be an object")
    _validate_tags(common, 2)
    return value


def _validate_tags(tags: list, expected_count: int) -> None:
    if len(tags) != expected_count:
        raise HashtagConfigError(f"Exactly {expected_count} hashtags are required")
    if any(not isinstance(tag, str) or not tag or not tag.startswith("#") for tag in tags):
        raise HashtagConfigError("Every hashtag must be a non-empty string beginning with #")
    if len(set(tags)) != len(tags):
        raise HashtagConfigError("Duplicate hashtags are not allowed")


def hashtags_for_category(category: str, config: dict | None = None) -> list[str]:
    config = config or load_hashtag_config()
    common = config.get("common")
    categories = config.get("categories")
    if not isinstance(common, list) or len(common) != 2:
        raise HashtagConfigError("Exactly two common hashtags are required")
    if not isinstance(categories, dict) or category not in categories:
        raise HashtagConfigError(f"No hashtag configuration for category: {category}")
    category_tags = categories[category]
    if not isinstance(category_tags, list):
        raise HashtagConfigError(f"Hashtags for {category} must be a list")
    _validate_tags(common, 2)
    _validate_tags(category_tags, 2)
    combined = [*common, *category_tags]
    _validate_tags(combined, 4)
    return combined


def build_final_caption(caption: str, category: str, config: dict | None = None) -> str:
    if not isinstance(caption, str) or not caption:
        raise HashtagConfigError("Caption body must be a non-empty string")
    tags = hashtags_for_category(category, config)
    return f"{caption}\n\n{' '.join(tags)}"
