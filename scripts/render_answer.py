#!/usr/bin/env python3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.answer_renderer import render_answer  # noqa: E402
from instagram_automation.paths import MASTER_DIR  # noqa: E402


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: {Path(__file__).name} CONTENT_ID")
    print(render_answer(MASTER_DIR / f"{sys.argv[1]}.json"))
