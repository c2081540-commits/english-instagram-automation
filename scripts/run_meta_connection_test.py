#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.connection_test import execute_live_test, load_test_payload  # noqa: E402
from instagram_automation.meta_client import InstagramMetaClient, InstagramSecrets  # noqa: E402
from instagram_automation.posting import PublicMediaResolver  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-test", action="store_true", help="Post the dedicated API test fixture")
    args = parser.parse_args()
    if not args.live_test:
        payload = load_test_payload()
        print(f"DRY RUN ONLY | {payload['content_id']} | add --live-test to perform the isolated test post")
        return
    secrets = InstagramSecrets.from_env()
    result = execute_live_test(secrets, InstagramMetaClient(secrets), PublicMediaResolver())
    print(json.dumps({"content_id": result["content_id"], "published_media_id": result["published_media_id"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
