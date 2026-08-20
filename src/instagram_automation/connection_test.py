from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .paths import REPO_ROOT
from .posting import PublicMediaResolver
from .preflight import run_preflight

PAYLOAD_PATH = REPO_ROOT / "data" / "test_payloads" / "instagram-carousel.json"
CONFIG_PATH = REPO_ROOT / "config" / "api_test.json"


def _write_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_test_payload() -> dict:
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))
    if payload.get("content_id") != "META-TEST-INSTAGRAM-CAROUSEL":
        raise ValueError("Instagram live test requires its dedicated content_id")
    if payload.get("caption") != "API接続テスト":
        raise ValueError("Instagram live test caption mismatch")
    return payload


def execute_live_test(secrets, client, resolver: PublicMediaResolver,
                      preflight_transport=None, result_path: Path | None = None) -> dict:
    payload = load_test_payload()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    media_urls = [resolver.resolve(payload["question_image"]), resolver.resolve(payload["answer_image"])]
    preflight = run_preflight(secrets, config["required_permissions"], media_urls, preflight_transport)
    child_ids = [client.create_child_container(url) for url in media_urls]
    carousel_id = client.create_carousel_container(child_ids, payload["caption"])
    published_id = client.publish(carousel_id)
    result = {"content_id": payload["content_id"], "platform": "instagram", "preflight": preflight,
              "child_container_ids": child_ids, "carousel_container_id": carousel_id,
              "published_media_id": published_id,
              "completed_at": datetime.now(ZoneInfo("Asia/Tokyo")).isoformat()}
    target = result_path or (REPO_ROOT / config["result_path"])
    _write_atomic(target, result)
    return result
