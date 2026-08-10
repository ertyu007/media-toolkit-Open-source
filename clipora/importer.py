from __future__ import annotations

import importlib.util
import ipaddress
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence
from urllib.parse import urlsplit

from .ffmpeg import CancellationToken, ConversionCancelled
from .tools import find_executable


WORKSPACE_PREFIX = '.clipora-import-'
MAX_DOWNLOAD_SIZE = '10G'
ALLOWED_OUTPUT_SUFFIXES = {
    '.aac',
    '.flac',
    '.m4a',
    '.mkv',
    '.mov',
    '.mp3',
    '.mp4',
    '.ogg',
    '.opus',
    '.wav',
    '.webm',
}
VIDEO_QUALITIES = ('สูงสุด', '1080p', '720p', '480p')
_PROGRESS_PATTERN = re.compile(r'^clipora-progress:\s*([0-9]+(?:\.[0-9]+)?)%')
_OUTPUT_PREFIX = 'clipora-output:'


class URLImportError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImportSpec:
    url: str
    destination: Path
    mode: str
    quality: str
    audio_format: str


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
    executable = find_executable('yt-dlp')
    if executable:
        return [str(executable)]
    try:
        module = importlib.util.find_spec('yt_dlp')
    except (ImportError, ValueError):
        module = None
    if module is not None:
        return [sys.executable, '-m', 'yt_dlp']
    return None


def managed_ytdlp_path() -> Path | None:
    return find_executable('yt-dlp')


def ytdlp_available() -> bool:
    return find_ytdlp_command() is not None


def find_javascript_runtime() -> str | None:
    for name in ('deno', 'node'):
        executable = find_executable(name)
        if executable is not None:
            return f'{name}:{executable}'
    return None


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

    output_template = str(workspace / '%(title).160B [%(id)s].%(ext)s')
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
        'download:clipora-progress:%(progress._percent_str)s',
        '--print',
        'after_move:clipora-output:%(filepath)j',
        '--windows-filenames',
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
    javascript_runtime = find_javascript_runtime()
    if javascript_runtime:
        command += ['--js-runtimes', javascript_runtime]
    ffmpeg = find_executable('ffmpeg')
    if ffmpeg is not None:
        command += ['--ffmpeg-location', str(ffmpeg.parent)]
    if spec.mode == 'audio':
        audio_format = spec.audio_format.lower()
        if audio_format not in {'mp3', 'm4a'}:
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
        try:
            sort_value = {
                'สูงสุด': 'res,fps,vcodec:h264,acodec:aac',
                '1080p': 'res:1080,fps,vcodec:h264,acodec:aac',
                '720p': 'res:720,fps,vcodec:h264,acodec:aac',
                '480p': 'res:480,fps,vcodec:h264,acodec:aac',
            }[spec.quality]
        except KeyError as exc:
            raise ValueError(f'ไม่รองรับระดับคุณภาพลิงก์: {spec.quality}') from exc
        command += [
            '--format',
            'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b',
            '--format-sort',
            sort_value,
            '--merge-output-format',
            'mp4',
            '--remux-video',
            'mp4',
        ]
    return [*command, '--', url]


def parse_import_progress(raw_line: str) -> float | None:
    match = _PROGRESS_PATTERN.match(raw_line.strip())
    if not match:
        return None
    try:
        percent = float(match.group(1))
    except ValueError:
        return None
    return max(0.0, min(percent / 100, 1.0))


def parse_reported_output(raw_line: str) -> Path | None:
    line = raw_line.strip()
    if not line.startswith(_OUTPUT_PREFIX):
        return None
    payload = line[len(_OUTPUT_PREFIX):]
    try:
        value = json.loads(payload)
    except json.JSONDecodeError:
        return None
    return Path(value) if isinstance(value, str) and value else None


def collision_free_path(target: Path) -> Path:
    if not target.exists():
        return target
    for index in range(1, 10_000):
        candidate = target.with_name(f'{target.stem} ({index}){target.suffix}')
        if not candidate.exists():
            return candidate
    raise URLImportError('มีไฟล์ชื่อซ้ำจำนวนมาก กรุณาเลือกโฟลเดอร์อื่น')


def create_import_workspace(destination: Path) -> Path:
    if not destination.is_dir():
        raise ValueError('ไม่พบโฟลเดอร์ปลายทาง')
    return Path(tempfile.mkdtemp(prefix=WORKSPACE_PREFIX, dir=destination))


def _is_owned_workspace(workspace: Path, destination: Path) -> bool:
    try:
        resolved_destination = destination.resolve()
        resolved_workspace = workspace.resolve()
        return (
            workspace != destination
            and workspace.parent.resolve() == resolved_destination
            and resolved_workspace.parent == resolved_destination
            and workspace.name.startswith(WORKSPACE_PREFIX)
            and len(workspace.name) > len(WORKSPACE_PREFIX)
        )
    except OSError:
        return False


def cleanup_import_workspace(workspace: Path, destination: Path) -> None:
    if not _is_owned_workspace(workspace, destination):
        raise ValueError('ปฏิเสธการลบโฟลเดอร์ชั่วคราวที่ไม่ได้เป็นของงานนี้')
    if workspace.is_symlink():
        workspace.unlink()
    elif workspace.is_dir():
        shutil.rmtree(workspace)


def finalize_import_output(completed: Path, destination: Path) -> Path:
    if not completed.is_file() or completed.stat().st_size == 0:
        raise URLImportError('ไฟล์ดาวน์โหลดไม่สมบูรณ์')
    for index in range(10_000):
        if index == 0:
            target = destination / completed.name
        else:
            target = destination / f'{completed.stem} ({index}){completed.suffix}'
        try:
            os.link(completed, target)
        except FileExistsError:
            continue
        except OSError:
            try:
                descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
            except FileExistsError:
                continue
            except OSError as exc:
                raise URLImportError(f'ไม่สามารถสร้างไฟล์ผลลัพธ์: {exc}') from exc
            try:
                with os.fdopen(descriptor, 'wb') as target_file, completed.open('rb') as source_file:
                    shutil.copyfileobj(source_file, target_file, length=1024 * 1024)
            except (OSError, ValueError):
                try:
                    target.unlink()
                except OSError:
                    pass
                raise
        try:
            completed.unlink()
        except OSError as exc:
            try:
                target.unlink()
            except OSError:
                pass
            raise URLImportError(f'ไม่สามารถย้ายไฟล์ผลลัพธ์: {exc}') from exc
        return target
    raise URLImportError('มีไฟล์ชื่อซ้ำจำนวนมาก กรุณาเลือกโฟลเดอร์อื่น')


def _resolve_completed_candidate(workspace: Path, root: Path, candidate: Path) -> Path | None:
    path = candidate if candidate.is_absolute() else workspace / candidate
    try:
        resolved = path.resolve()
        resolved.relative_to(root)
        if (
            resolved.is_file()
            and resolved.stat().st_size > 0
            and resolved.suffix.lower() in ALLOWED_OUTPUT_SUFFIXES
        ):
            return resolved
    except (OSError, ValueError):
        return None
    return None


def _find_completed_output(workspace: Path, reported: Sequence[Path]) -> Path:
    root = workspace.resolve()
    for candidate in reversed(reported):
        resolved = _resolve_completed_candidate(workspace, root, candidate)
        if resolved is not None:
            return resolved
    fallback = sorted(
        (path for path in workspace.iterdir() if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in fallback:
        resolved = _resolve_completed_candidate(workspace, root, candidate)
        if resolved is not None:
            return resolved
    raise URLImportError('ดาวน์โหลดเสร็จแต่ไม่พบไฟล์สื่อผลลัพธ์ที่สมบูรณ์')


def _run_import_process(
    command: Sequence[str],
    workspace: Path,
    on_progress: Callable[[float], None],
    cancellation: CancellationToken,
) -> Path:
    if cancellation.cancelled:
        raise ConversionCancelled('ยกเลิกงานแล้ว')
    diagnostics: deque[str] = deque(maxlen=60)
    reported_outputs: list[Path] = []
    process = subprocess.Popen(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
    )
    cancellation.attach(process, terminate_tree=True)
    assert process.stdout is not None
    try:
        for raw_line in process.stdout:
            progress = parse_import_progress(raw_line)
            if progress is not None:
                on_progress(progress)
                continue
            output = parse_reported_output(raw_line)
            if output is not None:
                reported_outputs.append(output)
                continue
            line = raw_line.strip()
            if line:
                diagnostics.append(line)
    finally:
        process.stdout.close()
        return_code = process.wait()
        cancellation.detach(process)
    if cancellation.cancelled:
        raise ConversionCancelled('ยกเลิกงานแล้ว')
    if return_code != 0:
        detail = '\n'.join(diagnostics)
        raise URLImportError(
            'ดาวน์โหลดลิงก์ไม่สำเร็จ ลิงก์อาจไม่เป็นสาธารณะหรือเว็บไซต์อาจเปลี่ยนแปลง'
            + (f'\n\n{detail}' if detail else f' (รหัส {return_code})')
        )
    return _find_completed_output(workspace, reported_outputs)


def import_url(
    spec: ImportSpec,
    on_progress: Callable[[float], None],
    cancellation: CancellationToken | None = None,
    tool_command: Sequence[str] | None = None,
) -> Path:
    validate_url(spec.url)
    command_prefix = list(tool_command) if tool_command is not None else find_ytdlp_command()
    if not command_prefix:
        raise URLImportError('ไม่พบ yt-dlp กรุณาติดตั้งแล้วเปิด Clipora ใหม่')
    token = cancellation or CancellationToken()
    workspace = create_import_workspace(spec.destination)
    try:
        command = build_import_command(command_prefix, spec, workspace)
        completed = _run_import_process(command, workspace, on_progress, token)
        return finalize_import_output(completed, spec.destination)
    finally:
        cleanup_import_workspace(workspace, spec.destination)
