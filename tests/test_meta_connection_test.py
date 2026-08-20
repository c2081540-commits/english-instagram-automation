import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.connection_test import execute_live_test
from instagram_automation.local_env import load_workspace_env
from instagram_automation.meta_client import InstagramSecrets, PostingError
from instagram_automation.posting import PublicMediaResolver
from instagram_automation.preflight import run_preflight


class FixtureClient:
    def __init__(self): self.calls = []
    def create_child_container(self, url): self.calls.append(("child", url)); return f"child-{len(self.calls)}"
    def create_carousel_container(self, ids, caption): self.calls.append(("carousel", ids, caption)); return "carousel-id"
    def publish(self, creation_id): self.calls.append(("publish", creation_id)); return "published-id"


def preflight_transport(url, fields):
    if url.endswith("/instagram-user-id"):
        return {"id": "instagram-user-id", "username": "test"}
    return {"data": [{"quota_usage": 0, "config": {"quota_total": 100}}]}


class InstagramConnectionTestTests(unittest.TestCase):
    def test_workspace_env_loader_does_not_override_process_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("INSTAGRAM_ACCESS_TOKEN=file-token\nINSTAGRAM_USER_ID=file-user\n")
            previous = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
            os.environ["INSTAGRAM_ACCESS_TOKEN"] = "process-token"
            os.environ.pop("INSTAGRAM_USER_ID", None)
            try:
                load_workspace_env(path)
                self.assertEqual(os.environ["INSTAGRAM_ACCESS_TOKEN"], "process-token")
                self.assertEqual(os.environ["INSTAGRAM_USER_ID"], "file-user")
            finally:
                if previous is None:
                    os.environ.pop("INSTAGRAM_ACCESS_TOKEN", None)
                else:
                    os.environ["INSTAGRAM_ACCESS_TOKEN"] = previous
                os.environ.pop("INSTAGRAM_USER_ID", None)

    def test_mock_live_test_saves_all_container_and_media_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            client = FixtureClient()
            result = execute_live_test(
                InstagramSecrets("secret-not-logged", "instagram-user-id", "v1"), client,
                PublicMediaResolver(checker=lambda _: True), preflight_transport,
                Path(directory) / "result.json")
            self.assertEqual(result["child_container_ids"], ["child-1", "child-2"])
            self.assertEqual(result["carousel_container_id"], "carousel-id")
            self.assertEqual(result["published_media_id"], "published-id")
            saved = json.loads((Path(directory) / "result.json").read_text())
            self.assertNotIn("secret-not-logged", json.dumps(saved))

    def test_missing_permission_blocks_before_post(self):
        def missing_permissions(url, fields):
            return ({"id": "instagram-user-id"} if url.endswith("/instagram-user-id")
                    else {"error": "permission denied"})
        with self.assertRaises(PostingError) as caught:
            run_preflight(InstagramSecrets("token", "instagram-user-id", "v1"),
                          ["instagram_business_basic", "instagram_business_content_publish"], [], missing_permissions)
        self.assertEqual(caught.exception.code, "MISSING_PERMISSION")

    def test_preflight_uses_instagram_login_host(self):
        urls = []
        def transport(url, fields):
            urls.append(url)
            return ({"id": "instagram-user-id"} if url.endswith("/instagram-user-id") else
                    {"data": [{"quota_usage": 0}]})
        run_preflight(InstagramSecrets("token", "instagram-user-id", "v25.0"),
                      ["instagram_business_basic"], [], transport)
        self.assertEqual(urls, ["https://graph.instagram.com/v25.0/instagram-user-id",
                                "https://graph.instagram.com/v25.0/instagram-user-id/content_publishing_limit"])

    def test_flag_is_required_and_production_queue_stays_pending(self):
        result = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "run_meta_connection_test.py")],
                                check=True, capture_output=True, text=True)
        self.assertIn("DRY RUN ONLY", result.stdout)
        queues = [json.loads(path.read_text()) for path in (REPO_ROOT / "data" / "queue").glob("ENG-*.json")]
        production = [item for item in queues if item.get("platform") == "instagram"]
        self.assertEqual(len(production), 49)
        self.assertTrue(all(item["status"] == "pending" and "remote_post_id" not in item for item in production))


if __name__ == "__main__":
    unittest.main()
