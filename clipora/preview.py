"""Link preview: title/uploader/duration/thumbnail without downloading.

Metadata comes from ``yt-dlp --skip-download --print``; the thumbnail is
downloaded (size-capped) and converted to PNG via the managed FFmpeg so the
stdlib-only Tk frontend can display it. Failures yield ``None`` — callers
treat a missing preview as "no card", never as an error.
"""

from __future__ import annotations

import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .ffmpeg import CancellationToken, ConversionCancelled
from .importer import find_ytdlp_command, validate_url
from .tools import find_executable

PREVIEW_FIELDS = ('title', 'duration_string', 'thumbnail', 'uploader')
MAX_THUMBNAIL_BYTES = 5 * 1024 * 1024
THUMBNAIL_WIDTH = 320


@dataclass(frozen=True)
class LinkPreview:
    title: str
    uploader: str
    duration: str
    thumbnail_url: str


def build_preview_command(tool_command: Sequence[str], url: str) -> list[str]:
    """yt-dlp metadata-only command; single item, no cache, no credentials."""
    if not tool_command:
        raise ValueError('ไม่พบคำสั่ง yt-dlp')
    clean = validate_url(url)
    command = [
        *tool_command,
        '--ignore-config',
        '--no-playlist',
        '--skip-download',
        '--no-cache-dir',
        '--no-colors',
        '--socket-timeout',
        '15',
    ]
    for field in PREVIEW_FIELDS:
        command += ['--print', field]
    return [*command, '--', clean]


def _clean_field(value: str) -> str:
    text = value.strip()
    return '' if text.lower() == 'na' else text


def parse_preview_output(text: str) -> LinkPreview:
    """Parse the four ``--print`` lines in field order; short output → ''."""
    lines = [_clean_field(line) for line in text.splitlines()]
    while len(lines) < len(PREVIEW_FIELDS):
        lines.append('')
    title, duration, thumbnail_url, uploader = lines[: len(PREVIEW_FIELDS)]
    return LinkPreview(
        title=title, uploader=uploader, duration=duration, thumbnail_url=thumbnail_url
    )


def fetch_link_preview(
    url: str,
    on_progress: Callable[[str], None] | None = None,
    cancellation: CancellationToken | None = None,
    tool_command: Sequence[str] | None = None,
) -> LinkPreview:
    """Run yt-dlp and return metadata; raises on failure/cancel."""
    command_prefix = list(tool_command) if tool_command is not None else find_ytdlp_command()
    command = build_preview_command(command_prefix, url)
    token = cancellation or CancellationToken()
    if token.cancelled:
        raise ConversionCancelled('ยกเลิกงานแล้ว')
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding='utf-8',
        errors='replace',
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
    )
    token.attach(process, terminate_tree=False)
    assert process.stdout is not None
    try:
        captured = process.stdout.read()
    finally:
        process.stdout.close()
        return_code = process.wait()
        token.detach(process)
    if token.cancelled:
        raise ConversionCancelled('ยกเลิกงานแล้ว')
    if return_code != 0:
        raise RuntimeError(f'อ่านข้อมูลลิงก์ไม่สำเร็จ (รหัส {return_code})')
    if on_progress is not None:
        on_progress('อ่านข้อมูลลิงก์แล้ว')
    return parse_preview_output(captured or '')


def download_thumbnail(thumbnail_url: str, png_path: Path, timeout: int = 15) -> Path | None:
    """Download + convert a thumbnail to PNG; None when anything fails."""
    if not thumbnail_url.startswith(('http://', 'https://')):
        return None
    try:
        request = urllib.request.Request(
            thumbnail_url, headers={'User-Agent': 'Clipora-LinkPreview/1.0'}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_THUMBNAIL_BYTES + 1)
    except (OSError, ValueError):
        return None
    if not raw or len(raw) > MAX_THUMBNAIL_BYTES:
        return None
    ffmpeg = find_executable('ffmpeg')
    if ffmpeg is None:
        return None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=Path(thumbnail_url.split('?')[0]).suffix or '.img', delete=False
        ) as source_file:
            source_file.write(raw)
        source_temp = Path(source_file.name)
    except OSError:
        return None
    try:
        result = subprocess.run(
            [
                str(ffmpeg),
                '-y',
                '-loglevel',
                'error',
                '-i',
                str(source_temp),
                '-vf',
                f'scale={THUMBNAIL_WIDTH}:-1',
                '-frames:v',
                '1',
                str(png_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
            creationflags=(
                subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            ),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        try:
            source_temp.unlink()
        except OSError:
            pass
    if result.returncode != 0 or not png_path.is_file():
        return None
    return png_path
