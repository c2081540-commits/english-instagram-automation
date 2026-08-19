#!/usr/bin/env python3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.paths import MASTER_DIR  # noqa: E402
from instagram_automation.review import machine_check, save_machine_reject, write_review_batch  # noqa: E402


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(f"Usage: {Path(__file__).name} CONTENT_ID [CONTENT_ID ...]")
    results = [machine_check(MASTER_DIR / f"{content_id}.json") for content_id in sys.argv[1:]]
    rejected = [result for result in results if result.status == "REJECT"]
    for result in results:
        print(f"{result.status} {result.content_id}" + (f": {result.reason}" if result.reason else ""))
    for result in rejected:
        save_machine_reject(result)
    passed = [result for result in results if result.status == "PASS"]
    if passed:
        print(write_review_batch(passed))
    if rejected:
        raise SystemExit(1)
