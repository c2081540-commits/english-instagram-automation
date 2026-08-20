from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


class PostingError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class InstagramSecrets:
    access_token: str
    user_id: str
    api_version: str

    @classmethod
    def from_env(cls) -> "InstagramSecrets":
        names = ("INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_USER_ID", "META_GRAPH_API_VERSION")
        values = {name: os.environ.get(name, "").strip() for name in names}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise PostingError("MISSING_SECRET", f"Missing environment variables: {', '.join(missing)}")
        return cls(values[names[0]], values[names[1]], values[names[2]])


class HttpTransport:
    def __init__(self, timeout: float = 20, retries: int = 2):
        self.timeout = timeout
        self.retries = retries

    def __call__(self, url: str, fields: dict) -> dict:
        body = urllib.parse.urlencode(fields, doseq=True).encode()
        for attempt in range(self.retries + 1):
            try:
                request = urllib.request.Request(url, data=body, method="POST")
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                if not isinstance(payload, dict):
                    raise PostingError("MALFORMED_API_RESPONSE", "Meta response must be a JSON object")
                return payload
            except urllib.error.HTTPError as exc:
                exc.read()
                if exc.code in {401, 403}:
                    raise PostingError("INVALID_TOKEN", f"Meta authentication failed with HTTP {exc.code}") from exc
                if exc.code == 429 or 500 <= exc.code < 600:
                    if attempt < self.retries:
                        time.sleep(.25 * (attempt + 1))
                        continue
                    raise PostingError("NETWORK_TIMEOUT", f"Temporary Meta HTTP failure: {exc.code}") from exc
                raise PostingError("META_API_ERROR", f"Meta HTTP failure: {exc.code}") from exc
            except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                if attempt < self.retries:
                    time.sleep(.25 * (attempt + 1))
                    continue
                raise PostingError("NETWORK_TIMEOUT", "Meta network request failed or timed out") from exc
            except json.JSONDecodeError as exc:
                raise PostingError("MALFORMED_API_RESPONSE", "Meta response was not valid JSON") from exc
        raise PostingError("NETWORK_TIMEOUT", "Meta request retry limit reached")


class HttpGetTransport:
    def __init__(self, timeout: float = 20):
        self.timeout = timeout

    def __call__(self, url: str, fields: dict) -> dict:
        request_url = f"{url}?{urllib.parse.urlencode(fields)}"
        try:
            with urllib.request.urlopen(request_url, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            exc.read()
            raise PostingError("CONTAINER_STATUS_FAILURE",
                               f"Instagram container status failed with HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            raise PostingError("NETWORK_TIMEOUT", "Instagram container status request failed") from exc
        except json.JSONDecodeError as exc:
            raise PostingError("MALFORMED_API_RESPONSE", "Container status was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise PostingError("MALFORMED_API_RESPONSE", "Container status must be an object")
        return payload


class InstagramMetaClient:
    def __init__(self, secrets: InstagramSecrets, transport=None, get_transport=None,
                 sleep=None, status_attempts: int = 10):
        self.secrets = secrets
        self.transport = transport or HttpTransport()
        self.get_transport = get_transport or HttpGetTransport()
        self.sleep = sleep or time.sleep
        self.status_attempts = status_attempts
        self.base_url = f"https://graph.instagram.com/{secrets.api_version}"

    def _post(self, path: str, fields: dict, failure_code: str) -> str:
        safe_fields = dict(fields, access_token=self.secrets.access_token)
        try:
            payload = self.transport(f"{self.base_url}/{path.lstrip('/')}", safe_fields)
        except PostingError as exc:
            if exc.code in {"MISSING_SECRET", "INVALID_TOKEN", "NETWORK_TIMEOUT", "MALFORMED_API_RESPONSE"}:
                raise
            raise PostingError(failure_code, str(exc)) from exc
        except Exception as exc:
            raise PostingError(failure_code, "Meta transport failed") from exc
        remote_id = payload.get("id") if isinstance(payload, dict) else None
        if not isinstance(remote_id, str) or not remote_id:
            raise PostingError("MALFORMED_API_RESPONSE", "Meta response did not contain an id")
        return remote_id

    def create_child_container(self, image_url: str) -> str:
        return self._post(f"{self.secrets.user_id}/media",
                          {"image_url": image_url, "is_carousel_item": "true"},
                          "CONTAINER_CREATION_FAILURE")

    def create_carousel_container(self, child_ids: list[str], caption: str) -> str:
        return self._post(f"{self.secrets.user_id}/media",
                          {"media_type": "CAROUSEL", "children": ",".join(child_ids), "caption": caption},
                          "CONTAINER_CREATION_FAILURE")

    def create_story_container(self, image_url: str) -> str:
        return self._post(f"{self.secrets.user_id}/media",
                          {"media_type": "STORIES", "image_url": image_url},
                          "CONTAINER_CREATION_FAILURE")

    def wait_until_ready(self, creation_id: str) -> None:
        for attempt in range(self.status_attempts):
            payload = self.get_transport(
                f"{self.base_url}/{creation_id}",
                {"fields": "status_code,status", "access_token": self.secrets.access_token},
            )
            status = payload.get("status_code")
            if status in {"FINISHED", "PUBLISHED"}:
                return
            if status in {"ERROR", "EXPIRED"}:
                raise PostingError("CONTAINER_STATUS_FAILURE", f"Instagram container status: {status}")
            if status != "IN_PROGRESS":
                raise PostingError("MALFORMED_API_RESPONSE", "Unknown Instagram container status")
            if attempt + 1 < self.status_attempts:
                self.sleep(2)
        raise PostingError("CONTAINER_STATUS_FAILURE", "Instagram container was not ready in time")

    def publish(self, creation_id: str) -> str:
        self.wait_until_ready(creation_id)
        return self._post(f"{self.secrets.user_id}/media_publish", {"creation_id": creation_id},
                          "PUBLISH_FAILURE")
