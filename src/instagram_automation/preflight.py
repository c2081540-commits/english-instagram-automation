from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request

from .meta_client import PostingError


class GetTransport:
    def __init__(self, timeout: float = 20):
        self.timeout = timeout

    def __call__(self, url: str, fields: dict) -> dict:
        request_url = f"{url}?{urllib.parse.urlencode(fields)}"
        try:
            with urllib.request.urlopen(request_url, timeout=self.timeout) as response:
                value = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            exc.read()
            code = "INVALID_TOKEN" if exc.code in {401, 403} else "PREFLIGHT_API_FAILURE"
            raise PostingError(code, f"Meta preflight failed with HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            raise PostingError("NETWORK_TIMEOUT", "Meta preflight network request failed") from exc
        except json.JSONDecodeError as exc:
            raise PostingError("MALFORMED_API_RESPONSE", "Meta preflight response was not valid JSON") from exc
        if not isinstance(value, dict):
            raise PostingError("MALFORMED_API_RESPONSE", "Meta preflight response must be an object")
        return value


def run_preflight(secrets, required_permissions: list[str], media_urls: list[str], transport=None) -> dict:
    get = transport or GetTransport()
    base = f"https://graph.instagram.com/{secrets.api_version}"
    user = get(f"{base}/{secrets.user_id}", {"fields": "id,username", "access_token": secrets.access_token})
    if str(user.get("id")) != secrets.user_id:
        raise PostingError("USER_ID_MISMATCH", "Configured Instagram User ID was not returned by Meta")
    permissions_response = get(
        f"{base}/{secrets.user_id}/content_publishing_limit",
        {"fields": "quota_usage,config", "access_token": secrets.access_token},
    )
    data = permissions_response.get("data")
    if not isinstance(data, list):
        raise PostingError("MISSING_PERMISSION", "Instagram content publishing permission probe failed")
    return {"status": "PASS", "user_id": secrets.user_id,
            "permissions": sorted(required_permissions),
            "permission_check": "content_publishing_limit", "media_urls": media_urls}
