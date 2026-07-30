from __future__ import annotations

import json
import math
import shutil
import subprocess
import threading
import uuid
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


class FFmpegError(RuntimeError):
    pass


class UnsupportedMediaError(FFmpegError):
    pass


class ConversionCancelled(FFmpegError):
    pass


@dataclass(frozen=True)
class MediaInfo:
    duration: float | None
    has_video: bool
    has_audio: bool
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True)
class JobSpec:
    source: Path
    destination: Path
    mode: str
    quality: str
    audio_format: str


class CancellationToken:
    def __init__(self) -> None:
        self._cancelled = threading.Event()
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def cancel(self) -> None:
        self._cancelled.set()
        with self._lock:
            process = self._process
        if process is not None and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    def attach(self, process: subprocess.Popen[str]) -> None:
        with self._lock:
            self._process = process
            cancelled = self._cancelled.is_set()
        if cancelled and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    def detach(self, process: subprocess.Popen[str]) -> None:
        with self._lock:
            if self._process is process:
                self._process = None


PROGRESS_KEYS = {
    'bitrate',
    'drop_frames',
    'dup_frames',
    'fps',
    'frame',
    'out_time',
    'out_time_ms',
    'out_time_us',
    'progress',
    'speed',
    'stream_0_0_q',
    'total_size',
}


def tools_available() -> bool:
    return shutil.which('ffmpeg') is not None and shutil.which('ffprobe') is not None


def _duration(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed > 0 else None


def probe(path: Path) -> MediaInfo:
    command = [
        'ffprobe',
        '-v',
        'error',
        '-show_entries',
        'format=duration:stream=codec_type,width,height',
        '-of',
        'json',
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise FFmpegError(result.stderr.strip() or 'อ่านข้อมูลไฟล์ไม่สำเร็จ')

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise FFmpegError('ข้อมูลที่ได้รับจาก ffprobe ไม่ถูกต้อง') from exc

    streams = data.get('streams', [])
    video_stream = next((stream for stream in streams if stream.get('codec_type') == 'video'), None)
    has_audio = any(stream.get('codec_type') == 'audio' for stream in streams)
    return MediaInfo(
        duration=_duration(data.get('format', {}).get('duration')),
        has_video=video_stream is not None,
        has_audio=has_audio,
        width=video_stream.get('width') if video_stream else None,
        height=video_stream.get('height') if video_stream else None,
    )


def validate_operation(info: MediaInfo, mode: str) -> None:
    if mode == 'audio' and not info.has_audio:
        raise UnsupportedMediaError('ไฟล์นี้ไม่มีเสียงให้แยก')
    if mode == 'video' and not info.has_video:
        raise UnsupportedMediaError('ไฟล์นี้ไม่มีภาพวิดีโอสำหรับแปลง')


def temporary_output_path(target: Path) -> Path:
    unique = uuid.uuid4().hex
    return target.with_name(f'.{target.stem}.clipora-{unique}{target.suffix}')


def _is_temporary_output_for(temporary: Path, target: Path) -> bool:
    try:
        same_parent = temporary.parent.resolve() == target.parent.resolve()
    except OSError:
        return False
    prefix = f'.{target.stem}.clipora-'
    return (
        temporary != target
        and same_parent
        and temporary.suffix.lower() == target.suffix.lower()
        and temporary.name.startswith(prefix)
    )


def cleanup_temporary_output(temporary: Path, target: Path) -> None:
    if not _is_temporary_output_for(temporary, target):
        raise ValueError('ปฏิเสธการลบไฟล์ชั่วคราวที่ไม่ได้เป็นของงานนี้')
    if temporary.is_file():
        temporary.unlink()


def finalize_output(temporary: Path, target: Path) -> None:
    if not _is_temporary_output_for(temporary, target):
        raise ValueError('ไฟล์ชั่วคราวไม่ตรงกับไฟล์ผลลัพธ์ของงาน')
    if not temporary.is_file() or temporary.stat().st_size == 0:
        raise FFmpegError('ไม่พบไฟล์ผลลัพธ์ชั่วคราวที่สมบูรณ์')
    temporary.replace(target)


def output_path(source: Path, destination: Path, mode: str, audio_format: str) -> Path:
    suffix = f'.{audio_format.lower()}' if mode == 'audio' else '.mp4'
    operation = 'audio' if mode == 'audio' else 'converted'
    return destination / f'{source.stem}_{operation}{suffix}'


def build_command(
    source: Path,
    target: Path,
    mode: str,
    quality: str,
    audio_format: str,
) -> list[str]:
    command = ['ffmpeg', '-y', '-loglevel', 'error', '-i', str(source)]
    if mode == 'audio':
        codecs = {
            'mp3': ['-c:a', 'libmp3lame', '-q:a', '2'],
            'm4a': ['-c:a', 'aac', '-b:a', '192k'],
        }
        try:
            codec = codecs[audio_format.lower()]
        except KeyError as exc:
            raise ValueError(f'ไม่รองรับรูปแบบเสียง: {audio_format}') from exc
        command += ['-map', '0:a:0', '-vn', *codec]
    elif mode == 'video':
        try:
            crf = {'High': '18', 'Balanced': '23', 'Small': '28'}[quality]
        except KeyError as exc:
            raise ValueError(f'ไม่รองรับระดับคุณภาพ: {quality}') from exc
        command += [
            '-map',
            '0:v:0',
            '-map',
            '0:a:0?',
            '-c:v',
            'libx264',
            '-crf',
            crf,
            '-preset',
            'medium',
            '-c:a',
            'aac',
            '-b:a',
            '192k',
            '-movflags',
            '+faststart',
        ]
    else:
        raise ValueError(f'ไม่รองรับโหมด: {mode}')
    return [*command, '-progress', 'pipe:1', '-nostats', str(target)]


def _timestamp_seconds(value: str) -> float | None:
    try:
        hours, minutes, seconds = value.split(':')
        parsed = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed >= 0 else None


def parse_progress_line(raw_line: str, duration: float | None) -> float | None:
    key, separator, value = raw_line.strip().partition('=')
    if not separator:
        return None
    if key == 'progress' and value == 'end':
        return 1.0
    if not duration:
        return None
    if key == 'out_time':
        elapsed = _timestamp_seconds(value)
    elif key == 'out_time_us':
        try:
            elapsed = float(value) / 1_000_000
        except ValueError:
            return None
    else:
        return None
    if elapsed is None:
        return None
    return max(0.0, min(elapsed / duration, 1.0))


def convert(
    command: list[str],
    target: Path,
    duration: float | None,
    on_progress: Callable[[float], None],
    cancellation: CancellationToken | None = None,
) -> None:
    token = cancellation or CancellationToken()
    if token.cancelled:
        raise ConversionCancelled('ยกเลิกงานแล้ว')
    diagnostics: deque[str] = deque(maxlen=40)
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
    )
    token.attach(process)
    assert process.stdout is not None
    try:
        for raw_line in process.stdout:
            progress = parse_progress_line(raw_line, duration)
            if progress is not None:
                on_progress(progress)
            key = raw_line.strip().partition('=')[0]
            if key not in PROGRESS_KEYS and raw_line.strip():
                diagnostics.append(raw_line.strip())
    finally:
        process.stdout.close()
        return_code = process.wait()
        token.detach(process)
    if token.cancelled:
        raise ConversionCancelled('ยกเลิกงานแล้ว')
    if return_code != 0:
        detail = '\n'.join(diagnostics)
        raise FFmpegError(detail or f'FFmpeg หยุดทำงานด้วยรหัส {return_code}')
    if not target.is_file() or target.stat().st_size == 0:
        raise FFmpegError('FFmpeg ทำงานเสร็จแต่ไม่พบไฟล์ผลลัพธ์ที่สมบูรณ์')
