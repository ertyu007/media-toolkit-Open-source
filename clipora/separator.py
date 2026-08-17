from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import deque
from pathlib import Path
from typing import Callable, Sequence

from .ffmpeg import (
    AUDIO_FORMATS,
    CancellationToken,
    ConversionCancelled,
    FFmpegError,
    build_command,
    convert,
    finalize_output,
    probe,
    temporary_output_path,
    validate_operation,
)
from .importer import collision_free_path
from .tools import find_executable, managed_tools_dir

SEPARATOR_MODEL = 'htdemucs_6s'
STEM_SOURCES = ('vocals', 'drums', 'bass', 'guitar', 'piano', 'other')
INSTRUMENTAL_SOURCES = ('drums', 'bass', 'guitar', 'piano', 'other')
SELECTABLE_STEMS = (*STEM_SOURCES, 'instrumental')
STEM_LABELS = {
    'vocals': 'เสียงร้อง',
    'drums': 'กลอง',
    'bass': 'เบส',
    'guitar': 'กีตาร์',
    'piano': 'เปียโน',
    'other': 'อื่นๆ',
    'instrumental': 'ดนตรีรวม',
}
WORKSPACE_PREFIX = '.clipora-separate-'
_PROGRESS_PATTERN = re.compile(r'(\d+(?:\.\d+)?)%')
_PROGRESS_PHASE_LOAD = 0.05
_PROGRESS_PHASE_SEPARATE = 0.70
_ELAPSED_MESSAGE_INTERVAL = 5.0
_FALLBACK_ELAPSED_AFTER = 15.0


class SeparatorError(RuntimeError):
    pass


class SeparatorNotInstalled(SeparatorError):
    pass


class OutputExistsError(SeparatorError):
    pass


def separator_tools_dir() -> Path:
    return managed_tools_dir() / 'separator'


def separator_python_dir() -> Path:
    return separator_tools_dir() / 'python'


def separator_python_exe() -> Path:
    return separator_python_dir() / 'python.exe'


def separator_site_packages() -> Path:
    return separator_python_dir() / 'site-packages'


def separator_models_dir() -> Path:
    return separator_tools_dir() / 'models'


def separator_model_path() -> Path:
    return separator_models_dir() / f'{SEPARATOR_MODEL}.th'


def find_separator_python() -> Path | None:
    override = os.environ.get('CLIPORA_SEPARATOR_PYTHON')
    if override:
        candidate = Path(override).expanduser()
        if candidate.is_file():
            return candidate
    candidate = separator_python_exe()
    return candidate if candidate.is_file() else None


def separator_installed() -> bool:
    return separator_python_exe().is_file() and separator_model_path().is_file()


def separator_environment() -> dict[str, str]:
    environment = dict(os.environ)
    environment['PYTHONPATH'] = str(separator_site_packages())
    environment['PYTHONNOUSERSITE'] = '1'
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    environment['PYTHONUNBUFFERED'] = '1'
    environment['PYTHONUTF8'] = '1'
    environment['TORCH_HOME'] = str(separator_models_dir())
    return environment


def build_separate_command(source: Path, out_dir: Path) -> list[str]:
    python = find_separator_python()
    if python is None:
        raise SeparatorNotInstalled('ยังไม่ได้ติดตั้งเครื่องมือแยกสเต็มเสียง กรุณาติดตั้งก่อน')
    return [
        str(python),
        '-m',
        'demucs',
        '-n',
        SEPARATOR_MODEL,
        '--repo',
        str(separator_models_dir()),
        '--out',
        str(out_dir),
        '--device',
        'cpu',
        '--filename',
        '{stem}.{ext}',
        str(source),
    ]


def build_instrumental_command(stem_dir: Path, target: Path) -> list[str]:
    ffmpeg = find_executable('ffmpeg')
    command = [str(ffmpeg) if ffmpeg is not None else 'ffmpeg', '-y', '-loglevel', 'error']
    for source in INSTRUMENTAL_SOURCES:
        command += ['-i', str(stem_dir / f'{source}.wav')]
    inputs = ''.join(f'[{index}:a]' for index in range(len(INSTRUMENTAL_SOURCES)))
    command += [
        '-filter_complex',
        f'{inputs}amix=inputs={len(INSTRUMENTAL_SOURCES)}:normalize=0:dropout_transition=0[aout]',
        '-map',
        '[aout]',
        '-c:a',
        'pcm_s16le',
        '-progress',
        'pipe:1',
        '-nostats',
        str(target),
    ]
    return command


def parse_demucs_progress(raw_line: str) -> float | None:
    match = _PROGRESS_PATTERN.search(raw_line)
    if not match:
        return None
    try:
        percent = float(match.group(1))
    except ValueError:
        return None
    return max(0.0, min(percent / 100.0, 1.0))


def separate_output_path(source: Path, destination: Path, audio_format: str, stem: str) -> Path:
    suffix = stem.replace('/', '_').replace('\\', '_')
    return destination / f'{source.stem}_{suffix}.{audio_format.lower()}'


def separate_output_paths(
    source: Path,
    destination: Path,
    audio_format: str,
    stems: Sequence[str],
) -> tuple[Path, ...]:
    return tuple(separate_output_path(source, destination, audio_format, stem) for stem in stems)


def create_workspace(destination: Path) -> Path:
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


def cleanup_workspace(workspace: Path, destination: Path) -> None:
    if not _is_owned_workspace(workspace, destination):
        raise ValueError('ปฏิเสธการลบโฟลเดอร์ชั่วคราวที่ไม่ได้เป็นของงานนี้')
    if workspace.is_symlink():
        workspace.unlink()
    elif workspace.is_dir():
        shutil.rmtree(workspace)


def _elapsed_text(started: float) -> str:
    elapsed = max(0.0, time.monotonic() - started)
    if elapsed < 60:
        return f'{elapsed:.0f} วินาที'
    return f'{elapsed / 60:.0f} นาที'


def _separating_message(progress: float, started: float) -> str:
    return f'กำลังแยกสเต็ม… {progress * 100:.0f}% (ผ่านไป {_elapsed_text(started)})'


def _fallback_message(started: float) -> str:
    return f'กำลังแยกสเต็ม… (ผ่านไป {_elapsed_text(started)})'


def _run_demucs(
    command: Sequence[str],
    environment: dict[str, str],
    cancellation: CancellationToken,
    on_phase: Callable[[str], None],
    on_progress: Callable[[float], None],
) -> None:
    if cancellation.cancelled:
        raise ConversionCancelled('ยกเลิกงานแล้ว')
    diagnostics: deque[str] = deque(maxlen=40)
    process = subprocess.Popen(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=environment,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
    )
    cancellation.attach(process, terminate_tree=True)
    assert process.stdout is not None
    started = time.monotonic()
    seen_percent = False
    last_fallback = 0.0
    try:
        for raw_line in process.stdout:
            if cancellation.cancelled:
                raise ConversionCancelled('ยกเลิกงานแล้ว')
            progress = parse_demucs_progress(raw_line)
            if progress is not None:
                seen_percent = True
                on_phase(_separating_message(progress, started))
                on_progress(
                    _PROGRESS_PHASE_LOAD + progress * (_PROGRESS_PHASE_SEPARATE - _PROGRESS_PHASE_LOAD)
                )
                continue
            now = time.monotonic()
            if (
                not seen_percent
                and now - started > _FALLBACK_ELAPSED_AFTER
                and now - last_fallback >= _ELAPSED_MESSAGE_INTERVAL
            ):
                last_fallback = now
                on_phase(_fallback_message(started))
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
        raise SeparatorError(detail or f'การแยกสเต็มเสียงหยุดทำงานด้วยรหัส {return_code}')


def _resolve_target(
    source: Path,
    destination: Path,
    audio_format: str,
    stem: str,
    overwrite: bool,
    collision_free: bool,
) -> Path:
    target = separate_output_path(source, destination, audio_format, stem)
    if collision_free:
        return collision_free_path(target)
    if target.exists() and not overwrite:
        raise OutputExistsError(str(target))
    return target


def _finalize_stems(
    source: Path,
    destination: Path,
    audio_format: str,
    selected: tuple[str, ...],
    stem_dir: Path,
    workspace: Path,
    targets: dict[str, Path],
    on_phase: Callable[[str], None],
    on_progress: Callable[[float], None],
    cancellation: CancellationToken,
) -> list[Path]:
    jobs: list[tuple[Path, str]] = []
    if 'instrumental' in selected:
        instrumental_wav = workspace / 'instrumental.wav'
        duration = None
        for stem in INSTRUMENTAL_SOURCES:
            duration = probe(stem_dir / f'{stem}.wav').duration
            if duration:
                break
        convert(
            build_instrumental_command(stem_dir, instrumental_wav),
            instrumental_wav,
            duration,
            lambda _value: None,
            cancellation,
        )
        jobs.append((instrumental_wav, 'instrumental'))
    jobs.extend((stem_dir / f'{stem}.wav', stem) for stem in selected if stem != 'instrumental')

    on_phase('กำลังแปลงและบันทึกไฟล์…')
    outputs: list[Path] = []
    span = (1.0 - _PROGRESS_PHASE_SEPARATE) / max(len(jobs), 1)
    for index, (wav, stem) in enumerate(jobs):
        if cancellation.cancelled:
            raise ConversionCancelled('ยกเลิกงานแล้ว')
        if not wav.is_file() or wav.stat().st_size == 0:
            raise SeparatorError(f'ไม่พบไฟล์สเต็ม {stem} จากการแยกเสียง')
        target = targets[stem]
        temporary = temporary_output_path(target)

        def report(value: float, _index: int = index) -> None:
            on_progress(_PROGRESS_PHASE_SEPARATE + (_index + value) * span)

        convert(
            build_command(wav, temporary, 'audio', 'Balanced', audio_format),
            temporary,
            probe(wav).duration,
            report,
            cancellation,
        )
        finalize_output(temporary, target)
        outputs.append(target)
    return outputs


def separate_audio(
    source: Path,
    destination: Path,
    audio_format: str,
    stems: Sequence[str] | None = None,
    on_phase: Callable[[str], None] | None = None,
    on_progress: Callable[[float], None] | None = None,
    cancellation: CancellationToken | None = None,
    overwrite: bool = False,
    collision_free: bool = False,
) -> list[Path]:
    if on_phase is None:
        on_phase = lambda _message: None
    if on_progress is None:
        on_progress = lambda _value: None
    selected = tuple(dict.fromkeys(stems)) if stems else SELECTABLE_STEMS
    unsupported = [stem for stem in selected if stem not in STEM_LABELS]
    if unsupported:
        raise ValueError(f'ไม่รองรับสเต็ม: {", ".join(unsupported)}')
    if audio_format.lower() not in AUDIO_FORMATS:
        raise ValueError(f'ไม่รองรับรูปแบบเสียง: {audio_format}')
    if not separator_installed():
        raise SeparatorNotInstalled('ยังไม่ได้ติดตั้งเครื่องมือแยกสเต็มเสียง กรุณาติดตั้งก่อน')
    info = probe(source)
    validate_operation(info, 'audio')

    targets = {stem: _resolve_target(source, destination, audio_format, stem, overwrite, collision_free) for stem in selected}

    token = cancellation or CancellationToken()
    workspace = create_workspace(destination)
    try:
        demucs_dir = workspace / 'stems'
        demucs_dir.mkdir()
        on_phase('กำลังโหลดโมเดลแยกสเต็ม…')
        on_progress(0.03)
        _run_demucs(build_separate_command(source, demucs_dir), separator_environment(), token, on_phase, on_progress)
        stem_dir = demucs_dir / SEPARATOR_MODEL
        return _finalize_stems(
            source,
            destination,
            audio_format,
            selected,
            stem_dir,
            workspace,
            targets,
            on_phase,
            on_progress,
            token,
        )
    finally:
        cleanup_workspace(workspace, destination)