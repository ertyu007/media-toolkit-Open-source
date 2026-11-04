"""Headless command line interface for Clipora.

The CLI is a thin shell over the same core the desktop UI uses:
``run_local_conversion`` for local files and ``import_url`` for public URLs.
Progress goes to stderr and the batch summary (text or ``--json``) goes to
stdout so automation can parse the result.
"""

from __future__ import annotations

import argparse
import json
import signal
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, NoReturn, Sequence, TextIO

from .conversion import run_local_conversion
from .ffmpeg import (
    AUDIO_FORMATS,
    VIDEO_CONTAINERS,
    CancellationToken,
    ConversionCancelled,
    FFmpegError,
    JobSpec,
    collision_free_output_path,
    output_path,
    parse_trim_seconds,
)
from .importer import ImportSpec, URLImportError, import_url, validate_url


EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_CANCELLED = 130

DEFAULT_MODE = 'audio'
DEFAULT_AUDIO_FORMAT = 'mp3'
DEFAULT_VIDEO_FORMAT = 'mp4'

# CLI value -> core preset. Keeping the mapping explicit keeps the core
# contracts (Thai labels for FPS, English quality presets) untouched.
QUALITY_PRESETS = {'high': 'High', 'balanced': 'Balanced', 'small': 'Small'}
FPS_PRESETS = {'max': 'สูงสุด', '60': '60', '30': '30'}
DOWNLOAD_QUALITY_PRESETS = {'high': 'สูงสุด', 'balanced': '1080p', 'small': '720p'}

PHASE_LABELS = {
    'converting': 'กำลังแปลง',
    'finalizing': 'กำลังบันทึก',
    'downloading': 'กำลังดาวน์โหลด',
}

ProgressCallback = Callable[[str, float], None]


class UsageError(Exception):
    """Invalid command line arguments; reported with exit code 2."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise UsageError(message)


@dataclass(frozen=True)
class FormatSelection:
    """Resolved media mode plus the audio/video container for the core specs."""

    mode: str
    audio_format: str
    video_format: str


@dataclass(frozen=True)
class Settings:
    """Validated command line options, ready to run a batch."""

    command: str
    entries: tuple[str, ...]
    formats: FormatSelection
    quality: str
    download_quality: str
    fps: str
    trim_start: float | None
    trim_duration: float | None
    output_dir: Path | None
    overwrite: bool
    continue_on_error: bool
    enhance: bool
    json_output: bool


@dataclass
class ItemResult:
    """Outcome of one batch entry (success, failure or skipped/cancelled)."""

    index: int
    source: str
    output: Path | None = None
    status: str = 'skipped'
    error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            'index': self.index,
            'input': self.source,
            'output': str(self.output) if self.output is not None else None,
            'status': self.status,
            'error': self.error,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(
        prog='python -m clipora.cli',
        description=(
            'Clipora CLI — แปลงไฟล์ในเครื่องและดาวน์โหลดลิงก์สาธารณะแบบไม่มีหน้าจอ '
            '(ใช้ core เดียวกับโปรแกรมเดสก์ท็อป)'
        ),
    )
    subparsers = parser.add_subparsers(
        dest='command',
        required=True,
        metavar='COMMAND',
    )

    convert = subparsers.add_parser(
        'convert',
        help='แปลงไฟล์ในเครื่อง',
        description='แปลงไฟล์ในเครื่องเป็นเสียงหรือวิดีโอ รองรับหลายไฟล์ต่อครั้ง',
    )
    _add_common_options(convert)
    convert.add_argument(
        'sources',
        nargs='+',
        type=Path,
        metavar='FILE',
        help='ไฟล์ต้นฉบับ 1 ไฟล์ขึ้นไป',
    )

    download = subparsers.add_parser(
        'download',
        help='ดาวน์โหลดลิงก์สาธารณะ',
        description=(
            'ดาวน์โหลดสื่อสาธารณะที่ได้รับอนุญาตผ่าน yt-dlp '
            '(ทีละรายการ ไม่รองรับ playlist/live/private)'
        ),
    )
    _add_common_options(download)
    download.add_argument(
        'urls',
        nargs='+',
        metavar='URL',
        help='ลิงก์ http/https สาธารณะ 1 ลิงก์ขึ้นไป',
    )
    return parser


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--mode',
        choices=('audio', 'video'),
        default=None,
        help='โหมดงาน: audio (เสียง) หรือ video (วิดีโอ); ถ้าไม่ระบุจะอนุมานจาก --format',
    )
    parser.add_argument(
        '--format',
        choices=(*AUDIO_FORMATS, *VIDEO_CONTAINERS),
        default=None,
        help=(
            'รูปแบบผลลัพธ์: mp3/m4a/wav/flac/opus (โหมดเสียง) '
            'หรือ mp4/mov (โหมดวิดีโอ); ค่าเริ่มต้นคือ mp3 หรือ mp4 ตามโหมด'
        ),
    )
    parser.add_argument(
        '--quality',
        choices=tuple(QUALITY_PRESETS),
        default='balanced',
        help=(
            'คุณภาพ: high/balanced/small (ค่าเริ่มต้น balanced) — '
            'งานดาวน์โหลดวิดีโอแมปเป็นความละเอียด สูงสุด/1080p/720p'
        ),
    )
    parser.add_argument(
        '--fps',
        choices=tuple(FPS_PRESETS),
        default='max',
        help='จำกัดเฟรมเรตผลลัพธ์: max (ค่าเริ่มต้น), 60 หรือ 30',
    )
    parser.add_argument(
        '--trim-start',
        default=None,
        metavar='TIME',
        help='จุดเริ่มตัด: วินาที หรือ MM:SS หรือ HH:MM:SS (เว้นว่าง = ไม่ตัด)',
    )
    parser.add_argument(
        '--trim-duration',
        default=None,
        metavar='TIME',
        help='ระยะเวลาที่ตัด: วินาที หรือ MM:SS หรือ HH:MM:SS (เว้นว่าง = ถึงท้ายไฟล์)',
    )
    parser.add_argument(
        '--enhance',
        action='store_true',
        help='เปิดปรับเสียงพอดแคสต์ (ลดนอยส์/เกลี่ยเสียง/ดัง -16 LUFS)',
    )
    parser.add_argument(
        '--output-dir',
        default=None,
        metavar='DIR',
        help=(
            'โฟลเดอร์ผลลัพธ์ (สร้างให้ถ้ายังไม่มี) — '
            'ค่าเริ่มต้น: โฟลเดอร์ของไฟล์ต้นฉบับ (convert) หรือโฟลเดอร์ปัจจุบัน (download)'
        ),
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='เขียนทับไฟล์ผลลัพธ์เดิม (ค่าเริ่มต้นจะเติมเลข (1), (2) ให้แทน)',
    )
    parser.add_argument(
        '--continue-on-error',
        action='store_true',
        dest='continue_on_error',
        help='ทำงานต่อเมื่อไฟล์หนึ่งล้มเหลว (ค่าเริ่มต้นคือหยุดเมื่อพบข้อผิดพลาดแรก)',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        dest='json',
        help='พิมพ์สรุปผลเป็น JSON บรรทัดเดียวที่ stdout (ปิด progress)',
    )


def resolve_formats(mode: str | None, format_value: str | None) -> FormatSelection:
    """Resolve ``--mode``/``--format`` into a consistent selection.

    Video containers require video mode and audio formats require audio mode.
    When ``--mode`` is omitted it is inferred from ``--format``.
    """
    if format_value is None:
        resolved_mode = mode or DEFAULT_MODE
    else:
        format_mode = 'video' if format_value in VIDEO_CONTAINERS else 'audio'
        if mode is not None and mode != format_mode:
            raise UsageError(
                f'รูปแบบ {format_value} ใช้กับโหมด {format_mode} '
                f'แต่ระบุ --mode {mode} — กรุณาเลือกโหมดและรูปแบบให้ตรงกัน'
            )
        resolved_mode = format_mode
    if resolved_mode == 'audio':
        return FormatSelection(
            mode=resolved_mode,
            audio_format=format_value or DEFAULT_AUDIO_FORMAT,
            video_format=DEFAULT_VIDEO_FORMAT,
        )
    return FormatSelection(
        mode=resolved_mode,
        audio_format=DEFAULT_AUDIO_FORMAT,
        video_format=format_value or DEFAULT_VIDEO_FORMAT,
    )


def _ensure_directory(path: Path) -> None:
    if path.exists():
        if not path.is_dir():
            raise UsageError(f'โฟลเดอร์ปลายทางไม่ถูกต้อง (มีไฟล์ชื่อนี้อยู่): {path}')
        return
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise UsageError(f'สร้างโฟลเดอร์ปลายทางไม่สำเร็จ: {path} ({exc})') from None


def _validate_args(parsed: argparse.Namespace) -> Settings:
    formats = resolve_formats(parsed.mode, parsed.format)
    try:
        trim_start = parse_trim_seconds(parsed.trim_start)
        trim_duration = parse_trim_seconds(parsed.trim_duration)
    except ValueError as exc:
        raise UsageError(str(exc)) from None
    if trim_duration is not None and trim_duration <= 0:
        raise UsageError('ระยะเวลาที่ตัดต้องมากกว่า 0')

    if parsed.command == 'convert':
        entries: tuple[str, ...] = tuple(str(path) for path in parsed.sources)
    else:
        validated: list[str] = []
        for raw_url in parsed.urls:
            try:
                validated.append(validate_url(raw_url))
            except ValueError as exc:
                raise UsageError(str(exc)) from None
        entries = tuple(validated)

    # Only touch the filesystem after every argument has been validated, so a
    # usage error never leaves a newly created output directory behind.
    output_dir = Path(parsed.output_dir) if parsed.output_dir is not None else None
    if output_dir is not None:
        _ensure_directory(output_dir)

    return Settings(
        command=parsed.command,
        entries=entries,
        formats=formats,
        quality=QUALITY_PRESETS[parsed.quality],
        download_quality=DOWNLOAD_QUALITY_PRESETS[parsed.quality],
        fps=FPS_PRESETS[parsed.fps],
        trim_start=trim_start,
        trim_duration=trim_duration,
        output_dir=output_dir,
        overwrite=parsed.overwrite,
        continue_on_error=parsed.continue_on_error,
        enhance=parsed.enhance,
        json_output=parsed.json,
    )


class ProgressPrinter:
    """Writes throttled progress updates for one batch to stderr."""

    _WIDTH = 78

    def __init__(self, stream: TextIO, enabled: bool, total: int) -> None:
        self._stream = stream
        self._enabled = enabled
        self._total = total
        self._index = 0
        self._label = ''
        self._bucket = -1
        self._wrote = False

    def begin(self, index: int, label: str) -> ProgressCallback:
        self._index = index
        self._label = label
        self._bucket = -1
        self._wrote = False
        return self._report

    def _report(self, phase: str, percent: float) -> None:
        if not self._enabled:
            return
        clamped = max(0.0, min(percent, 100.0))
        bucket = int(clamped // 5)
        if bucket == self._bucket:
            return
        self._bucket = bucket
        phase_label = PHASE_LABELS.get(phase, phase)
        line = (
            f'[{self._index}/{self._total}] {self._label} — '
            f'{phase_label} {clamped:.0f}%'
        )
        self._stream.write(f'\r{line[: self._WIDTH]}')
        self._stream.flush()
        self._wrote = True

    def end_item(self) -> None:
        if self._enabled and self._wrote:
            self._stream.write('\n')
            self._stream.flush()
        self._wrote = False


class InterruptGuard:
    """Cancels the active job token on the first Ctrl+C; aborts on the second."""

    def __init__(self) -> None:
        self._token: CancellationToken | None = None
        self._interrupts = 0
        self._previous: Any = None
        self._installed = False

    @property
    def interrupted(self) -> bool:
        return self._interrupts > 0

    def install(self) -> None:
        try:
            self._previous = signal.signal(signal.SIGINT, self.handle_sigint)
            self._installed = True
        except (ValueError, OSError):
            # Signal handlers can only be installed from the main thread.
            self._installed = False

    def restore(self) -> None:
        if not self._installed:
            return
        try:
            signal.signal(signal.SIGINT, self._previous)
        except (ValueError, OSError):
            pass
        self._installed = False

    def activate(self, token: CancellationToken) -> None:
        self._token = token

    def deactivate(self) -> None:
        self._token = None

    def handle_sigint(self, _signum: int, _frame: Any) -> None:
        self._interrupts += 1
        if self._interrupts > 1:
            raise KeyboardInterrupt
        sys.stderr.write('\nกำลังยกเลิก… (กด Ctrl+C อีกครั้งเพื่อออกทันที)\n')
        sys.stderr.flush()
        token = self._token
        if token is not None:
            token.cancel()


def build_job(source: Path, destination: Path, settings: Settings) -> JobSpec:
    """Snapshot a ``JobSpec`` from validated CLI settings (same as the UI does)."""
    formats = settings.formats
    return JobSpec(
        source=source,
        destination=destination,
        mode=formats.mode,
        quality=settings.quality,
        audio_format=formats.audio_format,
        video_format=formats.video_format,
        fps=settings.fps,
        trim_start=settings.trim_start,
        trim_duration=settings.trim_duration,
        enhance=settings.enhance,
    )


def build_import_spec(url: str, destination: Path, settings: Settings) -> ImportSpec:
    formats = settings.formats
    return ImportSpec(
        url=url,
        destination=destination,
        mode=formats.mode,
        quality=settings.download_quality,
        audio_format=formats.audio_format,
        video_format=formats.video_format,
        fps=settings.fps,
        enhance=settings.enhance,
        trim_start=settings.trim_start,
        trim_duration=settings.trim_duration,
    )


def _batch_target(base: Path, reserved: set[str], overwrite: bool) -> Path:
    """Reserve a batch-unique target name inside ``base.parent``.

    ``reserved`` holds the names already produced by this batch in the same
    directory. Even with ``--overwrite`` a pre-existing file may only be
    replaced on first use: a later item with the same name must get
    `` (1)``, `` (2)`` so batch outputs never silently replace each other.
    """
    if not overwrite:
        return collision_free_output_path(base, reserved)
    taken = {name.casefold() for name in reserved}
    if base.name.casefold() not in taken:
        return base
    for index in range(1, 1000):
        candidate = base.with_name(f'{base.stem} ({index}){base.suffix}')
        if candidate.name.casefold() not in taken:
            return candidate
    raise FFmpegError('มีไฟล์ชื่อซ้ำกันมากเกินไป')


def _convert_item(
    settings: Settings,
    source: Path,
    destination_dir: Path,
    token: CancellationToken,
    on_progress: ProgressCallback,
    reserved: dict[Path, set[str]],
) -> Path:
    if not source.is_file():
        raise FileNotFoundError(f'ไม่พบไฟล์: {source}')
    formats = settings.formats
    base = output_path(
        source,
        destination_dir,
        formats.mode,
        formats.audio_format,
        formats.video_format,
    )
    names = reserved.setdefault(destination_dir, set())
    target = _batch_target(base, names, settings.overwrite)
    names.add(target.name)
    job = build_job(source, target, settings)
    run_local_conversion(
        job,
        target,
        token,
        overwrite=settings.overwrite,
        on_progress=on_progress,
    )
    return target


def _download_item(
    settings: Settings,
    url: str,
    destination_dir: Path,
    token: CancellationToken,
    on_progress: ProgressCallback,
    reserved: dict[Path, set[str]],
) -> Path:
    spec = build_import_spec(url, destination_dir, settings)
    names = reserved.setdefault(destination_dir, set())

    def report(value: float) -> None:
        on_progress('downloading', value * 100.0)

    def on_conflict(target: Path) -> bool:
        # A batch-produced name must not be replaced ("keep both"), so the core
        # numbers it instead. A pre-existing file is still replaceable.
        return target.name.casefold() not in {name.casefold() for name in names}

    if settings.overwrite:
        produced = import_url(
            spec,
            report,
            cancellation=token,
            on_conflict=on_conflict,
        )
    else:
        # No conflict callback: the core keeps the existing file and picks "(1)".
        produced = import_url(spec, report, cancellation=token)
    names.add(produced.name)
    return produced


def _item_label(command: str, entry: str) -> str:
    return Path(entry).name if command == 'convert' else entry


def summary_payload(
    command: str,
    results: Sequence[ItemResult],
    exit_code: int,
) -> dict[str, Any]:
    succeeded = sum(1 for result in results if result.status == 'ok')
    failed = sum(1 for result in results if result.status == 'failed')
    skipped = sum(1 for result in results if result.status in {'skipped', 'cancelled'})
    return {
        'command': command,
        'exit_code': exit_code,
        'cancelled': exit_code == EXIT_CANCELLED,
        'total': len(results),
        'succeeded': succeeded,
        'failed': failed,
        'skipped': skipped,
        'items': [result.as_dict() for result in results],
    }


def format_summary(
    command: str,
    results: Sequence[ItemResult],
    exit_code: int,
) -> str:
    succeeded = sum(1 for result in results if result.status == 'ok')
    failed = sum(1 for result in results if result.status == 'failed')
    skipped = sum(1 for result in results if result.status in {'skipped', 'cancelled'})
    lines = [
        f'สรุปผล: ทั้งหมด {len(results)} รายการ • สำเร็จ {succeeded} • '
        f'ล้มเหลว {failed} • ข้าม {skipped}',
    ]
    for result in results:
        if result.status == 'ok':
            lines.append(f'  [สำเร็จ] {result.source} -> {result.output}')
        elif result.status == 'failed':
            lines.append(f'  [ล้มเหลว] {result.source}: {result.error}')
        elif result.status == 'cancelled':
            lines.append(f'  [ยกเลิก] {result.source}')
        else:
            lines.append(f'  [ข้าม] {result.source}')
    if exit_code == EXIT_CANCELLED:
        lines.append('ยกเลิกงานแล้ว — ไฟล์ชั่วคราวถูกล้างและไฟล์เดิมยังอยู่ครบ')
    return '\n'.join(lines) + '\n'


def _execute(
    settings: Settings,
    guard: InterruptGuard,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    total = len(settings.entries)
    printer = ProgressPrinter(stderr, enabled=not settings.json_output, total=total)
    results: list[ItemResult] = []
    # Names produced by this batch, scoped per destination directory.
    reserved: dict[Path, set[str]] = {}
    cancelled = False
    stopped = False
    download_dir = settings.output_dir if settings.output_dir is not None else Path.cwd()

    for index, entry in enumerate(settings.entries, 1):
        if cancelled or stopped or guard.interrupted:
            if guard.interrupted:
                cancelled = True
            results.append(ItemResult(index, entry))
            continue

        result = ItemResult(index, entry, status='failed')
        token = CancellationToken()
        guard.activate(token)
        on_progress = printer.begin(index, _item_label(settings.command, entry))
        try:
            if settings.command == 'convert':
                source = Path(entry)
                destination_dir = (
                    settings.output_dir if settings.output_dir is not None else source.parent
                )
                result.output = _convert_item(
                    settings, source, destination_dir, token, on_progress, reserved,
                )
            else:
                result.output = _download_item(
                    settings, entry, download_dir, token, on_progress, reserved,
                )
            result.status = 'ok'
            result.error = None
        except ConversionCancelled as exc:
            result.status = 'cancelled'
            result.error = str(exc) or 'ยกเลิกงานแล้ว'
            cancelled = True
        except (FFmpegError, URLImportError, OSError, ValueError) as exc:
            result.status = 'failed'
            result.error = str(exc) or exc.__class__.__name__
            if not settings.continue_on_error:
                stopped = True
        finally:
            guard.deactivate()
            printer.end_item()

        if result.status == 'failed':
            stderr.write(f'[{index}/{total}] ล้มเหลว: {result.error}\n')
        elif result.status == 'cancelled':
            stderr.write(f'[{index}/{total}] ถูกยกเลิก\n')
        results.append(result)
        if guard.interrupted:
            cancelled = True

    if guard.interrupted:
        cancelled = True
    if cancelled:
        exit_code = EXIT_CANCELLED
    elif any(result.status == 'failed' for result in results):
        exit_code = EXIT_FAILED
    else:
        exit_code = EXIT_OK

    if settings.json_output:
        stdout.write(json.dumps(summary_payload(settings.command, results, exit_code), ensure_ascii=False))
        stdout.write('\n')
    else:
        stdout.write(format_summary(settings.command, results, exit_code))
    stdout.flush()
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    try:
        parsed = parser.parse_args(arguments)
        settings = _validate_args(parsed)
    except UsageError as exc:
        sys.stderr.write(parser.format_usage())
        sys.stderr.write(f'ข้อผิดพลาด: {exc}\n')
        sys.stderr.flush()
        return EXIT_USAGE
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else EXIT_OK
        return EXIT_OK if code == 0 else EXIT_USAGE
    except KeyboardInterrupt:
        # Ctrl+C while parsing/validating (before the guard exists) must still
        # end cleanly with exit code 130 and no traceback.
        sys.stderr.write('\nยกเลิกทันที\n')
        sys.stderr.flush()
        return EXIT_CANCELLED

    guard = InterruptGuard()
    guard.install()
    try:
        return _execute(settings, guard, sys.stdout, sys.stderr)
    except KeyboardInterrupt:
        sys.stderr.write('\nยกเลิกทันที\n')
        sys.stderr.flush()
        return EXIT_CANCELLED
    finally:
        guard.restore()


if __name__ == '__main__':
    raise SystemExit(main())
