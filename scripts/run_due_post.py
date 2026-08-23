#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.meta_client import InstagramMetaClient, InstagramSecrets  # noqa: E402
from instagram_automation.posting import PublicMediaResolver, dry_run, post_one, select_one_due  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Actually call Meta API; omitted means dry-run")
    parser.add_argument("--now", help="ISO 8601 override for deterministic dry-run")
    parser.add_argument("--repost-failed-content-id",
                        help="Explicitly create a new post for exactly one failed content_id")
    args = parser.parse_args()
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(ZoneInfo("Asia/Tokyo"))
    if args.repost_failed_content_id:
        if not args.live:
            raise SystemExit("--repost-failed-content-id requires --live")
        path = REPO_ROOT / "data" / "queue" / f"{args.repost_failed_content_id}.json"
        if not path.is_file():
            raise SystemExit("Requested failed queue does not exist")
    else:
        path = select_one_due(now)
    if path is None:
        print("NO_DUE_ITEM")
        return
    queue = json.loads(path.read_text(encoding="utf-8"))
    resolver = PublicMediaResolver() if args.live else PublicMediaResolver(checker=lambda _: True)
    if not args.live:
        print(dry_run(queue, resolver))
        return
    client = InstagramMetaClient(InstagramSecrets.from_env())
    result = post_one(path, client, resolver, now,
                      failed_repost_content_id=args.repost_failed_content_id)
    print(json.dumps({"content_id": result["content_id"], "status": result["status"],
                      "remote_post_id": result["remote_post_id"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
