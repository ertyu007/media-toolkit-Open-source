from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from .tools import managed_tools_dir

GITHUB_RELEASES_URL = 'https://api.github.com/repos/ertyu007/media-toolkit-Open-source/releases'
USER_AGENT = 'Clipora-AppUpdate/1.0'
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_UPDATE_BYTES = 512 * 1024 * 1024
UPDATE_CHUNK_BYTES = 1024 * 1024
UPDATE_SPACE_MARGIN_BYTES = 64 * 1024 * 1024
_VERSION_DIGITS_RE = re.compile(r'(\d+)')
_SHA256_RE = re.compile(r'[0-9a-fA-F]{64}')


def application_update_directory() -> Path:
    local_app_data = os.environ.get('LOCALAPPDATA')
    root = Path(local_app_data) if local_app_data else Path.home() / 'AppData' / 'Local'
    return root / 'Clipora' / 'updates'


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
    download_size: int | None = None
    checksum_url: str | None = None


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
        if not re.fullmatch(r'\d+\.\d+\.\d+', version):
            continue

        title = str(release.get('name') or tag_name).strip()
        body = str(release.get('body') or '').strip()
        html_url = str(release.get('html_url') or 'https://github.com/ertyu007/media-toolkit-Open-source/releases')
        published_at = release.get('published_at')

        download_url: str | None = None
        checksum_url: str | None = None
        download_size: int | None = None
        assets = release.get('assets', [])
        if isinstance(assets, list):
            for asset in assets:
                if not isinstance(asset, dict):
                    continue
                asset_name = str(asset.get('name', ''))
                asset_url = asset.get('browser_download_url')
                if asset_name == f'Clipora-Setup-{version}-x64.exe' and asset_url:
                    download_url = str(asset_url)
                    try:
                        size = int(asset.get('size', 0))
                    except (TypeError, ValueError):
                        size = 0
                    download_size = size if size > 0 else None
                    break
            checksum_name = f'Clipora-Setup-{version}-x64.exe.sha256'
            for asset in assets:
                if isinstance(asset, dict) and asset.get('name') == checksum_name:
                    asset_url = asset.get('browser_download_url')
                    if asset_url:
                        checksum_url = str(asset_url)
                    break

        return AppReleaseInfo(
            version=version,
            tag_name=tag_name,
            title=title,
            release_notes=body,
            html_url=html_url,
            download_url=download_url or html_url,
            published_at=str(published_at) if published_at else None,
            download_size=download_size,
            checksum_url=checksum_url,
        )

    return None


def update_space_requirements(download_size: int) -> tuple[int, int]:
    """Return conservative bytes needed in app-data and installer temp storage."""
    if download_size <= 0 or download_size > MAX_UPDATE_BYTES:
        raise AppUpdateError('ขนาดไฟล์อัปเดตไม่ถูกต้องหรือใหญ่เกินกำหนด')
    download_required = download_size + UPDATE_SPACE_MARGIN_BYTES
    installer_temp_required = (download_size * 2) + UPDATE_SPACE_MARGIN_BYTES
    return download_required, installer_temp_required


def check_update_disk_space(download_size: int, update_dir: Path | None = None) -> tuple[int, int]:
    """Verify free space for the download cache and Inno Setup extraction."""
    download_required, temp_required = update_space_requirements(download_size)
    root = update_dir or application_update_directory()
    temp_root = Path(tempfile.gettempdir())
    for path, required, label in (
        (root, download_required, 'โฟลเดอร์ดาวน์โหลด'),
        (temp_root, temp_required, 'โฟลเดอร์ชั่วคราวสำหรับติดตั้ง'),
    ):
        try:
            probe = path
            while not probe.exists() and probe != probe.parent:
                probe = probe.parent
            free = shutil.disk_usage(probe).free
        except OSError as exc:
            raise AppUpdateError(f'ตรวจสอบพื้นที่ว่าง{label}ไม่สำเร็จ: {exc}') from exc
        if free < required:
            raise AppUpdateError(
                f'พื้นที่ว่าง{label}ไม่พอ (ต้องมีประมาณ {required // (1024 * 1024)} MB)'
            )
    return download_required, temp_required


def _trusted_release_asset_url(url: str, tag_name: str, filename: str) -> bool:
    parsed = urlsplit(url)
    expected_path = f'/ertyu007/media-toolkit-Open-source/releases/download/{tag_name}/{filename}'
    return (
        parsed.scheme == 'https'
        and parsed.hostname == 'github.com'
        and parsed.netloc == 'github.com'
        and parsed.path == expected_path
        and not parsed.query
        and not parsed.fragment
    )


def _download_response(url: str) -> Any:
    if urlsplit(url).scheme != 'https':
        raise AppUpdateError('ปฏิเสธ URL ดาวน์โหลดที่ไม่ใช่ HTTPS')
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        return urllib.request.urlopen(request, timeout=45)
    except OSError as exc:
        raise AppUpdateError(f'ดาวน์โหลดอัปเดตไม่สำเร็จ: {exc}') from exc


def _read_update_checksum(url: str, tag_name: str, filename: str) -> str:
    if not _trusted_release_asset_url(url, tag_name, f'{filename}.sha256'):
        raise AppUpdateError('URL checksum ไม่ตรงกับ asset ของ GitHub Release ที่คาดไว้')
    try:
        with _download_response(url) as response:
            payload = response.read(16 * 1024).decode('utf-8', errors='replace')
    except (OSError, UnicodeError) as exc:
        raise AppUpdateError(f'อ่าน checksum ของอัปเดตไม่สำเร็จ: {exc}') from exc
    for line in payload.splitlines():
        fields = line.strip().split()
        if len(fields) >= 2 and fields[-1].lstrip('*') == filename and _SHA256_RE.fullmatch(fields[0]):
            return fields[0].lower()
    raise AppUpdateError('ไม่พบ SHA-256 ที่ตรงกับตัวติดตั้งในไฟล์ checksum')


def download_app_update(
    release: AppReleaseInfo,
    on_progress: Callable[[int, int, float], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
    update_dir: Path | None = None,
) -> Path:
    """Download and verify the version-matched Windows installer atomically."""
    callback = on_progress or (lambda _downloaded, _total, _elapsed: None)
    cancelled = cancel_check or (lambda: False)
    if (
        not re.fullmatch(r'\d+\.\d+\.\d+', release.version)
        or release.tag_name not in {f'pc-v{release.version}', f'v{release.version}', release.version}
    ):
        raise AppUpdateError('ข้อมูลเวอร์ชันของอัปเดตไม่ถูกต้อง')
    filename = f'Clipora-Setup-{release.version}-x64.exe'
    if (
        not release.download_url
        or not release.checksum_url
        or not release.download_size
        or not _trusted_release_asset_url(release.download_url, release.tag_name, filename)
    ):
        raise AppUpdateError('Release นี้ไม่มี installer และ checksum ที่จำเป็นสำหรับอัปเดตในแอป')
    if release.download_size > MAX_UPDATE_BYTES:
        raise AppUpdateError('ไฟล์อัปเดตใหญ่เกินขีดจำกัดที่กำหนด')
    check_update_disk_space(release.download_size, update_dir)
    if cancelled():
        raise AppUpdateError('ยกเลิกการอัปเดตแล้ว')
    expected_digest = _read_update_checksum(release.checksum_url, release.tag_name, filename)
    root = update_dir or application_update_directory()
    root.mkdir(parents=True, exist_ok=True)
    target = root / filename
    fd, temporary_name = tempfile.mkstemp(prefix='.clipora-update-', suffix='.download', dir=root)
    temporary = Path(temporary_name)
    started = time.monotonic()
    downloaded = 0
    try:
        try:
            with os.fdopen(fd, 'wb') as output, _download_response(release.download_url) as response:
                declared = response.headers.get('Content-Length')
                if declared:
                    try:
                        response_size = int(declared)
                    except ValueError:
                        response_size = release.download_size
                    if response_size > MAX_UPDATE_BYTES or response_size != release.download_size:
                        raise AppUpdateError('ขนาดไฟล์ดาวน์โหลดไม่ตรงกับข้อมูล release')
                digest = hashlib.sha256()
                while True:
                    if cancelled():
                        raise AppUpdateError('ยกเลิกการอัปเดตแล้ว')
                    chunk = response.read(UPDATE_CHUNK_BYTES)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > release.download_size or downloaded > MAX_UPDATE_BYTES:
                        raise AppUpdateError('ไฟล์ดาวน์โหลดใหญ่กว่าขนาดที่ release ระบุ')
                    output.write(chunk)
                    digest.update(chunk)
                    callback(downloaded, release.download_size, time.monotonic() - started)
                output.flush()
                os.fsync(output.fileno())
        except OSError as exc:
            raise AppUpdateError(f'ดาวน์โหลดตัวติดตั้งไม่สำเร็จ: {exc}') from exc
        if downloaded != release.download_size:
            raise AppUpdateError('ไฟล์ดาวน์โหลดมีขนาดไม่ครบตามที่ release ระบุ')
        if digest.hexdigest().lower() != expected_digest:
            raise AppUpdateError('SHA-256 ของตัวติดตั้งไม่ตรงกัน ไฟล์ถูกปฏิเสธ')
        os.replace(temporary, target)
        return target
    finally:
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass


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
