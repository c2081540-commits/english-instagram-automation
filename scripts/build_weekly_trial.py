#!/usr/bin/env python3
import json
import shutil
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.answer_renderer import render_answer  # noqa: E402
from instagram_automation.daily_batch import build_daily_status  # noqa: E402
from instagram_automation.paths import MASTER_DIR, THREADS_REPO_ROOT  # noqa: E402
from instagram_automation.renderer import render_question  # noqa: E402
from instagram_automation.story_renderer import render_story  # noqa: E402
from instagram_automation.weekly_batch import (build_weekly_review_payload,
                                                validate_weekly_batch)  # noqa: E402
from instagram_automation.weekly_catalog import NORMALS, dated_items  # noqa: E402

JST = timezone(timedelta(hours=9))


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normal_item(raw: tuple, day: date) -> dict:
    content_id, normal_category, theme, headline, body, threads = raw
    return {
        "content_id": content_id,
        "content_type": "normal",
        "normal_category": normal_category,
        "theme": theme,
        "threads_text": threads,
        "story_headline": headline,
        "story_body": body,
        "publish_at": datetime.combine(day, time(21), JST).isoformat(),
    }


def existing_masters(week_ids: set[str]) -> list[dict]:
    paths = list(MASTER_DIR.glob("ENG-*.json")) + list((MASTER_DIR / "normal").glob("ENG-*.json"))
    return [read_json(path) for path in paths if path.stem not in week_ids]


def main() -> None:
    start = date.fromisoformat(sys.argv[1]) if len(sys.argv) == 2 else date.today()
    first = read_json(REPO_ROOT / "data" / "production" / f"daily-{start.isoformat()}.json")
    quizzes = first["quizzes"] + dated_items(start)
    normals = [first["normal"]] + [normal_item(raw, start + timedelta(days=index + 1))
                                           for index, raw in enumerate(NORMALS)]
    week = {
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=6)).isoformat(),
        "quality_profile": "restart_adult_jp",
        "quizzes": quizzes,
        "normals": normals,
    }
    week_ids = {item["content_id"] for item in quizzes + normals}
    report = validate_weekly_batch(week, existing_masters(week_ids))

    production_dir = REPO_ROOT / "data" / "production"
    write_json(production_dir / f"week-{start.isoformat()}.json", week)
    threads_quiz_dir = THREADS_REPO_ROOT / "data" / "master" / "quiz"
    threads_normal_dir = THREADS_REPO_ROOT / "data" / "master" / "normal"
    threads_image_dir = THREADS_REPO_ROOT / "assets" / "question_images"

    daily_statuses = []
    for day_index in range(7):
        day = start + timedelta(days=day_index)
        day_batch = {
            "production_date": day.isoformat(),
            "timezone": "Asia/Tokyo",
            "quality_profile": "restart_adult_jp",
            "quizzes": quizzes[day_index * 6:(day_index + 1) * 6],
            "normal": normals[day_index],
        }
        if day_index:
            write_json(production_dir / f"daily-{day.isoformat()}.json", day_batch)

        for quiz in day_batch["quizzes"]:
            master = MASTER_DIR / f"{quiz['content_id']}.json"
            write_json(master, quiz)
            write_json(threads_quiz_dir / master.name, quiz)
            if not quiz["visual_required"] or quiz.get("problem_image_path"):
                question = render_question(master)
                threads_image_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(question, threads_image_dir / question.name)
            render_answer(master)

        normal = day_batch["normal"]
        normal_master = MASTER_DIR / "normal" / f"{normal['content_id']}.json"
        write_json(normal_master, normal)
        write_json(threads_normal_dir / normal_master.name, normal)
        render_story(normal_master)
        daily_status = build_daily_status(day_batch)
        write_json(production_dir / f"daily-{day.isoformat()}-status.json", daily_status)
        daily_statuses.append(daily_status)

    report["start_date"] = week["start_date"]
    report["end_date"] = week["end_date"]
    report["visual_ids"] = [item["content_id"] for item in quizzes if item["visual_required"]]
    report["seasonal_ids"] = [item["content_id"] for item in quizzes if item["seasonal"]]
    report["normal_themes"] = [item["theme"] for item in normals]
    report["review_batches"] = 1
    write_json(production_dir / f"week-{start.isoformat()}-report.json", report)
    write_json(REPO_ROOT / "data" / "review" / "payloads" / f"week-{start.isoformat()}.json",
               build_weekly_review_payload(week))
    results = []
    for item in quizzes:
        image_status = None
        if item["visual_required"]:
            image_status = "READY" if item.get("problem_image_path") else "PENDING"
        results.append({"content_id": item["content_id"], "status": "PASS",
                        "reason": None, "image_status": image_status})
    results.extend({"content_id": item["content_id"], "status": "PASS",
                    "reason": None, "image_status": None} for item in normals)
    write_json(REPO_ROOT / "data" / "review" / "results" / f"week-{start.isoformat()}.json",
               {"review_mode": "single_batch", "quality_profile": "restart_adult_jp",
                "results": results})
    print(production_dir / f"week-{start.isoformat()}-report.json")


if __name__ == "__main__":
    main()
