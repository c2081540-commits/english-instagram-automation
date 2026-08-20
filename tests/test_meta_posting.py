import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import instagram_automation.posting as posting
from instagram_automation.meta_client import (InstagramMetaClient,
                                               InstagramSecrets, PostingError)


class FakeInstagramClient:
    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at

    def _call(self, name, *args):
        self.calls.append((name, args))
        if self.fail_at == name:
            code = "PUBLISH_FAILURE" if name == "publish" else "CONTAINER_CREATION_FAILURE"
            raise PostingError(code, f"mock {name} failure")
        return f"remote-{name}-{len(self.calls)}"

    def create_child_container(self, url): return self._call("child", url)
    def create_carousel_container(self, children, caption): return self._call("carousel", children, caption)
    def create_story_container(self, url): return self._call("story", url)
    def publish(self, creation_id): return self._call("publish", creation_id)


class InstagramMetaPostingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.receipts = self.root / "receipts"
        self.receipt_patch = patch.object(posting, "RECEIPT_DIR", self.receipts)
        self.receipt_patch.start()
        self.resolver = posting.PublicMediaResolver(checker=lambda _: True)

    def tearDown(self):
        self.receipt_patch.stop()
        self.temporary.cleanup()

    def queue_copy(self, content_id):
        queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text(encoding="utf-8"))
        queue["execution_eligibility"] = "scheduled"
        target = self.root / f"{content_id}.json"
        target.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
        return target

    def test_carousel_success_and_idempotency_fields(self):
        target = self.queue_copy("ENG-000009")
        client = FakeInstagramClient()
        result = posting.post_one(target, client, self.resolver, datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
        self.assertEqual([call[0] for call in client.calls], ["child", "child", "carousel", "publish"])
        self.assertEqual(result["status"], "posted")
        self.assertTrue(result["remote_post_id"])
        self.assertTrue(result["posted_at"])
        with self.assertRaisesRegex(PostingError, "Only pending"):
            posting.post_one(target, client, self.resolver, datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
        self.assertEqual(len(client.calls), 4)

    def test_story_success(self):
        target = self.queue_copy("ENG-100002")
        client = FakeInstagramClient()
        result = posting.post_one(target, client, self.resolver, datetime.fromisoformat("2026-08-21T00:00:00+09:00"))
        self.assertEqual([call[0] for call in client.calls], ["story", "publish"])
        self.assertEqual(result["status"], "posted")

    def test_dry_run_covers_carousel_and_story_without_secrets(self):
        quiz = json.loads(self.queue_copy("ENG-000009").read_text())
        story = json.loads(self.queue_copy("ENG-100002").read_text())
        self.assertIn("child(question) -> child(answer) -> carousel container -> publish",
                      posting.dry_run(quiz, self.resolver))
        self.assertIn("story container -> publish", posting.dry_run(story, self.resolver))

    def test_child_and_publish_failures_are_distinct(self):
        for failure, expected in (("child", "CONTAINER_CREATION_FAILURE"), ("publish", "PUBLISH_FAILURE")):
            target = self.queue_copy("ENG-000009")
            with self.subTest(failure=failure), self.assertRaises(PostingError) as caught:
                posting.post_one(target, FakeInstagramClient(failure), self.resolver,
                                 datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
            self.assertEqual(caught.exception.code, expected)
            target.unlink()

    def test_media_url_and_missing_secret_fail_closed(self):
        blocked = posting.PublicMediaResolver(checker=lambda _: False)
        with self.assertRaises(PostingError) as caught:
            blocked.resolve("artifacts/images/ENG-000009-question.png")
        self.assertEqual(caught.exception.code, "BLOCKED_MEDIA_URL")
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(PostingError) as caught:
            InstagramSecrets.from_env()
        self.assertEqual(caught.exception.code, "MISSING_SECRET")

    def test_due_selector_excludes_hold_future_and_posted(self):
        queue_dir = self.root / "queue"
        queue_dir.mkdir()
        source_ids = ("ENG-000006", "ENG-000007", "ENG-000009")
        for content_id in source_ids:
            queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text(encoding="utf-8"))
            (queue_dir / f"{content_id}.json").write_text(json.dumps(queue), encoding="utf-8")
        self.assertIsNone(posting.select_one_due(datetime.fromisoformat("2026-08-20T14:00:00+09:00"), queue_dir))
        selected = posting.select_one_due(datetime.fromisoformat("2026-08-20T16:00:00+09:00"), queue_dir)
        self.assertEqual(selected.stem, "ENG-000009")
        queue = json.loads(selected.read_text())
        queue["status"] = "posted"
        selected.write_text(json.dumps(queue), encoding="utf-8")
        self.assertIsNone(posting.select_one_due(datetime.fromisoformat("2026-08-20T16:00:00+09:00"), queue_dir))

    def test_token_is_not_exposed_by_client_error(self):
        token = "super-secret-token"
        client = InstagramMetaClient(InstagramSecrets(token, "user", "v1"),
                                     transport=lambda *_: (_ for _ in ()).throw(PostingError("INVALID_TOKEN", "invalid token")))
        with self.assertRaises(PostingError) as caught:
            client.publish("container")
        self.assertNotIn(token, str(caught.exception))


if __name__ == "__main__":
    unittest.main()
