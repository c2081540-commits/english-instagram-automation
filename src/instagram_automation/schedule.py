from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .paths import REPO_ROOT

SCHEDULE_CONFIG_PATH = REPO_ROOT / "config" / "schedule.json"
ALLOWED_STATUSES = {"pending", "posted", "failed", "skipped"}


def load_schedule_config(path: Path = SCHEDULE_CONFIG_PATH) -> dict:
    resolved = path.resolve()
    if resolved != SCHEDULE_CONFIG_PATH.resolve() or not resolved.is_file():
        raise FileNotFoundError(f"Required schedule config not found: {resolved}")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if value.get("timezone") != "Asia/Tokyo":
        raise ValueError("schedule timezone must be Asia/Tokyo")
    slots = value.get("quiz_slots")
    if not isinstance(slots, list) or len(slots) != 6 or len(set(slots)) != 6:
        raise ValueError("schedule requires six unique quiz slots")
    parsed = [_parse_slot(slot) for slot in slots]
    normal = _parse_slot(value.get("normal_slot"))
    if normal in parsed:
        raise ValueError("normal slot must not overlap a quiz slot")
    if set(value.get("allowed_statuses", [])) != ALLOWED_STATUSES:
        raise ValueError("schedule allowed_statuses mismatch")
    if value.get("past_slot_policy") != "hold":
        raise ValueError("past slots must use hold policy")
    return value


def _parse_slot(value: str) -> time:
    try:
        return time.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid schedule slot: {value!r}") from exc


def publish_datetime(day: date, slot: str, timezone_name: str = "Asia/Tokyo") -> datetime:
    return datetime.combine(day, _parse_slot(slot), ZoneInfo(timezone_name))


def eligibility(publish_at: str, now: datetime) -> str:
    target = datetime.fromisoformat(publish_at)
    if target.tzinfo is None or now.tzinfo is None:
        raise ValueError("publish_at and now must be timezone-aware")
    return "past_due_hold" if target < now else "scheduled"


def should_execute(queue: dict, now: datetime) -> bool:
    if queue.get("status") != "pending":
        return False
    if queue.get("execution_eligibility") != "scheduled":
        return False
    target = datetime.fromisoformat(queue["publish_at"])
    return target <= now


def schedule_week(week: dict, config: dict) -> dict:
    start = date.fromisoformat(week["start_date"])
    quizzes = week["quizzes"]
    normals = week["normals"]
    if len(quizzes) != 42 or len(normals) != 7:
        raise ValueError("schedule requires 42 quizzes and 7 normal posts")
    for day_index in range(7):
        day = start + timedelta(days=day_index)
        for item, slot in zip(quizzes[day_index * 6:(day_index + 1) * 6], config["quiz_slots"]):
            item["publish_at"] = publish_datetime(day, slot, config["timezone"]).isoformat()
        normals[day_index]["publish_at"] = publish_datetime(day, config["normal_slot"], config["timezone"]).isoformat()
    return week


def validate_schedule_items(items: list[dict]) -> None:
    if len(items) != 49:
        raise ValueError("schedule requires exactly 49 items")
    platform_slots: set[tuple[str, str]] = set()
    per_day: dict[str, dict[str, int]] = {}
    ids: set[str] = set()
    for item in items:
        content_id = item["content_id"]
        if content_id in ids:
            raise ValueError(f"duplicate scheduled content_id: {content_id}")
        ids.add(content_id)
        parsed = datetime.fromisoformat(item["publish_at"])
        if parsed.utcoffset() != timedelta(hours=9):
            raise ValueError("scheduled item must use Asia/Tokyo")
        key = (item["platform"], item["publish_at"])
        if key in platform_slots:
            raise ValueError("duplicate platform publish slot")
        platform_slots.add(key)
        day = parsed.date().isoformat()
        counts = per_day.setdefault(day, {"quiz": 0, "normal": 0})
        counts[item["content_type"]] += 1
        if item["content_type"] == "normal" and parsed.strftime("%H:%M") != "22:30":
            raise ValueError("normal post must use the 22:30 slot")
    if any(value != {"quiz": 6, "normal": 1} for value in per_day.values()) or len(per_day) != 7:
        raise ValueError("each schedule day requires six quizzes and one normal post")
