import json
import os
import sys
import tempfile
import unittest
import urllib.error
from io import BytesIO
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

import instagram_automation.posting as posting
from instagram_automation.meta_client import (HttpTransport, InstagramMetaClient,
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


class ReconciliationClient(FakeInstagramClient):
    def __init__(self, matches):
        super().__init__()
        self.matches = matches

    def publish(self, creation_id):
        self.calls.append(("publish", (creation_id,)))
        raise PostingError("RATE_LIMIT", "request limited",
                           {"http_status": 403, "code": 4, "subcode": 2207051})

    def find_unique_recent_media(self, **criteria):
        self.calls.append(("reconcile_get", (criteria,)))
        return self.matches


class FakeImageResponse:
    def __init__(self, data, *, content_type="image/png", url="https://example.com/image.png"):
        self.data = data
        self.status = 200
        self.headers = {"Content-Type": content_type, "Content-Length": str(len(data))}
        self.url = url

    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return self.data
    def geturl(self): return self.url


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
        queue["status"] = "pending"
        for field in ("remote_post_id", "posted_at", "error"):
            queue.pop(field, None)
        target = self.root / f"{content_id}.json"
        target.write_text(json.dumps(queue, ensure_ascii=False), encoding="utf-8")
        return target

    def test_carousel_success_and_idempotency_fields(self):
        target = self.queue_copy("ENG-000009")
        client = FakeInstagramClient()
        result = posting.post_one(target, client, self.resolver, datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
        self.assertEqual([call[0] for call in client.calls], ["child", "child", "carousel", "publish"])
        self.assertEqual(result["status"], "posted")
        carousel_call = client.calls[2]
        self.assertEqual(carousel_call[0], "carousel")
        self.assertEqual(carousel_call[1][1],
                         "by と until、仕事の締め切りならどちらが自然でしょう？\n\n"
                         "#英語学習 #英語やり直し #英文法 #英語初心者")
        self.assertTrue(all(len(call[1]) == 1 for call in client.calls[:2]))
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

    def test_publish_error_with_unique_media_is_reconciled_without_republish(self):
        target = self.queue_copy("ENG-000009")
        client = ReconciliationClient({"id": "published-media",
                                       "timestamp": "2026-08-20T07:00:12+0000"})
        result = posting.post_one(
            target, client, self.resolver, datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
        self.assertEqual(result["status"], "posted")
        self.assertEqual(result["remote_post_id"], "published-media")
        self.assertEqual([name for name, _ in client.calls].count("publish"), 1)
        self.assertEqual([name for name, _ in client.calls].count("reconcile_get"), 1)
        receipt = json.loads((self.receipts / "instagram-ENG-000009.json").read_text())
        self.assertTrue(receipt["reconciled_after_publish_error"])
        self.assertEqual(receipt["publish_error"]["code"], "RATE_LIMIT")
        self.assertIsNone(result["error"])

    def test_publish_error_without_unique_media_remains_failed(self):
        for match in (None, None):
            target = self.queue_copy("ENG-000009")
            client = ReconciliationClient(match)
            with self.assertRaises(PostingError) as caught:
                posting.post_one(target, client, self.resolver,
                                 datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
            self.assertEqual(caught.exception.code, "RATE_LIMIT")
            self.assertEqual(json.loads(target.read_text())["status"], "failed")
            self.assertFalse((self.receipts / "instagram-ENG-000009.json").exists())
            target.unlink()

    def test_reconciled_post_is_not_due_or_recoverable(self):
        queue_dir = self.root / "queue"
        queue_dir.mkdir()
        source = REPO_ROOT / "data" / "queue" / "ENG-000039.json"
        target = queue_dir / source.name
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        now = datetime.fromisoformat("2026-08-25T16:00:00+09:00")
        self.assertIsNone(posting.select_one_due(now, queue_dir))
        with self.assertRaises(PostingError) as caught:
            posting.recover_publish(target, dry_run_only=True)
        self.assertEqual(caught.exception.code, "RECOVERY_NOT_ALLOWED")

    def test_recent_media_matching_is_exact_and_ambiguous_results_fail_closed(self):
        expected = datetime.fromisoformat("2026-08-20T16:00:00+09:00")
        base = {"caption": "approved caption", "media_type": "CAROUSEL_ALBUM",
                "media_product_type": "FEED", "timestamp": "2026-08-20T07:00:12+0000",
                "children": {"data": [{"id": "child-1"}, {"id": "child-2"}]}}
        for rows, expected_id in [([dict(base, id="one")], "one"),
                                  ([dict(base, id="one"), dict(base, id="two")], None),
                                  ([dict(base, id="one", caption="different")], None)]:
            client = InstagramMetaClient(
                InstagramSecrets("token", "user", "v25.0"),
                get_transport=lambda *_, rows=rows: {"data": rows})
            match = client.find_unique_recent_media(caption="approved caption", expected_at=expected,
                                                    expected_child_count=2)
            self.assertEqual(match and match["id"], expected_id)

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
            if failure == "publish":
                saved = json.loads((self.receipts / "instagram-ENG-000009-container.json").read_text())
                self.assertEqual(saved["container_id"], "remote-carousel-3")
            target.unlink()

    def test_failed_publish_has_safe_meta_details_and_recovery_dry_run(self):
        target = self.queue_copy("ENG-000009")
        details = {"http_status": 400, "endpoint": "https://graph.instagram.com/v25.0/user/media_publish",
                   "method": "POST", "payload": {"creation_id": "container"},
                   "message": "Container is not ready", "type": "OAuthException",
                   "code": 9007, "subcode": 2207027, "fbtrace_id": "trace"}
        client = InstagramMetaClient(
            InstagramSecrets("secret-token", "user", "v25.0"),
            transport=lambda url, fields: ({"id": "container"} if not url.endswith("media_publish")
                                           else (_ for _ in ()).throw(
                                               PostingError("META_API_ERROR", "Meta HTTP 400", details))),
            get_transport=lambda *_: {"status_code": "FINISHED"}, sleep=lambda _: None)
        with self.assertRaises(PostingError):
            posting.post_one(target, client, self.resolver,
                             datetime.fromisoformat("2026-08-20T16:00:00+09:00"))
        queue = json.loads(target.read_text())
        self.assertEqual(queue["error"]["meta"]["message"], "Container is not ready")
        self.assertEqual(queue["error"]["meta"]["subcode"], 2207027)
        self.assertNotIn("secret-token", json.dumps(queue))
        plan = posting.recover_publish(target, dry_run_only=True)
        self.assertEqual(plan["container_action"], "reuse_only")
        self.assertEqual(plan["publish_payload"], {"creation_id": "container"})

    def test_failed_repost_requires_exact_id_and_no_saved_container(self):
        target = self.queue_copy("ENG-000009")
        queue = json.loads(target.read_text())
        queue["status"] = "failed"
        queue["error"] = {"code": "PUBLISH_FAILURE", "reason": "old failure"}
        target.write_text(json.dumps(queue), encoding="utf-8")
        with self.assertRaises(PostingError) as caught:
            posting.post_one(target, FakeInstagramClient(), self.resolver,
                             datetime.fromisoformat("2026-08-20T16:00:00+09:00"),
                             failed_repost_content_id="ENG-999999")
        self.assertEqual(caught.exception.code, "DUPLICATE_PREVENTED")
        result = posting.post_one(target, FakeInstagramClient(), self.resolver,
                                  datetime.fromisoformat("2026-08-20T16:00:00+09:00"),
                                  failed_repost_content_id="ENG-000009")
        self.assertEqual(result["status"], "posted")

    def test_http_400_response_is_parsed_without_token(self):
        error_body = json.dumps({"error": {"message": "Container is not ready", "type": "OAuthException",
                                           "code": 9007, "error_subcode": 2207027,
                                           "fbtrace_id": "trace"}}).encode()
        error = urllib.error.HTTPError("https://graph.instagram.com/v25.0/user/media_publish",
                                      400, "Bad Request", {}, BytesIO(error_body))
        with patch("urllib.request.urlopen", side_effect=error), self.assertRaises(PostingError) as caught:
            HttpTransport(retries=0)("https://graph.instagram.com/v25.0/user/media_publish",
                                     {"creation_id": "container", "access_token": "secret-token"})
        self.assertEqual(caught.exception.details["message"], "Container is not ready")
        self.assertEqual(caught.exception.details["subcode"], 2207027)
        self.assertNotIn("secret-token", json.dumps(caught.exception.details))

    def test_meta_error_classification_distinguishes_rate_limit_and_authentication(self):
        cases = [
            (403, {"message": "Application request limit reached", "type": "OAuthException",
                   "code": 4, "error_subcode": 2207051}, "RATE_LIMIT"),
            (400, {"message": "Invalid OAuth access token", "type": "OAuthException",
                   "code": 190}, "AUTHENTICATION_ERROR"),
            (403, {"message": "Permission denied", "type": "OAuthException",
                   "code": 200}, "PERMISSION_ERROR"),
            (400, {"message": "Other Meta error", "type": "OAuthException",
                   "code": 100}, "META_API_ERROR"),
        ]
        for status, meta_error, expected in cases:
            body = json.dumps({"error": meta_error}).encode()
            error = urllib.error.HTTPError("https://graph.instagram.com/v25.0/user/media_publish",
                                          status, "error", {}, BytesIO(body))
            with self.subTest(expected=expected), patch("urllib.request.urlopen", side_effect=error):
                with self.assertRaises(PostingError) as caught:
                    HttpTransport(retries=0)(
                        "https://graph.instagram.com/v25.0/user/media_publish",
                        {"creation_id": "container", "access_token": "secret"})
                self.assertEqual(caught.exception.code, expected)

    def test_media_url_and_missing_secret_fail_closed(self):
        blocked = posting.PublicMediaResolver(checker=lambda _: False)
        with self.assertRaises(PostingError) as caught:
            blocked.resolve("artifacts/images/ENG-000009-question.png")
        self.assertEqual(caught.exception.code, "BLOCKED_MEDIA_URL")
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(PostingError) as caught:
            InstagramSecrets.from_env()
        self.assertEqual(caught.exception.code, "MISSING_SECRET")

    def test_public_image_preflight_gets_and_decodes_exact_approved_png(self):
        image_path = REPO_ROOT / "artifacts" / "images" / "ENG-000040-question.png"
        approved = image_path.read_bytes()
        self.assertEqual(posting.PublicMediaResolver._decode_png(approved), (1080, 1350, "RGB"))
        with patch("urllib.request.urlopen", return_value=FakeImageResponse(approved)) as opened:
            self.assertTrue(posting.PublicMediaResolver._get_and_validate(
                "https://example.com/image.png", approved))
        self.assertEqual(opened.call_args.args[0].get_method(), "GET")

        with patch("urllib.request.urlopen",
                   return_value=FakeImageResponse(approved, content_type="text/plain")):
            self.assertFalse(posting.PublicMediaResolver._get_and_validate(
                "https://example.com/image.png", approved))
        with self.assertRaises(ValueError):
            posting.PublicMediaResolver._decode_png(b"not a png")

    def test_github_actions_uses_immutable_raw_commit_url(self):
        sha = "a" * 40
        with patch.dict(os.environ, {"GITHUB_SHA": sha}):
            resolver = posting.PublicMediaResolver(checker=lambda _: True)
            url = resolver.resolve("artifacts/images/ENG-000040-question.png")
        self.assertIn(f"/{sha}/artifacts/images/ENG-000040-question.png", url)
        self.assertNotIn("/main/", url)

    def test_malformed_queue_and_placeholder_fail_closed(self):
        queue = json.loads(self.queue_copy("ENG-000009").read_text())
        queue["carousel"] = list(reversed(queue["carousel"]))
        with self.assertRaises(PostingError):
            posting.validate_queue_for_post(queue)
        with self.assertRaises(PostingError) as caught:
            self.resolver.resolve("assets/source/ice-cream-placeholder.png")
        self.assertEqual(caught.exception.code, "BLOCKED_MEDIA_URL")

    def test_due_selector_excludes_hold_future_and_posted(self):
        queue_dir = self.root / "queue"
        queue_dir.mkdir()
        source_ids = ("ENG-000006", "ENG-000007", "ENG-000009")
        for content_id in source_ids:
            queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text(encoding="utf-8"))
            if content_id == "ENG-000009":
                queue["status"] = "pending"
                queue.pop("remote_post_id", None)
                queue.pop("posted_at", None)
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
                                     transport=lambda *_: (_ for _ in ()).throw(PostingError("INVALID_TOKEN", "invalid token")),
                                     get_transport=lambda *_: {"status_code": "FINISHED"})
        with self.assertRaises(PostingError) as caught:
            client.publish("container")
        self.assertNotIn(token, str(caught.exception))

    def test_instagram_login_host_is_used_for_content_publishing(self):
        calls = []
        client = InstagramMetaClient(InstagramSecrets("token", "user", "v25.0"),
                                     transport=lambda url, fields: calls.append(url) or {"id": "remote"},
                                     get_transport=lambda *_: {"status_code": "FINISHED"})
        child = client.create_child_container("https://example.com/question.png")
        carousel = client.create_carousel_container([child], "caption")
        client.create_story_container("https://example.com/story.png")
        client.publish(carousel)
        self.assertEqual(calls, [
            "https://graph.instagram.com/v25.0/user/media",
            "https://graph.instagram.com/v25.0/user/media",
            "https://graph.instagram.com/v25.0/user/media",
            "https://graph.instagram.com/v25.0/user/media_publish",
        ])

    def test_publish_waits_for_container_and_is_finite(self):
        statuses = iter([{"status_code": "IN_PROGRESS"}, {"status_code": "FINISHED"}])
        posts = []
        client = InstagramMetaClient(
            InstagramSecrets("token", "user", "v25.0"),
            transport=lambda url, fields: posts.append(url) or {"id": "published"},
            get_transport=lambda *_: next(statuses), sleep=lambda _: None,
            status_attempts=2, status_interval=60)
        self.assertEqual(client.publish("carousel"), "published")
        self.assertEqual(posts, ["https://graph.instagram.com/v25.0/user/media_publish"])

        blocked = InstagramMetaClient(
            InstagramSecrets("token", "user", "v25.0"),
            transport=lambda *_: {"id": "must-not-publish"},
            get_transport=lambda *_: {"status_code": "IN_PROGRESS"},
            sleep=lambda _: None, status_attempts=2, status_interval=60)
        with self.assertRaises(PostingError) as caught:
            blocked.publish("carousel")
        self.assertEqual(caught.exception.code, "CONTAINER_STATUS_FAILURE")

        published = InstagramMetaClient(
            InstagramSecrets("token", "user", "v25.0"),
            transport=lambda *_: {"id": "must-not-publish"},
            get_transport=lambda *_: {"status_code": "PUBLISHED"}, sleep=lambda _: None)
        with self.assertRaises(PostingError) as caught:
            published.publish("carousel")
        self.assertEqual(caught.exception.code, "DUPLICATE_PREVENTED")


if __name__ == "__main__":
    unittest.main()
