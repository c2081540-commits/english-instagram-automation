#!/usr/bin/env python3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.paths import REVIEW_DECISION_DIR, REVIEW_PAYLOAD_DIR  # noqa: E402
from instagram_automation.review import write_review_results  # noqa: E402


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(f"Usage: {Path(__file__).name} BATCH_NAME DECISION_NAME")
    paths = write_review_results(REVIEW_PAYLOAD_DIR / f"{sys.argv[1]}.json",
                                 REVIEW_DECISION_DIR / f"{sys.argv[2]}.json")
    for path in paths:
        print(path)
