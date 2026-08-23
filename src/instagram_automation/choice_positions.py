from __future__ import annotations

import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from .paths import REPO_ROOT

CONFIG_PATH = REPO_ROOT / "config" / "quiz_positioning.json"


def load_position_config(path: Path = CONFIG_PATH) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("allowed_choice_counts") != [2, 4]:
        raise ValueError("choice position config must support exactly 2 and 4 choices")
    if value.get("assignment_strategy") != "least_used_balanced":
        raise ValueError("unsupported choice position assignment strategy")
    return value


def correct_position(item: dict) -> str:
    choices = item.get("choices")
    best = item.get("best_answer")
    if not isinstance(choices, list) or len(choices) not in {2, 4} or best not in choices:
        raise ValueError(f"invalid choices/best_answer: {item.get('content_id')}")
    return "ABCD"[choices.index(best)]


def _position_letters(choice_count: int) -> str:
    if choice_count not in {2, 4}:
        raise ValueError("only 2-choice and 4-choice quizzes are supported")
    return "ABCD"[:choice_count]


def max_same_position_streak(items: list[dict]) -> int:
    maximum = current = 0
    previous = None
    for item in sorted(items, key=lambda value: value["publish_at"]):
        position = correct_position(item)
        current = current + 1 if position == previous else 1
        previous = position
        maximum = max(maximum, current)
    return maximum


def position_report(items: list[dict]) -> dict:
    distributions = {}
    for choice_count in (2, 4):
        subset = [item for item in items if len(item["choices"]) == choice_count]
        counts = Counter(correct_position(item) for item in subset)
        distributions[str(choice_count)] = {
            letter: counts[letter] for letter in _position_letters(choice_count)
        }
    daily = {}
    for day in sorted({item["publish_at"][:10] for item in items}):
        daily[day] = position_report_without_daily(
            [item for item in items if item["publish_at"][:10] == day])
    return {"distribution": distributions,
            "max_same_position_streak": max_same_position_streak(items),
            "daily": daily}


def position_report_without_daily(items: list[dict]) -> dict:
    result = {}
    for choice_count in (2, 4):
        counts = Counter(correct_position(item) for item in items
                         if len(item["choices"]) == choice_count)
        result[str(choice_count)] = {
            letter: counts[letter] for letter in _position_letters(choice_count)
        }
    return result


def validate_position_distribution(items: list[dict], path: Path = CONFIG_PATH) -> dict:
    config = load_position_config(path)
    report = position_report(items)
    for choice_count in (2, 4):
        counts = list(report["distribution"][str(choice_count)].values())
        limit = config[("two" if choice_count == 2 else "four") +
                       "_choice_weekly_max_difference"]
        if max(counts) - min(counts) > limit:
            raise ValueError(f"{choice_count}-choice weekly correct-position distribution is biased")
        subset = [item for item in items if len(item["choices"]) == choice_count]
        if max_same_position_streak(subset) > config["max_same_position_streak"]:
            raise ValueError(f"{choice_count}-choice correct-position streak exceeds limit")
    if report["max_same_position_streak"] > config["max_same_position_streak"]:
        raise ValueError("overall correct-position streak exceeds limit")
    for day, groups in report["daily"].items():
        for choice_count, counts in groups.items():
            if sum(counts.values()) and max(counts.values()) - min(counts.values()) > config["daily_max_difference"]:
                raise ValueError(f"daily correct-position bias: {day} {choice_count}-choice")
    return report


def assign_balanced_positions(items: list[dict]) -> list[dict]:
    """Place fixed answers using only position usage; difficulty is deliberately ignored."""
    result = deepcopy(items)
    usage = {2: Counter(), 4: Counter()}
    daily = defaultdict(lambda: {2: Counter(), 4: Counter()})
    recent_all: list[str] = []
    recent_by_count = {2: [], 4: []}
    for item in sorted(result, key=lambda value: value["publish_at"]):
        count = len(item["choices"])
        letters = _position_letters(count)
        day = item["publish_at"][:10]
        allowed = [letter for letter in letters
                   if recent_all[-2:] != [letter, letter]
                   and recent_by_count[count][-2:] != [letter, letter]] or list(letters)
        chosen = min(allowed, key=lambda letter: (
            usage[count][letter], daily[day][count][letter], letters.index(letter)))
        best = item["best_answer"]
        distractors = [choice for choice in item["choices"] if choice != best]
        position = letters.index(chosen)
        item["choices"] = distractors[:position] + [best] + distractors[position:]
        usage[count][chosen] += 1
        daily[day][count][chosen] += 1
        recent_all.append(chosen)
        recent_by_count[count].append(chosen)
    validate_position_distribution(result)
    return result
