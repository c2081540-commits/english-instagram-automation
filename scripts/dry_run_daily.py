#!/usr/bin/env python3
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.daily_batch import format_daily_dry_run  # noqa: E402


if __name__ == "__main__":
    production_date = sys.argv[1] if len(sys.argv) == 2 else date.today().isoformat()
    try:
        date.fromisoformat(production_date)
    except ValueError as exc:
        raise SystemExit("Usage: dry_run_daily.py [YYYY-MM-DD]") from exc
    status_path = REPO_ROOT / "data" / "production" / f"daily-{production_date}-status.json"
    if not status_path.is_file():
        raise SystemExit(f"Required daily status not found: {status_path}")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    print(format_daily_dry_run(status))
