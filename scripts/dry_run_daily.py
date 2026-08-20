#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.daily_batch import format_daily_dry_run  # noqa: E402


if __name__ == "__main__":
    status_path = REPO_ROOT / "data" / "production" / "daily-2026-08-20-status.json"
    if not status_path.is_file():
        raise SystemExit(f"Required daily status not found: {status_path}")
    status = json.loads(status_path.read_text(encoding="utf-8"))
    print(format_daily_dry_run(status))
