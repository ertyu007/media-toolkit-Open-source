from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .tools import managed_tools_dir

GITHUB_RELEASES_URL = 'https://api.github.com/repos/ertyu007/media-toolkit-Open-source/releases'
USER_AGENT = 'Clipora-AppUpdate/1.0'
MAX_JSON_BYTES = 2 * 1024 * 1024
_VERSION_DIGITS_RE = re.compile(r'(\d+)')


class AppUpdateError(RuntimeError):
    """Raised when checking for application updates fails."""
    pass


@dataclass(frozen=True)
class AppReleaseInfo:
    version: str
    tag_name: str
    title: str
    release_notes: str
    html_url: str
    download_url: str | None
    published_at: str | None = None


def parse_app_version(version_str: str | None) -> tuple[int, ...] | None:
    """Parse version string into tuple of integers.

    Supports formats like '0.6.1', 'pc-v0.6.1', 'v1.2.0.3'.
    Returns None if no version numbers can be found.
    """
    if not version_str:
        return None
    text = version_str.strip()
    if text.startswith('pc-v'):
        text = text[4:]
    elif text.startswith('v'):
        text = text[1:]

    matches = _VERSION_DIGITS_RE.findall(text)
    if not matches:
        return None
    return tuple(int(m) for m in matches)


def is_app_update_available(latest_version: str | None, current_version: str | None) -> bool:
    """Return True if latest_version is strictly newer than current_version."""
    latest = parse_app_version(latest_version)
    if latest is None:
        return False
    current = parse_app_version(current_version)
    if current is None:
        return True
    return latest > current


def parse_release_payload(payload: str | list[dict[str, Any]] | dict[str, Any]) -> AppReleaseInfo | None:
    """Parse GitHub release API JSON data and find the newest PC release."""
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise AppUpdateError('ไม่สามารถอ่านข้อมูลเวอร์ชันล่าสุดจาก GitHub ได้') from exc
    else:
        data = payload

    releases: list[dict[str, Any]]
    if isinstance(data, list):
        releases = data
    elif isinstance(data, dict):
        releases = [data]
    else:
        raise AppUpdateError('รูปแบบข้อมูลการตอบกลับจาก GitHub ไม่ถูกต้อง')

    # Look for the first release that matches PC tag (pc-v*) and is not a draft
    for release in releases:
        if not isinstance(release, dict):
            continue
        if release.get('draft', False):
            continue

        tag_name = release.get('tag_name')
        if not isinstance(tag_name, str) or not tag_name:
            continue

        # Check if tag corresponds to PC release (starts with pc-v or is standalone vX.Y.Z)
        if not (tag_name.startswith('pc-v') or tag_name.startswith('v') or re.match(r'^\d+\.\d+', tag_name)):
            continue

        # Disregard mobile-only tags
        if tag_name.startswith('mobile-'):
            continue

        # Extract clean version number
        version = tag_name
        if version.startswith('pc-v'):
            version = version[4:]
        elif version.startswith('v'):
            version = version[1:]

        title = str(release.get('name') or tag_name).strip()
        body = str(release.get('body') or '').strip()
        html_url = str(release.get('html_url') or 'https://github.com/ertyu007/media-toolkit-Open-source/releases')
        published_at = release.get('published_at')

        # Find direct installer asset (.exe)
        download_url: str | None = None
        assets = release.get('assets', [])
        if isinstance(assets, list):
            # Prefer Clipora-Setup-*.exe, then any .exe
            for asset in assets:
                if not isinstance(asset, dict):
                    continue
                asset_name = str(asset.get('name', ''))
                asset_url = asset.get('browser_download_url')
                if asset_name.startswith('Clipora-Setup-') and asset_name.endswith('.exe') and asset_url:
                    download_url = str(asset_url)
                    break

            if not download_url:
                for asset in assets:
                    if not isinstance(asset, dict):
                        continue
                    asset_name = str(asset.get('name', ''))
                    asset_url = asset.get('browser_download_url')
                    if asset_name.endswith('.exe') and asset_url:
                        download_url = str(asset_url)
                        break

        return AppReleaseInfo(
            version=version,
            tag_name=tag_name,
            title=title,
            release_notes=body,
            html_url=html_url,
            download_url=download_url or html_url,
            published_at=str(published_at) if published_at else None,
        )

    return None


def fetch_latest_app_release(
    releases_url: str = GITHUB_RELEASES_URL,
    timeout: int = 20,
) -> AppReleaseInfo | None:
    """Fetch releases from GitHub API and return release info for the latest PC release."""
    if urlsplit(releases_url).scheme != 'https':
        raise AppUpdateError(f'ปฏิเสธ URL ที่ไม่ใช่ HTTPS: {releases_url}')

    request = urllib.request.Request(
        releases_url,
        headers={
            'User-Agent': USER_AGENT,
            'Accept': 'application/vnd.github.v3+json',
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read(MAX_JSON_BYTES)
            text = data.decode('utf-8', errors='replace')
    except OSError as exc:
        raise AppUpdateError(f'เชื่อมต่อกับเซิร์ฟเวอร์ตรวจสอบอัปเดตไม่สำเร็จ: {exc}') from exc

    return parse_release_payload(text)


def _settings_file_path() -> Path:
    """Return path to Clipora settings JSON file."""
    base = managed_tools_dir().parent
    base.mkdir(parents=True, exist_ok=True)
    return base / 'settings.json'


def load_settings() -> dict[str, Any]:
    """Load settings dict from local disk."""
    path = _settings_file_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_settings(settings: dict[str, Any]) -> None:
    """Save settings dict to local disk."""
    path = _settings_file_path()
    try:
        tmp_path = path.with_suffix('.tmp')
        tmp_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding='utf-8')
        tmp_path.replace(path)
    except OSError as exc:
        raise AppUpdateError(f'บันทึกการตั้งค่าไม่สำเร็จ: {exc}') from exc


def get_skipped_version() -> str | None:
    """Return the version string that the user previously chose to skip."""
    settings = load_settings()
    skipped = settings.get('skipped_app_version')
    return str(skipped).strip() if skipped else None


def set_skipped_version(version: str) -> None:
    """Store the skipped version so auto-check won't prompt for this version again."""
    settings = load_settings()
    settings['skipped_app_version'] = version.strip()
    save_settings(settings)


def clear_skipped_version() -> None:
    """Clear skipped version."""
    settings = load_settings()
    if 'skipped_app_version' in settings:
        del settings['skipped_app_version']
        save_settings(settings)
