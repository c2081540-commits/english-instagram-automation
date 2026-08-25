from __future__ import annotations

import json
import os
import re
import struct
import urllib.error
import urllib.request
import zlib
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


def validate_queue_for_post(queue: dict) -> None:
    if not isinstance(queue, dict):
        raise PostingError("MALFORMED_QUEUE", "Queue root must be an object")
    if queue.get("platform") != "instagram":
        raise PostingError("MALFORMED_QUEUE", "Queue platform must be instagram")
    if queue.get("content_type") not in {"quiz", "normal"}:
        raise PostingError("MALFORMED_QUEUE", "Unsupported Instagram content_type")
    try:
        publish_at = datetime.fromisoformat(queue["publish_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PostingError("MALFORMED_QUEUE", "publish_at must be ISO 8601") from exc
    if publish_at.tzinfo is None:
        raise PostingError("MALFORMED_QUEUE", "publish_at must include timezone")
    if queue.get("status") == "pending" and queue.get("remote_post_id"):
        raise PostingError("DUPLICATE_PREVENTED", "Pending queue already has a remote_post_id")
    if queue["content_type"] == "quiz":
        carousel = queue.get("carousel")
        roles = [(item.get("order"), item.get("role")) for item in carousel or []
                 if isinstance(item, dict)]
        if roles != [(1, "question"), (2, "answer")] or not all(
                isinstance(item.get("image_path"), str) and item["image_path"] for item in carousel or []):
            raise PostingError("MALFORMED_QUEUE", "Quiz carousel must be question then answer")
        if not isinstance(queue.get("caption"), str) or not queue["caption"].strip():
            raise PostingError("MALFORMED_QUEUE", "Quiz caption is required")
        expected = [f"{queue.get('content_id')}-question.png", f"{queue.get('content_id')}-answer.png"]
        if [Path(item["image_path"]).name for item in carousel] != expected:
            raise PostingError("MALFORMED_QUEUE", "Carousel assets do not match content_id")
    elif not isinstance(queue.get("story_image"), str) or not queue["story_image"]:
        raise PostingError("MALFORMED_QUEUE", "Story image is required")
    elif Path(queue["story_image"]).name != f"{queue.get('content_id')}-story.png":
        raise PostingError("MALFORMED_QUEUE", "Story asset does not match content_id")


def _write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _safe_error(exc: PostingError, code: str | None = None) -> dict:
    result = {"code": code or exc.code, "reason": str(exc)[:500]}
    if exc.details:
        result["meta"] = exc.details
    return result


def _publish_error_may_have_succeeded(exc: PostingError) -> bool:
    return exc.code in {"RATE_LIMIT", "NETWORK_TIMEOUT"}


def _reconcile_quiz_publish(client, *, caption: str, expected_at: datetime,
                            publish_error: PostingError) -> dict | None:
    if not _publish_error_may_have_succeeded(publish_error):
        return None
    finder = getattr(client, "find_unique_recent_media", None)
    if not callable(finder):
        return None
    return finder(caption=caption, expected_at=expected_at,
                  media_type="CAROUSEL_ALBUM", media_product_type="FEED",
                  expected_child_count=2)


class PublicMediaResolver:
    def __init__(self, checker=None):
        config = json.loads(MEDIA_CONFIG.read_text(encoding="utf-8"))
        self.base_url = self._immutable_raw_base(config["base_url"])
        self.require_https = config["require_https"]
        self.verify_remote = config["verify_remote_before_post"]
        self.checker = checker

    @staticmethod
    def _immutable_raw_base(base_url: str) -> str:
        checkout_sha = os.environ.get("GITHUB_SHA", "").strip()
        if (re.fullmatch(r"[0-9a-fA-F]{40}", checkout_sha) and
                base_url.startswith("https://raw.githubusercontent.com/") and "/main/" in base_url):
            return base_url.replace("/main/", f"/{checkout_sha}/", 1)
        return base_url

    @staticmethod
    def _decode_png(data: bytes) -> tuple[int, int, str]:
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("invalid PNG signature")
        offset = 8
        width = height = bit_depth = color_type = interlace = None
        idat = []
        saw_iend = False
        while offset + 12 <= len(data):
            length = struct.unpack(">I", data[offset:offset + 4])[0]
            chunk_type = data[offset + 4:offset + 8]
            chunk = data[offset + 8:offset + 8 + length]
            crc_bytes = data[offset + 8 + length:offset + 12 + length]
            if len(chunk) != length or len(crc_bytes) != 4:
                raise ValueError("truncated PNG chunk")
            expected_crc = struct.unpack(">I", crc_bytes)[0]
            if zlib.crc32(chunk_type + chunk) & 0xffffffff != expected_crc:
                raise ValueError("invalid PNG CRC")
            if chunk_type == b"IHDR":
                if length != 13:
                    raise ValueError("invalid PNG IHDR")
                width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(
                    ">IIBBBBB", chunk)
                if (bit_depth, color_type, compression, filtering, interlace) != (8, 2, 0, 0, 0):
                    raise ValueError("PNG must be non-interlaced 8-bit RGB")
            elif chunk_type == b"IDAT":
                idat.append(chunk)
            elif chunk_type == b"IEND":
                saw_iend = True
                break
            offset += 12 + length
        if not saw_iend or not width or not height or not idat:
            raise ValueError("incomplete PNG")
        decoded = zlib.decompress(b"".join(idat))
        if len(decoded) != height * (1 + width * 3):
            raise ValueError("PNG pixel data did not decode to RGB dimensions")
        return width, height, "RGB"

    @classmethod
    def _get_and_validate(cls, url: str, local_bytes: bytes) -> bool:
        for _attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "english-instagram-preflight/1"},
                                                 method="GET")
                with urllib.request.urlopen(request, timeout=20) as response:
                    remote_bytes = response.read()
                    content_type = (response.headers.get("Content-Type") or "").split(";", 1)[0].lower()
                    content_length = response.headers.get("Content-Length")
                    final_url = response.geturl()
                    if response.status != 200 or not content_type.startswith("image/"):
                        continue
                    if urlparse(final_url).scheme != "https":
                        continue
                    if content_length is not None and int(content_length) != len(remote_bytes):
                        continue
                    if remote_bytes != local_bytes:
                        continue
                    cls._decode_png(remote_bytes)
                    return True
            except (urllib.error.URLError, TimeoutError, ValueError, zlib.error):
                continue
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
        if "placeholder" in relative.as_posix().casefold() or "dummy" in relative.as_posix().casefold():
            raise PostingError("BLOCKED_MEDIA_URL", "Placeholder or dummy media is prohibited")
        url = urljoin(self.base_url, relative.as_posix())
        if self.require_https and urlparse(url).scheme != "https":
            raise PostingError("BLOCKED_MEDIA_URL", "Public media URL must use HTTPS")
        if self.verify_remote:
            valid = self.checker(url) if self.checker is not None else self._get_and_validate(
                url, resolved.read_bytes())
            if not valid:
                raise PostingError("BLOCKED_MEDIA_URL",
                                   "Public media URL did not return the approved decodable image")
        return url


def select_one_due(now: datetime, queue_dir: Path = QUEUE_DIR) -> Path | None:
    candidates = []
    for path in queue_dir.glob("ENG-*.json"):
        queue = json.loads(path.read_text(encoding="utf-8"))
        if queue.get("platform") == "instagram":
            validate_queue_for_post(queue)
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
             now: datetime | None = None, *, failed_repost_content_id: str | None = None) -> dict:
    now = now or datetime.now(ZoneInfo("Asia/Tokyo"))
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    validate_queue_for_post(queue)
    is_explicit_failed_repost = (queue.get("status") == "failed" and
                                 queue.get("content_id") == failed_repost_content_id)
    if queue.get("status") != "pending" and not is_explicit_failed_repost:
        raise PostingError("DUPLICATE_PREVENTED", "Only pending content may be posted")
    if queue.get("execution_eligibility") != "scheduled" or datetime.fromisoformat(queue["publish_at"]) > now:
        raise PostingError("NOT_DUE", "Queue item is not eligible and due")
    receipt_path = RECEIPT_DIR / f"instagram-{queue['content_id']}.json"
    container_receipt_path = RECEIPT_DIR / f"instagram-{queue['content_id']}-container.json"
    if is_explicit_failed_repost and container_receipt_path.is_file():
        raise PostingError("DUPLICATE_PREVENTED",
                           "Failed repost cannot replace an existing container receipt")
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
            container_receipt = {"content_id": queue["content_id"], "platform": "instagram",
                                 "child_container_ids": child_ids,
                                 "container_id": container_id, "container_type": "carousel",
                                 "stage": "container_created", "created_at": now.isoformat()}
        else:
            container_id = client.create_story_container(resolver.resolve(queue["story_image"]))
            container_receipt = {"content_id": queue["content_id"], "platform": "instagram",
                                 "container_id": container_id, "container_type": "story",
                                 "stage": "container_created", "created_at": now.isoformat()}
        _write_json_atomic(container_receipt_path, container_receipt)
        approved_caption = final_quiz_caption(queue) if queue["content_type"] == "quiz" else None
        try:
            remote_id = client.publish(container_id)
        except PostingError as publish_error:
            try:
                matched = (_reconcile_quiz_publish(client, caption=approved_caption,
                                                   expected_at=now, publish_error=publish_error)
                           if approved_caption is not None else None)
            except PostingError as reconciliation_error:
                details = dict(publish_error.details)
                details["reconciliation_error"] = _safe_error(reconciliation_error)
                raise PostingError(publish_error.code, str(publish_error), details) from publish_error
            if matched is None:
                raise
            remote_id = matched["id"]
            posted_at = matched["timestamp"]
            audit = _safe_error(publish_error)
            receipt = {"content_id": queue["content_id"], "platform": "instagram",
                       "remote_post_id": remote_id, "posted_at": posted_at,
                       "reconciled_after_publish_error": True,
                       "reconciliation_source": "instagram_recent_media_get",
                       "container_id": container_id, "publish_error": audit}
            _write_json_atomic(receipt_path, receipt)
            history = list(queue.get("audit_history") or [])
            history.append({"event": "publish_error_reconciled_as_posted",
                            "recorded_at": now.isoformat(), "publish_error": audit})
            queue.update(status="posted", remote_post_id=remote_id, posted_at=posted_at,
                         error=None, audit_history=history)
            _write_json_atomic(queue_path, queue)
            return queue
        posted_at = now.isoformat()
        _write_json_atomic(receipt_path, {"content_id": queue["content_id"], "platform": "instagram",
                                         "remote_post_id": remote_id, "posted_at": posted_at})
        queue.update(status="posted", remote_post_id=remote_id, posted_at=posted_at, error=None)
        _write_json_atomic(queue_path, queue)
        return queue
    except PostingError as exc:
        queue.update(status="failed", error=_safe_error(exc))
        _write_json_atomic(queue_path, queue)
        raise


def recover_publish(queue_path: Path, client=None, *, dry_run_only: bool = True,
                    now: datetime | None = None) -> dict:
    """Resume a failed item from its saved container without creating new media."""
    now = now or datetime.now(ZoneInfo("Asia/Tokyo"))
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    validate_queue_for_post(queue)
    if queue.get("status") != "failed":
        raise PostingError("RECOVERY_NOT_ALLOWED", "Publish recovery requires failed status")
    receipt_path = RECEIPT_DIR / f"instagram-{queue['content_id']}.json"
    container_path = RECEIPT_DIR / f"instagram-{queue['content_id']}-container.json"
    if receipt_path.is_file():
        raise PostingError("DUPLICATE_PREVENTED", "Final receipt already exists")
    if not container_path.is_file():
        raise PostingError("RECOVERY_NOT_ALLOWED", "Saved Instagram container is required")
    saved = json.loads(container_path.read_text(encoding="utf-8"))
    container_id = saved.get("container_id")
    if saved.get("content_id") != queue.get("content_id") or not isinstance(container_id, str) or not container_id:
        raise PostingError("RECOVERY_NOT_ALLOWED", "Container receipt does not match queue")
    plan = {
        "content_id": queue["content_id"], "container_id": container_id,
        "container_action": "reuse_only",
        "status_endpoint": f"https://graph.instagram.com/<VERSION>/{container_id}?fields=status_code",
        "publish_endpoint": "https://graph.instagram.com/<VERSION>/<IG_ID>/media_publish",
        "publish_payload": {"creation_id": container_id},
    }
    if dry_run_only:
        return plan
    if client is None:
        raise PostingError("RECOVERY_NOT_ALLOWED", "Live recovery requires a Meta client")
    remote_id = client.publish(container_id)
    posted_at = now.isoformat()
    _write_json_atomic(receipt_path, {"content_id": queue["content_id"],
                                     "platform": "instagram", "remote_post_id": remote_id,
                                     "posted_at": posted_at, "recovered_from_container": container_id})
    queue.update(status="posted", remote_post_id=remote_id, posted_at=posted_at, error=None)
    _write_json_atomic(queue_path, queue)
    return queue
