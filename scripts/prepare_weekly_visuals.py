#!/usr/bin/env python3
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    start = sys.argv[1] if len(sys.argv) == 2 else date.today().isoformat()
    week_path = REPO_ROOT / "data" / "production" / f"week-{start}.json"
    if not week_path.is_file():
        raise SystemExit(f"Required weekly manuscript not found: {week_path}")
    week = json.loads(week_path.read_text(encoding="utf-8"))
    requests = []
    for item in week["quizzes"]:
        if not item["visual_required"]:
            continue
        requests.append({
            "content_id": item["content_id"],
            "visual_type": item["visual_type"],
            "visual_description": item["visual_description"],
            "source_path": item.get("problem_image_path"),
            "status": "READY" if item.get("problem_image_path") else "WAITING_FOR_VISUAL",
            "constraints": ["no text", "no logos", "no watermark", "image must be essential to the question"],
        })
    payload = {
        "start_date": week["start_date"],
        "end_date": week["end_date"],
        "batch_generation": True,
        "request_count": len(requests),
        "requests": requests,
    }
    target = REPO_ROOT / "data" / "visual" / "requests" / f"week-{start}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
