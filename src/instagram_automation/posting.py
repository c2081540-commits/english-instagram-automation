from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from .meta_client import PostingError
from .hashtags import HashtagConfigError, build_final_caption
from .paths import QUEUE_DIR, REPO_ROOT

MEDIA_CONFIG = REPO_ROOT / "config" / "media_public.json"
RECEIPT_DIR = REPO_ROOT / "data" / "receipts"
MASTER_DIR = REPO_ROOT / "data" / "master"


def _write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


class PublicMediaResolver:
    def __init__(self, checker=None):
        config = json.loads(MEDIA_CONFIG.read_text(encoding="utf-8"))
        self.base_url = config["base_url"]
        self.require_https = config["require_https"]
        self.verify_remote = config["verify_remote_before_post"]
        self.checker = checker or self._head

    @staticmethod
    def _head(url: str) -> bool:
        try:
            request = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(request, timeout=15) as response:
                return 200 <= response.status < 400
        except (urllib.error.URLError, TimeoutError):
            return False

    def resolve(self, asset: str) -> str:
        local = Path(asset)
        resolved = local.resolve() if local.is_absolute() else (REPO_ROOT / local).resolve()
        try:
            relative = resolved.relative_to(REPO_ROOT)
        except ValueError as exc:
            raise PostingError("BLOCKED_MEDIA_URL", "Media asset must be inside the repository") from exc
        if not resolved.is_file():
            raise PostingError("BLOCKED_MEDIA_URL", f"Media asset is missing: {relative.as_posix()}")
        url = urljoin(self.base_url, relative.as_posix())
        if self.require_https and urlparse(url).scheme != "https":
            raise PostingError("BLOCKED_MEDIA_URL", "Public media URL must use HTTPS")
        if self.verify_remote and not self.checker(url):
            raise PostingError("BLOCKED_MEDIA_URL", "Public media URL is not anonymously reachable")
        return url


def select_one_due(now: datetime, queue_dir: Path = QUEUE_DIR) -> Path | None:
    candidates = []
    for path in queue_dir.glob("ENG-*.json"):
        queue = json.loads(path.read_text(encoding="utf-8"))
        if (queue.get("platform") == "instagram" and queue.get("status") == "pending" and
                queue.get("execution_eligibility") == "scheduled"):
            publish_at = datetime.fromisoformat(queue["publish_at"])
            if publish_at <= now:
                candidates.append((publish_at, queue["content_id"], path))
    return min(candidates)[2] if candidates else None


def dry_run(queue: dict, resolver: PublicMediaResolver) -> str:
    if queue["content_type"] == "quiz":
        assets = [resolver.resolve(slide["image_path"]) for slide in queue["carousel"]]
        final_caption = final_quiz_caption(queue)
        flow = "child(question) -> child(answer) -> carousel container -> publish"
        return (f"{queue['content_id']} | instagram | {queue['publish_at']} | carousel Quiz | "
                f"assets={assets} | caption=yes | hashtags={final_caption.count('#')} | {flow}")
    asset = resolver.resolve(queue["story_image"])
    return (f"{queue['content_id']} | instagram | {queue['publish_at']} | Story Normal | "
            f"asset={asset} | caption=no | story container -> publish")


def final_quiz_caption(queue: dict) -> str:
    master_path = MASTER_DIR / f"{queue.get('content_id', '')}.json"
    if not master_path.is_file():
        raise PostingError("INVALID_HASHTAG_CONFIG", "Quiz master is missing for final caption")
    master = json.loads(master_path.read_text(encoding="utf-8"))
    if queue.get("caption") != master.get("instagram_caption"):
        raise PostingError("CAPTION_MISMATCH", "Queue caption does not match the approved master caption")
    try:
        return build_final_caption(queue["caption"], master.get("production_category"))
    except (HashtagConfigError, KeyError) as exc:
        raise PostingError("INVALID_HASHTAG_CONFIG", str(exc)) from exc


def post_one(queue_path: Path, client, resolver: PublicMediaResolver,
             now: datetime | None = None) -> dict:
    now = now or datetime.now(ZoneInfo("Asia/Tokyo"))
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    if queue.get("status") != "pending":
        raise PostingError("DUPLICATE_PREVENTED", "Only pending content may be posted")
    if queue.get("execution_eligibility") != "scheduled" or datetime.fromisoformat(queue["publish_at"]) > now:
        raise PostingError("NOT_DUE", "Queue item is not eligible and due")
    receipt_path = RECEIPT_DIR / f"instagram-{queue['content_id']}.json"
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        queue.update(status="posted", remote_post_id=receipt["remote_post_id"], posted_at=receipt["posted_at"])
        _write_json_atomic(queue_path, queue)
        return queue
    try:
        if queue["content_type"] == "quiz":
            child_ids = [client.create_child_container(resolver.resolve(slide["image_path"]))
                         for slide in queue["carousel"]]
            container_id = client.create_carousel_container(child_ids, final_quiz_caption(queue))
        else:
            container_id = client.create_story_container(resolver.resolve(queue["story_image"]))
        remote_id = client.publish(container_id)
        posted_at = now.isoformat()
        _write_json_atomic(receipt_path, {"content_id": queue["content_id"], "platform": "instagram",
                                         "remote_post_id": remote_id, "posted_at": posted_at})
        queue.update(status="posted", remote_post_id=remote_id, posted_at=posted_at, error=None)
        _write_json_atomic(queue_path, queue)
        return queue
    except PostingError as exc:
        queue.update(status="failed", error={"code": exc.code, "reason": str(exc)[:200]})
        _write_json_atomic(queue_path, queue)
        raise
