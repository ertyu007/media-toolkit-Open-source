"""Android port of the URL-download half of ``clipora/importer.py``.

Kept compatible with the PC module for URL validation, command building and
progress parsing (see ``android/tests/test_core.py``). Platform deltas:

* yt-dlp runs as ``python -m yt_dlp`` (pip install, no managed binary),
* no ``--js-runtimes`` flag: there is no Deno/Node on Android,
* no ``--impersonate``: ``curl_cffi`` has no Android wheel, so the PC retry
  ladder collapses to a single pass.
"""

from __future__ import annotations

import importlib.util
import ipaddress
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import urlsplit

WORKSPACE_PREFIX = '.clipora-import-'
MAX_DOWNLOAD_SIZE = '10G'
ALLOWED_OUTPUT_SUFFIXES = {
    '.aac', '.flac', '.m4a', '.mkv', '.mov', '.mp3',
    '.mp4', '.ogg', '.opus', '.wav', '.webm',
}
VIDEO_QUALITIES = ('สูงสุด', '2160p', '1080p', '720p', '480p', '360p')
AUDIO_FORMATS = ('mp3', 'm4a', 'wav', 'flac', 'opus')
_PROGRESS_PATTERN = re.compile(
    r'^clipora-progress:\s*([0-9]+(?:\.[0-9]+)?)%(?:\|([^|]*)\|([^|]*))?'
)
_OUTPUT_PREFIX = 'clipora-output:'
_BLOCK_SIGNATURES = (
    'http error 403',
    'http error 429',
    '403 forbidden',
    '429 too many requests',
    "confirm you're not a bot",
    'unusual traffic',
    'this request has been blocked',
    'temporary block',
    'captcha',
    'automated access',
    'robot',
)
_NETWORK_BLOCK_SIGNATURES = (
    'getaddrinfo failed',
    'failed to resolve',
    'unable to resolve',
    'temporary failure in name resolution',
    'name resolution failed',
    'network is unreachable',
    'no route to host',
    'errno 11001',
)
_EXTRACTOR_BROKEN_SIGNATURES = (
    'unexpected response from webpage request',
    'please report this issue',
    'confirm you are on the latest version',
    'unable to extract player response',
)
_SITE_WORKAROUND_HEADERS = (
    ('tiktok', ('--add-header', 'Referer:https://www.tiktok.com/')),
)
_SITE_EXTRACTOR_ARGS = (
    ('youtube.com', ('--extractor-args', 'youtube:player_client=android,web_embedded,tv')),
    ('youtu.be', ('--extractor-args', 'youtube:player_client=android,web_embedded,tv')),
)


class URLImportError(RuntimeError):
    pass


class URLImportBlocked(URLImportError):
    """Raised when the target site blocks automated downloads (403/429/bot check)."""

    def __init__(self, detail: str = '') -> None:
        super().__init__(
            'เว็บไซต์บล็อกการดาวน์โหลดอัตโนมัติ (HTTP 403/429 หรือกัน bot) — '
            'ลองอัปเดต yt-dlp หรือใช้ลิงก์อื่น'
            + (f'\n\n{detail}' if detail else '')
        )
        self.detail = detail


class URLNetworkBlocked(URLImportError):
    """Raised when the network/ISP blocks resolution or connection (DNS-level block)."""

    def __init__(self, detail: str = '') -> None:
        super().__init__(
            'เครือข่าย/ISP บล็อกการเข้าถึงเว็บไซต์นี้ (resolve โดเมนไม่ได้) — '
            'ลองเปลี่ยน DNS เป็น 1.1.1.1 หรือ 8.8.8.8 หรือใช้ VPN/proxy แล้วลองใหม่'
            + (f'\n\n{detail}' if detail else '')
        )
        self.detail = detail


class URLExtractorBroken(URLImportError):
    """Raised when yt-dlp cannot parse the site (site changed, extractor outdated)."""

    def __init__(self, detail: str = '') -> None:
        super().__init__(
            'เว็บไซต์เปลี่ยนระบบจนตัวดาวน์โหลดตามไม่ทัน — '
            'รอ yt-dlp เวอร์ชันใหม่แล้วลองอีกครั้ง'
            + (f'\n\n{detail}' if detail else '')
        )
        self.detail = detail


@dataclass(frozen=True)
class ImportSpec:
    url: str
    destination: Path
    mode: str
    quality: str
    audio_format: str
    video_format: str = 'mp4'
    fps: str = 'สูงสุด'


_NUMERIC_PART_RE = re.compile(r'^(?:0[xX][0-9a-fA-F]+|0[0-7]*|[0-9]+)$')


def _parse_numeric_part(part: str) -> int | None:
    if not _NUMERIC_PART_RE.match(part):
        return None
    try:
        if part.lower().startswith('0x'):
            return int(part, 16)
        if len(part) > 1 and part.startswith('0') and part.isdigit():
            try:
                return int(part, 8)
            except ValueError:
                # '08'/'09' are not valid octal; resolvers read them as
                # decimal, so decode as decimal to avoid a private-IP bypass.
                return int(part, 10)
        return int(part, 10)
    except ValueError:
        return None


def _decode_obscured_ipv4(hostname: str) -> ipaddress.IPv4Address | None:
    """Decode hex/decimal/octal/shorthand IPv4 forms (e.g. ``0x7f000001``).

    Returns None when the hostname is not a numeric IP encoding.
    """
    host = hostname.strip().lower().rstrip('.')
    if not host:
        return None
    if '.' not in host:
        value = _parse_numeric_part(host)
        if value is None or not 0 <= value < 2**32:
            return None
        return ipaddress.IPv4Address(value)
    parts = host.split('.')
    if not 2 <= len(parts) <= 4:
        return None
    values: list[int] = []
    for part in parts:
        value = _parse_numeric_part(part)
        if value is None:
            return None
        values.append(value)
    try:
        if len(values) == 4:
            if any(value > 255 for value in values):
                return None
            packed = (values[0] << 24) | (values[1] << 16) | (values[2] << 8) | values[3]
        elif len(values) == 3:
            if values[0] > 255 or values[1] > 255 or values[2] > 65535:
                return None
            packed = (values[0] << 24) | (values[1] << 16) | values[2]
        else:
            if values[0] > 255 or values[1] > 2**24 - 1:
                return None
            packed = (values[0] << 24) | values[1]
    except (ValueError, OverflowError):
        return None
    return ipaddress.IPv4Address(packed)


def validate_url(raw_url: str) -> str:
    url = raw_url.strip()
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise ValueError('ลิงก์ไม่ถูกต้อง กรุณาตรวจสอบแล้วลองใหม่') from exc
    if parsed.scheme.lower() not in {'http', 'https'}:
        raise ValueError('รองรับเฉพาะลิงก์ http หรือ https')
    if not parsed.hostname:
        raise ValueError('ลิงก์ไม่มีชื่อเว็บไซต์')
    if parsed.username or parsed.password:
        raise ValueError('ไม่รองรับลิงก์ที่ฝังชื่อผู้ใช้หรือรหัสผ่าน')
    if port is not None and not 1 <= port <= 65535:
        raise ValueError('พอร์ตในลิงก์ไม่ถูกต้อง')

    hostname = parsed.hostname.rstrip('.').lower()
    if hostname == 'localhost' or hostname.endswith('.localhost'):
        raise ValueError('ไม่รองรับลิงก์ภายในเครื่อง')
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError('ไม่รองรับลิงก์เครือข่ายภายในหรือ IP ส่วนตัว')
    if address is None:
        obscured = _decode_obscured_ipv4(hostname)
        if obscured is not None and not obscured.is_global:
            raise ValueError('ไม่รองรับลิงก์เครือข่ายภายในหรือ IP ส่วนตัว')
    return url


def url_summary(raw_url: str) -> str:
    if not raw_url.strip():
        return 'วางลิงก์สาธารณะที่ต้องการดาวน์โหลด'
    try:
        url = validate_url(raw_url)
    except ValueError as exc:
        return str(exc)
    hostname = urlsplit(url).hostname or ''
    return f'พร้อมตรวจสอบลิงก์จาก {hostname}'


def find_ytdlp_command() -> list[str] | None:
    """yt-dlp ships as a pip module inside the APK; there is no managed binary."""
    try:
        module = importlib.util.find_spec('yt_dlp')
    except (ImportError, ValueError):
        return None
    if module is None:
        return None
    return [sys.executable, '-m', 'yt_dlp']


def site_workaround_headers(raw_url: str) -> list[str]:
    """Extra ``--add-header`` arguments for sites that block header-less requests."""
    lower_url = raw_url.lower()
    args: list[str] = []
    for needle, header_args in _SITE_WORKAROUND_HEADERS:
        if needle in lower_url:
            args.extend(header_args)
    return args


def site_workaround_extractor_args(raw_url: str) -> list[str]:
    """Extra ``--extractor-args`` for sites with known client/player workarounds."""
    lower_url = raw_url.lower()
    args: list[str] = []
    for needle, extractor_args in _SITE_EXTRACTOR_ARGS:
        if needle in lower_url:
            args.extend(extractor_args)
    return args


def _has_signature(diagnostics: Sequence[str], signatures: tuple[str, ...]) -> bool:
    return any(
        signature in line.lower()
        for line in diagnostics
        for signature in signatures
    )


def is_block_error(diagnostics: Sequence[str]) -> bool:
    """True when captured yt-dlp output looks like a site-side block (403/429/bot)."""
    return _has_signature(diagnostics, _BLOCK_SIGNATURES)


def is_network_block_error(diagnostics: Sequence[str]) -> bool:
    """True when captured yt-dlp output looks like a network/ISP-level block."""
    return _has_signature(diagnostics, _NETWORK_BLOCK_SIGNATURES)


def is_extractor_broken_error(diagnostics: Sequence[str]) -> bool:
    """True when yt-dlp reports its extractor can no longer parse the site."""
    return _has_signature(diagnostics, _EXTRACTOR_BROKEN_SIGNATURES)


def build_import_command(
    tool_command: Sequence[str],
    spec: ImportSpec,
    workspace: Path,
) -> list[str]:
    if not tool_command:
        raise ValueError('ไม่พบคำสั่ง yt-dlp')
    url = validate_url(spec.url)
    if spec.mode not in {'audio', 'video'}:
        raise ValueError(f'ไม่รองรับโหมดดาวน์โหลด: {spec.mode}')

    output_template = str(workspace / '%(title).160B.%(ext)s')
    command = [
        *tool_command,
        '--ignore-config',
        '--no-playlist',
        '--no-cache-dir',
        '--no-colors',
        '--encoding',
        'utf-8',
        '--newline',
        '--progress',
        '--progress-delta',
        '0.2',
        '--progress-template',
        'download:clipora-progress:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s',
        '--print',
        'after_move:clipora-output:%(filepath)j',
        '--trim-filenames',
        '180',
        '--no-overwrites',
        '--max-filesize',
        MAX_DOWNLOAD_SIZE,
        '--socket-timeout',
        '30',
        '--retries',
        '3',
        '--fragment-retries',
        '3',
        '--concurrent-fragments',
        '4',
        '--match-filter',
        '!is_live',
        '--output',
        output_template,
    ]
    if spec.mode == 'audio':
        audio_format = spec.audio_format.lower()
        if audio_format not in AUDIO_FORMATS:
            raise ValueError(f'ไม่รองรับรูปแบบเสียง: {spec.audio_format}')
        command += [
            '--format',
            'bestaudio/best',
            '--extract-audio',
            '--audio-format',
            audio_format,
            '--audio-quality',
            '0',
        ]
    else:
        if spec.video_format not in {'mp4', 'mov'}:
            raise ValueError(f'ไม่รองรับรูปแบบไฟล์วิดีโอ: {spec.video_format}')
        try:
            sort_value = {
                'สูงสุด': 'res,fps,vcodec:h264,acodec:aac',
                '2160p': 'res:2160,fps,vcodec:h264,acodec:aac',
                '1080p': 'res:1080,fps,vcodec:h264,acodec:aac',
                '720p': 'res:720,fps,vcodec:h264,acodec:aac',
                '480p': 'res:480,fps,vcodec:h264,acodec:aac',
                '360p': 'res:360,fps,vcodec:h264,acodec:aac',
            }[spec.quality]
        except KeyError as exc:
            raise ValueError(f'ไม่รองรับระดับคุณภาพลิงก์: {spec.quality}') from exc
        fps_digits = ''.join(character for character in spec.fps if character.isdigit())
        if fps_digits:
            fps_filter = f'[fps<={fps_digits}]'
            download_format = (
                f'bv*[ext=mp4]{fps_filter}+ba[ext=m4a]'
                f'/b[ext=mp4]{fps_filter}/bv*+ba/b'
            )
        else:
            download_format = 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b'
        command += [
            '--format',
            download_format,
            '--format-sort',
            sort_value,
            '--merge-output-format',
            'mp4',
            '--remux-video',
            'mp4',
        ]
    command += site_workaround_headers(url)
    command += site_workaround_extractor_args(url)
    return [*command, '--', url]


def _clean_progress_field(value: str | None) -> str:
    """Drop yt-dlp 'NA'/empty placeholders from speed/ETA fields."""
    text = (value or '').strip()
    return '' if not text or text.upper() == 'NA' else text


def parse_import_progress_detail(raw_line: str) -> tuple[float, str, str] | None:
    """Parse percent + download speed + ETA; old percent-only lines still work."""
    match = _PROGRESS_PATTERN.match(raw_line.strip())
    if not match:
        return None
    try:
        percent = float(match.group(1))
    except ValueError:
        return None
    fraction = max(0.0, min(percent / 100, 1.0))
    return (
        fraction,
        _clean_progress_field(match.group(2)),
        _clean_progress_field(match.group(3)),
    )


def parse_import_progress(raw_line: str) -> float | None:
    detail = parse_import_progress_detail(raw_line)
    return detail[0] if detail is not None else None


def parse_reported_output(raw_line: str) -> Path | None:
    """Read the ``clipora-output:`` line yt-dlp prints after a successful move."""
    text = raw_line.strip()
    if not text.startswith(_OUTPUT_PREFIX):
        return None
    try:
        return Path(json.loads(text[len(_OUTPUT_PREFIX):]))
    except (ValueError, OSError):
        return None


def collision_free_path(target: Path) -> Path:
    if not target.exists():
        return target
    for index in range(1, 1000):
        candidate = target.with_name(f'{target.stem} ({index}){target.suffix}')
        if not candidate.exists():
            return candidate
    raise URLImportError('มีไฟล์ชื่อซ้ำกันมากเกินไป')


def _classify_failure(diagnostics: Sequence[str]) -> URLImportError:
    detail = '\n'.join(list(diagnostics)[-12:])
    if is_block_error(diagnostics):
        return URLImportBlocked(detail)
    if is_network_block_error(diagnostics):
        return URLNetworkBlocked(detail)
    if is_extractor_broken_error(diagnostics):
        return URLExtractorBroken(detail)
    return URLImportError(detail or 'ดาวน์โหลดไม่สำเร็จ')


def download(
    spec: ImportSpec,
    on_progress: Callable[[float, str, str], None],
    cancellation=None,
) -> Path:
    """Download one public URL into ``spec.destination`` and return the new file.

    Downloads land in a private workspace first, so a cancelled or failed run
    never leaves a partial file in the user's output folder.
    """
    tool_command = find_ytdlp_command()
    if tool_command is None:
        raise URLImportError('ไม่พบ yt-dlp ในแอป กรุณาติดตั้งแอปใหม่')
    destination = spec.destination
    destination.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix=WORKSPACE_PREFIX, dir=destination))
    diagnostics: list[str] = []
    reported: list[Path] = []
    process = subprocess.Popen(
        build_import_command(tool_command, spec, workspace),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    if cancellation is not None:
        cancellation.attach(process)
    try:
        assert process.stdout is not None
        for raw_line in process.stdout:
            output = parse_reported_output(raw_line)
            if output is not None:
                reported.append(output)
                continue
            detail = parse_import_progress_detail(raw_line)
            if detail is not None:
                on_progress(*detail)
            else:
                diagnostics.append(raw_line.strip())
    finally:
        process.stdout.close()
        return_code = process.wait()
        if cancellation is not None:
            cancellation.detach(process)

    try:
        if cancellation is not None and cancellation.cancelled:
            return _abandon(workspace, reported)
        if return_code != 0:
            raise _classify_failure(diagnostics)
        completed = _resolve_completed(workspace, reported)
        target = collision_free_path(destination / completed.name)
        shutil.move(str(completed), str(target))
        return target
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _abandon(workspace: Path, reported: Sequence[Path]) -> Path:
    shutil.rmtree(workspace, ignore_errors=True)
    raise URLImportError('ยกเลิกการดาวน์โหลดแล้ว')


def _resolve_completed(workspace: Path, reported: Sequence[Path]) -> Path:
    candidates = [
        candidate for candidate in reported
        if candidate.is_file()
        and candidate.suffix.lower() in ALLOWED_OUTPUT_SUFFIXES
        and candidate.stat().st_size > 0
    ]
    if not candidates:
        candidates = [
            item for item in sorted(workspace.iterdir())
            if item.is_file()
            and item.suffix.lower() in ALLOWED_OUTPUT_SUFFIXES
            and item.stat().st_size > 0
        ]
    if not candidates:
        raise URLImportError('ดาวน์โหลดสำเร็จแต่ไม่พบไฟล์ที่ใช้ได้')
    return candidates[-1]
