#!/usr/bin/env python3
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.paths import MASTER_DIR, QUEUE_DIR, THREADS_REPO_ROOT  # noqa: E402
from instagram_automation.queue import (build_queue, build_story_queue,
                                         validate_queue_state)  # noqa: E402
from instagram_automation.schedule import (eligibility, load_schedule_config,
                                            schedule_week,
                                            validate_schedule_items)  # noqa: E402


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    if len(sys.argv) not in {2, 3}:
        raise SystemExit("Usage: finalize_week_schedule.py START_DATE [AS_OF_ISO8601]")
    start = date.fromisoformat(sys.argv[1])
    now = (datetime.fromisoformat(sys.argv[2]) if len(sys.argv) == 3
           else datetime.now(ZoneInfo("Asia/Tokyo")))
    if now.tzinfo is None:
        raise ValueError("AS_OF must include a timezone")
    config = load_schedule_config()
    week_path = REPO_ROOT / "data" / "production" / f"week-{start.isoformat()}.json"
    week = schedule_week(read_json(week_path), config)
    write_json(week_path, week)

    schedule_items = []
    dry_run_entries = []
    for item in week["quizzes"]:
        content_id = item["content_id"]
        write_json(MASTER_DIR / f"{content_id}.json", item)
        write_json(THREADS_REPO_ROOT / "data" / "master" / "quiz" / f"{content_id}.json", item)
        hold = eligibility(item["publish_at"], now)
        queue = build_queue(MASTER_DIR / f"{content_id}.json", hold)
        validate_queue_state(queue)
        for slide in queue["carousel"]:
            if not Path(slide["image_path"]).is_file():
                raise FileNotFoundError(f"Required carousel asset missing: {slide['image_path']}")
        write_json(QUEUE_DIR / f"{content_id}.json", queue)
        schedule_items.append({key: queue[key] for key in
                               ("content_id", "platform", "content_type", "publish_at", "status", "execution_eligibility")})
        dry_run_entries.append((queue["publish_at"],
            f"{queue['publish_at']} | {content_id} | quiz | Feed | "
            f"{queue['carousel'][0]['image_path']} -> {queue['carousel'][1]['image_path']} | "
            f"caption=yes | {queue['status']} | {queue['execution_eligibility']}"))

    for item in week["normals"]:
        content_id = item["content_id"]
        write_json(MASTER_DIR / "normal" / f"{content_id}.json", item)
        write_json(THREADS_REPO_ROOT / "data" / "master" / "normal" / f"{content_id}.json", item)
        hold = eligibility(item["publish_at"], now)
        queue = build_story_queue(item, hold)
        validate_queue_state(queue)
        if not (REPO_ROOT / queue["story_image"]).is_file():
            raise FileNotFoundError(f"Required Story asset missing: {queue['story_image']}")
        write_json(QUEUE_DIR / f"{content_id}.json", queue)
        schedule_items.append({key: queue[key] for key in
                               ("content_id", "platform", "content_type", "publish_at", "status", "execution_eligibility")})
        dry_run_entries.append((queue["publish_at"],
            f"{queue['publish_at']} | {content_id} | normal | Stories | {queue['story_image']} | "
            f"caption=no | {queue['status']} | {queue['execution_eligibility']}"))

    validate_schedule_items(schedule_items)
    for day_index in range(7):
        day = start + timedelta(days=day_index)
        daily = {
            "production_date": day.isoformat(),
            "timezone": config["timezone"],
            "quality_profile": week["quality_profile"],
            "quizzes": week["quizzes"][day_index * 6:(day_index + 1) * 6],
            "normal": week["normals"][day_index],
        }
        write_json(REPO_ROOT / "data" / "production" / f"daily-{day.isoformat()}.json", daily)

    final = {
        "start_date": week["start_date"],
        "end_date": week["end_date"],
        "timezone": config["timezone"],
        "generated_at": now.isoformat(),
        "past_slot_policy": config["past_slot_policy"],
        "items": sorted(schedule_items, key=lambda item: item["publish_at"]),
    }
    write_json(REPO_ROOT / "data" / "production" / f"final-schedule-{start.isoformat()}.json", final)
    output = REPO_ROOT / "artifacts" / "weekly" / start.isoformat() / "instagram-final-dry-run.txt"
    dry_run = [f"DRY RUN Instagram final schedule | {week['start_date']} to {week['end_date']}"]
    dry_run.extend(text for _, text in sorted(dry_run_entries))
    output.write_text("\n".join(dry_run) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
