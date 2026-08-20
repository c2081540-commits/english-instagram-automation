#!/usr/bin/env python3
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.answer_renderer import render_answer  # noqa: E402
from instagram_automation.daily_batch import (build_daily_review_payload, build_daily_status,
                                                validate_daily_batch)  # noqa: E402
from instagram_automation.paths import MASTER_DIR  # noqa: E402
from instagram_automation.renderer import render_question  # noqa: E402
from instagram_automation.story_renderer import render_story  # noqa: E402


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def existing_masters(batch_ids: set[str]) -> list[dict]:
    paths = list(MASTER_DIR.glob("ENG-*.json")) + list((MASTER_DIR / "normal").glob("ENG-*.json"))
    values = [read_json(path) for path in paths]
    return [value for value in values if value.get("content_id") not in batch_ids]


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    production_date = sys.argv[1] if len(sys.argv) == 2 else date.today().isoformat()
    try:
        date.fromisoformat(production_date)
    except ValueError as exc:
        raise SystemExit("Usage: build_daily_trial.py [YYYY-MM-DD]") from exc
    batch_path = REPO_ROOT / "data" / "production" / f"daily-{production_date}.json"
    batch = read_json(batch_path)
    if batch.get("production_date") != production_date:
        raise ValueError("batch filename and production_date must match")
    batch_ids = {item["content_id"] for item in batch["quizzes"]} | {batch["normal"]["content_id"]}
    validate_daily_batch(batch, existing_masters(batch_ids))

    for quiz in batch["quizzes"]:
        master = MASTER_DIR / f"{quiz['content_id']}.json"
        write_json(master, quiz)
        if not quiz["visual_required"] or quiz.get("problem_image_path"):
            render_question(master)
        render_answer(master)

    normal_path = MASTER_DIR / "normal" / f"{batch['normal']['content_id']}.json"
    write_json(normal_path, batch["normal"])
    render_story(normal_path)

    status = build_daily_status(batch)
    output = REPO_ROOT / "data" / "production" / f"daily-{production_date}-status.json"
    write_json(output, status)
    review = build_daily_review_payload(batch)
    write_json(REPO_ROOT / "data" / "review" / "payloads" / f"daily-{production_date}.json", review)
    print(output)


if __name__ == "__main__":
    main()
