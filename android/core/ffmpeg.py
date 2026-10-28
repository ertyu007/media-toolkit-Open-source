"""Android port of ``clipora/ffmpeg.py``.

Kept byte-for-byte compatible with the PC module wherever the platform allows
so ``android/tests/test_core.py`` can assert both sides build the same ffmpeg
command line. Platform deltas:

* no ``creationflags`` (``subprocess`` rejects the kwarg off Windows),
* ``CancellationToken`` signals SIGTERM then SIGKILL instead of ``taskkill``,
* ``probe`` falls back to ``ffmpeg -i`` when the p4a recipe ships no ffprobe,
* mp3 uses ``libshine`` and opus uses the native (experimental) encoder: the
  p4a recipe enables libshine but not libmp3lame/libopus.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import threading
import uuid
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .tools import find_executable


AUDIO_FORMATS = ('mp3', 'm4a', 'wav', 'flac', 'opus')
VIDEO_CONTAINERS = ('mp4', 'mov')
VIDEO_QUALITY_PRESETS = ('High', 'Balanced', 'Small')
FPS_OPTIONS = ('สูงสุด', '60', '30')
PRORES_PROFILES = {
    'High': '3',
    'Balanced': '2',
    'Small': '1',
    'สูงสุด': '3',
    '1080p': '3',
    '720p': '2',
    '480p': '1',
}


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
    video_format: str = 'mp4'
    fps: str = 'สูงสุด'
    trim_start: float | None = None
    trim_duration: float | None = None
    enhance: bool = False


PODCAST_ENHANCE_AF = (
    'silenceremove=start_periods=1:start_duration=0.3:start_threshold=-45dB,'
    'highpass=f=65,afftdn=nr=10:nf=-40,'
    'acompressor=threshold=-20dB:ratio=3:attack=20:release=250:makeup=2dB,'
    'loudnorm=I=-16:TP=-1.5:LRA=11'
)


def build_enhance_filter() -> str:
    """Return the Auphonic-style podcast enhance filter chain (all free built-ins)."""
    return PODCAST_ENHANCE_AF


SILENCE_CUT_THRESHOLD_DB = -35.0
SILENCE_CUT_MIN_DURATION = 0.8
SILENCE_CUT_PAD = 0.25

_SILENCE_START_RE = re.compile(r'silence_start:\s*(-?[0-9]+(?:\.[0-9]+)?)')
_SILENCE_END_RE = re.compile(r'silence_end:\s*(-?[0-9]+(?:\.[0-9]+)?)')


def parse_silence_report(stderr: str, duration: float) -> list[tuple[float, float]]:
    """Parse ``silencedetect`` stderr into ``[(start, end)]`` (pure, testable)."""
    found: list[tuple[float, float]] = []
    pending: float | None = None
    for line in stderr.splitlines():
        start = _SILENCE_START_RE.search(line)
        if start is not None:
            pending = float(start.group(1))
            continue
        end = _SILENCE_END_RE.search(line)
        if end is not None:
            begin = pending if pending is not None else 0.0
            pending = None
            if float(end.group(1)) > begin:
                found.append((begin, float(end.group(1))))
    if pending is not None and duration > pending:
        found.append((pending, duration))
    return found


def detect_silences(
    source: Path,
    duration: float,
    threshold_db: float = SILENCE_CUT_THRESHOLD_DB,
    min_duration: float = SILENCE_CUT_MIN_DURATION,
    start_time: str | None = None,
    duration_time: str | None = None,
) -> list[tuple[float, float]]:
    """Find silent spans with ``silencedetect`` (timeline matches trim args)."""
    ffmpeg = find_executable('ffmpeg')
    command = [str(ffmpeg) if ffmpeg is not None else 'ffmpeg']
    if start_time:
        command += ['-ss', start_time]
    command += [
        '-hide_banner', '-nostats', '-loglevel', 'info', '-i', str(source),
    ]
    if duration_time:
        command += ['-t', duration_time]
    command += [
        '-af', f'silencedetect=noise={threshold_db}dB:d={min_duration}',
        '-f', 'null', '-',
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        tail = (result.stderr or '').strip().splitlines()[-5:]
        raise FFmpegError('\n'.join(tail) or 'ตรวจช่วงเงียบไม่สำเร็จ')
    return parse_silence_report(result.stderr or '', duration)


def keep_intervals(
    silences: Sequence[tuple[float, float]],
    duration: float,
    pad: float = SILENCE_CUT_PAD,
) -> list[tuple[float, float]]:
    """Complement of silences with padded edges (pure); breaths survive."""
    cuts: list[tuple[float, float]] = []
    for start, end in sorted(silences):
        narrowed = (start + pad, end - pad)
        if narrowed[1] > narrowed[0]:
            cuts.append((max(0.0, narrowed[0]), min(duration, narrowed[1])))
    merged: list[list[float]] = []
    for start, end in cuts:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    keeps: list[tuple[float, float]] = []
    cursor = 0.0
    for start, end in merged:
        if start > cursor:
            keeps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < duration:
        keeps.append((cursor, duration))
    return [(s, e) for s, e in keeps if e > s]


def build_av_select_filter(keeps: Sequence[tuple[float, float]]) -> tuple[str, str]:
    """``(video_filter, audio_filter)`` cutting both streams to ``keeps``."""
    expression = '+'.join(f'between(t,{start:.3f},{end:.3f})' for start, end in keeps)
    return (
        f"select='{expression}',setpts=N/FRAME_RATE/TB",
        f"aselect='{expression}',asetpts=N/SR/TB",
    )


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
            self._terminate(process)

    @staticmethod
    def _terminate(process: subprocess.Popen[str]) -> None:
        try:
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError:
                pass
        except OSError:
            pass

    def attach(self, process: subprocess.Popen[str]) -> None:
        with self._lock:
            self._process = process
            cancelled = self._cancelled.is_set()
        if cancelled and process.poll() is None:
            self._terminate(process)

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
    return find_executable('ffmpeg') is not None


def _duration(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed > 0 else None


_DURATION_RE = re.compile(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)')
_VIDEO_STREAM_RE = re.compile(r'Stream #\d+:\d+.*?:\s*Video:')
_AUDIO_STREAM_RE = re.compile(r'Stream #\d+:\d+.*?:\s*Audio:')
_SIZE_RE = re.compile(r'\b(\d{2,5})x(\d{2,5})\b')


def _probe_with_ffmpeg(path: Path) -> MediaInfo:
    """Fallback probe: read the stream table out of ``ffmpeg -i`` output.

    The p4a ffmpeg recipe ships no ffprobe. ``ffmpeg -i`` with no output always
    exits non-zero; the stream table is the useful part.
    """
    ffmpeg = find_executable('ffmpeg')
    if ffmpeg is None:
        raise FFmpegError('ไม่พบ FFmpeg ในแอป กรุณาติดตั้งแอปใหม่')
    result = subprocess.run(
        [str(ffmpeg), '-hide_banner', '-i', str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        check=False,
    )
    report = result.stdout or ''
    if 'Invalid data found' in report or 'No such file' in report:
        raise FFmpegError('อ่านไฟล์ไม่ได้ หรือไฟล์เสียหาย')

    seconds = None
    match = _DURATION_RE.search(report)
    if match:
        hours, minutes, secs = match.group(1), match.group(2), match.group(3)
        seconds = _duration(int(hours) * 3600 + int(minutes) * 60 + float(secs))

    lines = report.splitlines()
    video_line = next((line for line in lines if _VIDEO_STREAM_RE.search(line)), None)
    has_audio = any(_AUDIO_STREAM_RE.search(line) for line in lines)
    if video_line is None and not has_audio and seconds is None:
        raise FFmpegError('อ่านข้อมูลไฟล์ไม่สำเร็จ')

    width = height = None
    size = _SIZE_RE.search(video_line) if video_line else None
    if size:
        width, height = int(size.group(1)), int(size.group(2))
    return MediaInfo(
        duration=seconds,
        has_video=video_line is not None,
        has_audio=has_audio,
        width=width,
        height=height,
    )


def probe(path: Path) -> MediaInfo:
    ffprobe = find_executable('ffprobe')
    if ffprobe is None:
        return _probe_with_ffmpeg(path)
    command = [
        str(ffprobe),
        '-v',
        'error',
        '-show_entries',
        'format=duration:stream=codec_type,width,height',
        '-of',
        'json',
        str(path),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
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


def validate_output(path: Path, mode: str) -> MediaInfo:
    """Probe a completed temporary output and require its expected stream."""
    info = probe(path)
    validate_operation(info, mode)
    return info


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


def finalize_output(temporary: Path, target: Path, overwrite: bool = True) -> None:
    if not _is_temporary_output_for(temporary, target):
        raise ValueError('ไฟล์ชั่วคราวไม่ตรงกับไฟล์ผลลัพธ์ของงาน')
    if not temporary.is_file() or temporary.stat().st_size == 0:
        raise FFmpegError('ไม่พบไฟล์ผลลัพธ์ชั่วคราวที่สมบูรณ์')
    if overwrite:
        temporary.replace(target)
        return
    os.link(temporary, target)
    temporary.unlink()


def output_path(
    source: Path,
    destination: Path,
    mode: str,
    audio_format: str,
    video_format: str = 'mp4',
) -> Path:
    if mode == 'audio':
        suffix = f'.{audio_format.lower()}'
        operation = 'audio'
    else:
        suffix = f'.{video_format.lower()}'
        operation = 'converted'
    return destination / f'{source.stem}_{operation}{suffix}'


def collision_free_output_path(target: Path, reserved: set[str] | None = None) -> Path:
    """Return the first unused ``(n)`` sibling path, including case-insensitive matches."""
    try:
        existing = {entry.name.casefold() for entry in target.parent.iterdir()}
    except OSError:
        existing = set()
    existing.update(name.casefold() for name in (reserved or set()))
    if target.name.casefold() not in existing:
        return target
    for index in range(1, 1000):
        candidate = target.with_name(f'{target.stem} ({index}){target.suffix}')
        if candidate.name.casefold() not in existing:
            return candidate
    raise FFmpegError('มีไฟล์ชื่อซ้ำกันมากเกินไป')


def prores_encoder() -> str | None:
    ffmpeg = find_executable('ffmpeg')
    if ffmpeg is None:
        return None
    try:
        result = subprocess.run(
            [str(ffmpeg), '-hide_banner', '-encoders'],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode:
        return None
    for candidate in ('prores_ks', 'prores', 'prores_aw'):
        if re.search(rf'(?m)^\s*[VFS.]+\s+{candidate}\b', result.stdout):
            return candidate
    return None


def _fps_value(fps: str) -> str | None:
    digits = ''.join(character for character in fps if character.isdigit())
    if not digits:
        return None
    value = int(digits)
    if value < 1:
        return None
    return str(value)


def parse_trim_seconds(text: str | None) -> float | None:
    """Parse a trim time field into seconds.

    Accepts plain seconds (``90``, ``90.5``) or clock formats (``MM:SS``,
    ``HH:MM:SS``). Blank input returns ``None`` (no trim). Raises
    ``ValueError`` with a Thai message for anything else.
    """
    if text is None:
        return None
    cleaned = text.strip()
    if not cleaned:
        return None
    parts = cleaned.split(':')
    if len(parts) > 3:
        raise ValueError(f'รูปแบบเวลาไม่ถูกต้อง: {cleaned} (ใช้ วินาที หรือ HH:MM:SS)')
    try:
        numbers = [float(part) for part in parts]
    except ValueError:
        raise ValueError(f'รูปแบบเวลาไม่ถูกต้อง: {cleaned} (ใช้ วินาที หรือ HH:MM:SS)') from None
    if any(not math.isfinite(number) or number < 0 for number in numbers):
        raise ValueError(f'เวลาในการตัดต้องไม่ติดลบ: {cleaned}')
    if len(parts) == 2 and (numbers[0] >= 60 or numbers[1] >= 60):
        raise ValueError(f'รูปแบบเวลาไม่ถูกต้อง: {cleaned} (ใช้ MM:SS โดยนาทีและวินาทีไม่เกิน 59)')
    if len(parts) == 3 and (numbers[1] >= 60 or numbers[2] >= 60):
        raise ValueError(f'รูปแบบเวลาไม่ถูกต้อง: {cleaned} (ใช้ HH:MM:SS โดยนาทีและวินาทีไม่เกิน 59)')
    multipliers = (1.0, 60.0, 3600.0)
    total = sum(number * multiplier for number, multiplier in zip(reversed(numbers), multipliers))
    return total


def normalize_trim(
    start: float | None,
    duration: float | None,
    media_duration: float | None,
) -> tuple[str | None, str | None, float | None]:
    """Normalize trim bounds against the probed media duration.

    Returns ``(start_arg, duration_arg, effective_duration)`` where the args
    are formatted for ``build_command`` and ``effective_duration`` is the
    expected output length for progress reporting. Raises ``ValueError``
    with a Thai message when the bounds are out of range.
    """
    if start is not None and (not math.isfinite(start) or start < 0):
        raise ValueError('จุดเริ่มตัดต้องไม่ติดลบ')
    if duration is not None and (not math.isfinite(duration) or duration <= 0):
        raise ValueError('ระยะเวลาที่ตัดต้องมากกว่า 0')
    if media_duration is not None and start is not None and start >= media_duration:
        raise ValueError(
            f'จุดเริ่มตัด ({start:.1f} วินาที) เกินความยาวไฟล์ ({media_duration:.1f} วินาที)',
        )
    if media_duration is None:
        start_arg = f'{start:.3f}' if start is not None else None
        duration_arg = f'{duration:.3f}' if duration is not None else None
        return start_arg, duration_arg, None
    base = start or 0.0
    remaining = media_duration - base
    if (start is not None or duration is not None) and remaining <= 0:
        raise ValueError('ไฟล์สั้นกว่าจุดเริ่มตัดที่ระบุ')
    if duration is None:
        effective = remaining if (start is not None or duration is not None) else media_duration
        return (f'{start:.3f}' if start is not None else None, None, effective)
    effective = min(duration, remaining)
    return (f'{start:.3f}' if start is not None else None, f'{effective:.3f}', effective)


def build_command(
    source: Path,
    target: Path,
    mode: str,
    quality: str,
    audio_format: str,
    video_format: str = 'mp4',
    fps: str = 'สูงสุด',
    start_time: str | None = None,
    duration_time: str | None = None,
    enhance: bool = False,
) -> list[str]:
    ffmpeg = find_executable('ffmpeg')
    command = [str(ffmpeg) if ffmpeg is not None else 'ffmpeg']
    if start_time:
        command += ['-ss', start_time]
    command += ['-y', '-loglevel', 'error', '-i', str(source)]
    if duration_time:
        command += ['-t', duration_time]
    if mode == 'audio':
        command += ['-map', '0:a:0', '-vn', *_audio_codec_args(audio_format)]
    elif mode == 'video':
        container = video_format.lower()
        command += ['-map', '0:v:0', '-map', '0:a:0?', *_video_codec_args(container, quality)]
        fps_value = _fps_value(fps)
        if fps_value is not None:
            command += ['-r', fps_value]
    else:
        raise ValueError(f'ไม่รองรับโหมด: {mode}')
    if enhance:
        command += ['-af', build_enhance_filter()]
    return [*command, '-progress', 'pipe:1', '-nostats', str(target)]


def _audio_codec_args(audio_format: str) -> list[str]:
    """Audio codec args (shared by convert + enhance)."""
    codecs = {
        # p4a's ffmpeg recipe ships libshine, not libmp3lame (CBR only).
        'mp3': ['-c:a', 'libshine', '-b:a', '192k'],
        'm4a': ['-c:a', 'aac', '-b:a', '192k'],
        'wav': ['-c:a', 'pcm_s16le'],
        'flac': ['-c:a', 'flac'],
        # No libopus in the recipe; the native encoder is experimental.
        'opus': ['-c:a', 'opus', '-b:a', '160k', '-strict', '-2'],
    }
    try:
        return codecs[audio_format.lower()]
    except KeyError as exc:
        raise ValueError(f'ไม่รองรับรูปแบบเสียง: {audio_format}') from exc


def enhance_audio(
    source: Path,
    target: Path,
    audio_format: str,
    start_time: str | None = None,
    duration_time: str | None = None,
    cut_silence: bool = True,
    on_progress: Callable[[float], None] = lambda _value: None,
    cancellation: CancellationToken | None = None,
) -> None:
    """Enhance audio and cut silent spans (same timeline as trim args)."""
    info = probe(source)
    validate_operation(info, 'audio')
    base = float(duration_time) if duration_time else info.duration
    audio_parts: list[str] = []
    if cut_silence and base:
        if cancellation is not None and cancellation.cancelled:
            raise ConversionCancelled('ยกเลิกงานแล้ว')
        silences = detect_silences(
            source, base,
            start_time=start_time, duration_time=duration_time,
        )
        keeps = keep_intervals(silences, base)
        if keeps and not (len(keeps) == 1 and keeps[0][0] <= 0 and keeps[0][1] >= base):
            _, audio_cut = build_av_select_filter(keeps)
            audio_parts.append(audio_cut)
            base = sum(end - start for start, end in keeps)
    audio_parts.append(build_enhance_filter())
    ffmpeg = find_executable('ffmpeg')
    command = [str(ffmpeg) if ffmpeg is not None else 'ffmpeg']
    if start_time:
        command += ['-ss', start_time]
    command += ['-y', '-loglevel', 'error', '-i', str(source)]
    if duration_time:
        command += ['-t', duration_time]
    command += [
        '-map', '0:a:0', '-vn',
        '-af', ','.join(audio_parts),
        *_audio_codec_args(audio_format),
    ]
    convert([*command, '-progress', 'pipe:1', '-nostats', str(target)],
            target, base, on_progress, cancellation)


def _video_codec_args(container: str, quality: str) -> list[str]:
    """Video+audio codec args for ``container`` (shared by convert + enhance)."""
    if container == 'mp4':
        try:
            crf = {'High': '18', 'Balanced': '23', 'Small': '28'}[quality]
        except KeyError as exc:
            raise ValueError(f'ไม่รองรับระดับคุณภาพ: {quality}') from exc
        return [
            '-c:v', 'libx264', '-crf', crf, '-preset', 'medium',
            '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
        ]
    if container == 'mov':
        encoder = prores_encoder()
        if encoder is None:
            raise ValueError(
                'FFmpeg ที่ติดตั้งไม่รองรับ ProRes กรุณาเลือก MP4 หรืออัปเดตเครื่องมือ'
            )
        try:
            profile = PRORES_PROFILES[quality]
        except KeyError as exc:
            raise ValueError(f'ไม่รองรับระดับคุณภาพ: {quality}') from exc
        return [
            '-c:v', encoder, '-profile:v', profile, '-pix_fmt', 'yuv422p10le',
            '-c:a', 'pcm_s16le',
        ]
    raise ValueError(f'ไม่รองรับรูปแบบไฟล์วิดีโอ: {container}')


def enhance_video(
    source: Path,
    target: Path,
    video_format: str = 'mp4',
    quality: str = 'Balanced',
    fps: str = 'สูงสุด',
    start_time: str | None = None,
    duration_time: str | None = None,
    reencode_video: bool = True,
    cut_silence: bool = True,
    on_progress: Callable[[float], None] = lambda _value: None,
    cancellation: CancellationToken | None = None,
) -> None:
    """Enhance video audio and cut silent spans from picture *and* sound.

    Detection runs on the same trim timeline as the output, so A/V stay in
    sync. With nothing worth cutting this degrades to audio-only enhance
    (copying the picture when ``reencode_video`` is False).
    """
    info = probe(source)
    if not info.has_video:
        raise UnsupportedMediaError('ไฟล์นี้ไม่มีภาพวิดีโอสำหรับปรับเสียง')
    container = video_format.lower()
    if container not in ('mp4', 'mov'):
        raise ValueError(f'ไม่รองรับรูปแบบไฟล์วิดีโอ: {video_format}')
    base = float(duration_time) if duration_time else info.duration
    cutting = False
    video_filter: str | None = None
    audio_parts: list[str] = []
    if cut_silence and base:
        if cancellation is not None and cancellation.cancelled:
            raise ConversionCancelled('ยกเลิกงานแล้ว')
        silences = detect_silences(
            source, base,
            start_time=start_time, duration_time=duration_time,
        )
        keeps = keep_intervals(silences, base)
        if keeps and not (len(keeps) == 1 and keeps[0][0] <= 0 and keeps[0][1] >= base):
            video_filter, audio_cut = build_av_select_filter(keeps)
            audio_parts.append(audio_cut)
            cutting = True
    ffmpeg = find_executable('ffmpeg')
    command = [str(ffmpeg) if ffmpeg is not None else 'ffmpeg']
    if start_time:
        command += ['-ss', start_time]
    command += ['-y', '-loglevel', 'error', '-i', str(source)]
    if duration_time:
        command += ['-t', duration_time]
    command += ['-map', '0:v:0', '-map', '0:a:0?']
    if video_filter is not None:
        command += ['-vf', video_filter]
    if info.has_audio:
        audio_parts.append(build_enhance_filter())
        command += ['-af', ','.join(audio_parts)]
    if reencode_video or cutting:
        command += _video_codec_args(container, quality)
        fps_value = _fps_value(fps)
        if fps_value is not None:
            command += ['-r', fps_value]
    else:
        command += ['-c:v', 'copy']
        if container == 'mov':
            command += ['-c:a', 'pcm_s16le']
        else:
            command += ['-c:a', 'aac', '-b:a', '192k']
    progress_total = base
    if cutting:
        progress_total = sum(end - start for start, end in keeps)
    convert([*command, '-progress', 'pipe:1', '-nostats', str(target)],
            target, progress_total, on_progress, cancellation)


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


def check_disk_space(destination: Path, required_bytes: int = 50 * 1024 * 1024) -> None:
    """Check if the destination disk has enough free space (default 50 MB buffer)."""
    try:
        resolved = destination.resolve()
        while not resolved.exists() and resolved.parent != resolved:
            resolved = resolved.parent
        usage = shutil.disk_usage(resolved)
        if usage.free < required_bytes:
            raise FFmpegError(
                f'พื้นที่ดิสก์ไม่เพียงพอ (เหลือ {usage.free / (1024*1024):.1f} MB, '
                f'ต้องการอย่างน้อย {required_bytes / (1024*1024):.1f} MB)'
            )
    except OSError:
        pass


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
