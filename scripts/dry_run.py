#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.paths import QUEUE_DIR  # noqa: E402


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: {Path(__file__).name} CONTENT_ID")
    queue_path = QUEUE_DIR / f"{sys.argv[1]}.json"
    if not queue_path.is_file():
        raise SystemExit(f"Required queue file not found: {queue_path}")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    print(f"DRY RUN Instagram | {queue['content_id']} | {queue['publish_at']} | status={queue['status']}")
    for item in queue["carousel"]:
        print(f"{item['order']}. {item['role']} image={item['image_path']}")
    print(f"caption={queue['caption']}")
