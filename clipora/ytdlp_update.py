from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

from .dependencies import DependencySpec, _write_install_record, verify_sha256
from .tools import find_executable, managed_tools_dir


LATEST_RELEASE_URL = 'https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest'
DOWNLOAD_URL = 'https://github.com/yt-dlp/yt-dlp/releases/download/{tag}/yt-dlp.exe'
CHECKSUMS_URL = 'https://github.com/yt-dlp/yt-dlp/releases/download/{tag}/SHA2-256SUMS'
SOURCE_URL = 'https://github.com/yt-dlp/yt-dlp'
LICENSE_URL = 'https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE'
USER_AGENT = 'Clipora/0.5.2 yt-dlp-update'
CHUNK_SIZE = 1024 * 1024
MAX_TEXT_BYTES = 4 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024
_VERSION_RE = re.compile(r'(\d{4})\.(\d{2})\.(\d{2})')
_SHA256_RE = re.compile(r'[0-9a-fA-F]{64}')


class YtDlpUpdateError(RuntimeError):
    pass


def parse_ytdlp_version(text: str) -> tuple[int, int, int] | None:
    match = _VERSION_RE.search(text or '')
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def is_newer_available(latest: str, installed: str | None) -> bool:
    latest_version = parse_ytdlp_version(latest)
    if latest_version is None:
        return False
    installed_version = parse_ytdlp_version(installed)
    if installed_version is None:
        return True
    return latest_version > installed_version


def _recorded_ytdlp_version() -> str | None:
    record = managed_tools_dir() / 'installed.json'
    try:
        data = json.loads(record.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None
    entry = data.get('dependencies', {}).get('yt-dlp')
    version = entry.get('version') if isinstance(entry, dict) else None
    return version if isinstance(version, str) and version else None


def installed_ytdlp_version() -> str | None:
    executable = find_executable('yt-dlp')
    if executable is None:
        return None
    flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
    try:
        result = subprocess.run(
            [str(executable), '--version'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=False,
            timeout=30,
            creationflags=flags,
        )
    except (OSError, subprocess.TimeoutExpired):
        return _recorded_ytdlp_version()
    if result.returncode != 0:
        return _recorded_ytdlp_version()
    return (result.stdout or '').strip() or _recorded_ytdlp_version()


def _https_response(url: str) -> object:
    if urlsplit(url).scheme != 'https':
        raise YtDlpUpdateError(f'ปฏิเสธ URL ที่ไม่ใช่ HTTPS: {url}')
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        return urllib.request.urlopen(request, timeout=45)
    except OSError as exc:
        raise YtDlpUpdateError(f'เชื่อมต่อเพื่อตรวจสอบอัปเดต yt-dlp ไม่สำเร็จ: {exc}') from exc


def _fetch_https_text(url: str, cancel_check: Callable[[], bool] | None = None) -> str:
    cancel = cancel_check or (lambda: False)
    if cancel():
        raise YtDlpUpdateError('ยกเลิกการอัปเดต yt-dlp แล้ว')
    response = _https_response(url)
    chunks: list[bytes] = []
    total = 0
    try:
        with response:
            while True:
                if cancel():
                    raise YtDlpUpdateError('ยกเลิกการอัปเดต yt-dlp แล้ว')
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_TEXT_BYTES:
                    raise YtDlpUpdateError('คำตอบจากเซิร์ฟเวอร์ใหญ่เกินขีดจำกัดที่กำหนด')
                chunks.append(chunk)
    except OSError as exc:
        raise YtDlpUpdateError(f'ดาวน์โหลดข้อมูลไม่สำเร็จ: {exc}') from exc
    return b''.join(chunks).decode('utf-8', errors='replace')


def latest_ytdlp_version(cancel_check: Callable[[], bool] | None = None) -> str:
    payload = _fetch_https_text(LATEST_RELEASE_URL, cancel_check)
    try:
        release = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise YtDlpUpdateError('ไม่สามารถอ่านเวอร์ชันล่าสุดของ yt-dlp ได้') from exc
    tag = release.get('tag_name')
    if not isinstance(tag, str) or not tag:
        raise YtDlpUpdateError('ไม่พบเวอร์ชันล่าสุดของ yt-dlp')
    return tag


def _parse_checksum_digest(text: str, filename: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        tokens = stripped.split()
        if len(tokens) >= 2 and tokens[-1].endswith(filename) and _SHA256_RE.fullmatch(tokens[0]):
            return tokens[0].lower()
    raise YtDlpUpdateError(f'ไม่พบ checksum ของ {filename} ในรายการยืนยัน')


def _download_https_file(
    url: str,
    destination: Path,
    on_fraction: Callable[[float], None],
    cancel_check: Callable[[], bool] | None = None,
    size_limit: int = MAX_DOWNLOAD_BYTES,
) -> int:
    cancel = cancel_check or (lambda: False)
    if cancel():
        raise YtDlpUpdateError('ยกเลิกการอัปเดต yt-dlp แล้ว')
    response = _https_response(url)
    downloaded = 0
    try:
        with response:
            declared = response.headers.get('Content-Length')
            try:
                total_declared = int(declared) if declared else None
            except ValueError:
                total_declared = None
            if total_declared and total_declared > size_limit:
                raise YtDlpUpdateError('ไฟล์ดาวน์โหลดใหญ่เกินขีดจำกัดที่กำหนด')
            with destination.open('wb') as target:
                while True:
                    if cancel():
                        raise YtDlpUpdateError('ยกเลิกการอัปเดต yt-dlp แล้ว')
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > size_limit:
                        raise YtDlpUpdateError('ไฟล์ดาวน์โหลดใหญ่เกินขีดจำกัดที่กำหนด')
                    target.write(chunk)
                    if total_declared:
                        on_fraction(min(downloaded / total_declared, 1.0))
                    else:
                        on_fraction(0.0)
                target.flush()
                os.fsync(target.fileno())
    except OSError as exc:
        raise YtDlpUpdateError(f'ดาวน์โหลด yt-dlp ไม่สำเร็จ: {exc}') from exc
    return downloaded


def update_ytdlp(
    on_progress: Callable[[float, str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> str:
    callback = on_progress or (lambda _fraction, _message: None)
    cancel = cancel_check or (lambda: False)
    latest = latest_ytdlp_version(cancel)
    root = managed_tools_dir()
    root.mkdir(parents=True, exist_ok=True)
    checksums = _fetch_https_text(CHECKSUMS_URL.format(tag=latest), cancel)
    expected = _parse_checksum_digest(checksums, 'yt-dlp.exe')
    download_url = DOWNLOAD_URL.format(tag=latest)
    temporary = root / '.yt-dlp.exe.tmp'
    try:
        _download_https_file(
            download_url,
            temporary,
            lambda fraction: callback(0.1 + fraction * 0.8, 'กำลังดาวน์โหลด yt-dlp…'),
            cancel,
        )
        callback(0.92, 'กำลังตรวจสอบความถูกต้องของไฟล์…')
        verify_sha256(temporary, expected)
        os.replace(temporary, root / 'yt-dlp.exe')
        _write_install_record(
            root,
            (
                DependencySpec(
                    key='yt-dlp',
                    display_name='yt-dlp',
                    version=latest,
                    url=download_url,
                    sha256=expected,
                    expected_bytes=0,
                    archive_type='raw',
                    members=(('yt-dlp.exe', 'yt-dlp.exe'),),
                    source_url=SOURCE_URL,
                    license_url=LICENSE_URL,
                ),
            ),
        )
    finally:
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError:
                pass
    callback(1.0, 'อัปเดต yt-dlp เรียบร้อย')
    return latest
