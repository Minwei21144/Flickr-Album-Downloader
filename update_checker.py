from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from app_metadata import (
    APP_CURRENT_RELEASE_URL,
    APP_LATEST_RELEASE_API_URL,
    APP_RELEASES_URL,
    APP_USER_AGENT,
    APP_VERSION,
)


GITHUB_API_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": APP_USER_AGENT,
}


def ssl_context() -> ssl.SSLContext | None:
    try:
        import certifi
    except ImportError:
        return None
    return ssl.create_default_context(cafile=certifi.where())


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    latest_version: str | None
    latest_tag: str | None
    release_url: str
    is_update_available: bool
    error: str | None = None


def normalize_release_version(version: str | None) -> str:
    return (version or "").strip().removeprefix("v").removeprefix("V")


def version_sort_key(version: str | None) -> tuple[int, ...]:
    clean = normalize_release_version(version)
    match = re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?", clean)
    if not match:
        return ()
    parts = [int(part) for part in match.groups(default="0")]
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts or [0])


def is_newer_version(latest_version: str | None, current_version: str | None = APP_VERSION) -> bool:
    latest_key = version_sort_key(latest_version)
    current_key = version_sort_key(current_version)
    if not latest_key or not current_key:
        return False
    max_len = max(len(latest_key), len(current_key))
    latest_key = latest_key + (0,) * (max_len - len(latest_key))
    current_key = current_key + (0,) * (max_len - len(current_key))
    return latest_key > current_key


def result_from_release_payload(payload: dict[str, Any], current_version: str = APP_VERSION) -> UpdateCheckResult:
    latest_tag = str(payload.get("tag_name") or "").strip()
    latest_version = normalize_release_version(latest_tag)
    release_url = str(payload.get("html_url") or APP_RELEASES_URL)
    return UpdateCheckResult(
        current_version=current_version,
        latest_version=latest_version or None,
        latest_tag=latest_tag or None,
        release_url=release_url,
        is_update_available=is_newer_version(latest_version, current_version),
    )


def update_error_result(error: str, current_version: str = APP_VERSION) -> UpdateCheckResult:
    return UpdateCheckResult(
        current_version=current_version,
        latest_version=None,
        latest_tag=None,
        release_url=APP_CURRENT_RELEASE_URL,
        is_update_available=False,
        error=error,
    )


def check_for_update(current_version: str = APP_VERSION, timeout: float = 10.0) -> UpdateCheckResult:
    request = urllib.request.Request(APP_LATEST_RELEASE_API_URL, headers=GITHUB_API_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl_context()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return update_error_result(f"GitHub HTTP {exc.code}", current_version)
    except urllib.error.URLError as exc:
        return update_error_result(str(exc.reason), current_version)
    except (OSError, json.JSONDecodeError) as exc:
        return update_error_result(str(exc), current_version)
    if not isinstance(payload, dict):
        return update_error_result("Unexpected GitHub response.", current_version)
    return result_from_release_payload(payload, current_version)
