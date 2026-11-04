"""Run one local conversion without UI dependencies."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .ffmpeg import (
    CancellationToken,
    ConversionCancelled,
    FFmpegError,
    JobSpec,
    build_command,
    cleanup_temporary_output,
    convert,
    enhance_video,
    finalize_output,
    normalize_trim,
    probe,
    temporary_output_path,
    validate_operation,
    validate_output,
)


ProgressCallback = Callable[[str, float], None]

#: Substrings that mark an encoder-initialisation failure (hardware or build
#: capability). Only these trigger the automatic libx264 retry.
_HARDWARE_ERROR_MARKERS = (
    'nvenc',
    'qsv',
    'amf',
    'cannot load',
    'no capable devices',
    'unknown encoder',
    'encoder not found',
    'error while opening encoder',
    'failed to initialise',
    'openencodesession',
)


def is_hardware_encoder_error(message: str) -> bool:
    """True when ``message`` looks like a hardware-encoder failure."""
    lowered = (message or '').lower()
    return any(marker in lowered for marker in _HARDWARE_ERROR_MARKERS)


class _EmptyEnhancedOutput(FFmpegError):
    """The enhance filter consumed every audio frame (fully silent span)."""


def _build_job_command(
    job: JobSpec,
    target: Path,
    trim_start: str | None,
    trim_duration: str | None,
    hardware: bool,
    enhance: bool | None = None,
) -> list[str]:
    return build_command(
        job.source,
        target,
        job.mode,
        job.quality,
        job.audio_format,
        job.video_format,
        job.fps,
        trim_start,
        trim_duration,
        job.enhance if enhance is None else enhance,
        hardware=hardware,
    )


def run_local_conversion(
    job: JobSpec,
    target: Path,
    cancellation: CancellationToken,
    overwrite: bool = False,
    on_progress: ProgressCallback | None = None,
) -> None:
    """Convert one job, validating its temporary output before finalizing.

    A hardware-encoder failure retries exactly once with libx264 on a fresh
    temporary path; an enhanced audio job whose output lost every frame (all
    silence) retries once without the enhance filter. Every other failure
    propagates unchanged and the previous output stays intact.
    """
    report = on_progress or (lambda _phase, _value: None)
    temporary = temporary_output_path(target)
    trim_start: str | None = None
    trim_duration: str | None = None
    effective_duration: float | None = None

    def convert_once(hardware: bool, enhance: bool) -> None:
        convert(
            _build_job_command(
                job, temporary, trim_start, trim_duration, hardware, enhance,
            ),
            temporary,
            effective_duration,
            lambda value: report('converting', value * 100),
            cancellation,
        )
        if cancellation.cancelled:
            raise ConversionCancelled('ยกเลิกงานแล้ว')
        report('finalizing', 90.0)
        try:
            validate_output(temporary, job.mode)
        except FFmpegError as exc:
            if enhance and job.mode == 'audio':
                raise _EmptyEnhancedOutput(str(exc)) from exc
            raise

    def restart() -> None:
        nonlocal temporary
        cleanup_temporary_output(temporary, target)
        temporary = temporary_output_path(target)
        report('converting', 0.0)

    try:
        if cancellation.cancelled:
            raise ConversionCancelled('ยกเลิกงานแล้ว')
        info = probe(job.source)
        validate_operation(info, job.mode)
        if cancellation.cancelled:
            raise ConversionCancelled('ยกเลิกงานแล้ว')
        trim_start, trim_duration, effective_duration = normalize_trim(
            job.trim_start, job.trim_duration, info.duration,
        )
        report('converting', 0.0)
        if job.mode == 'video' and job.enhance:
            enhance_video(
                job.source,
                temporary,
                video_format=job.video_format,
                quality=job.quality,
                fps=job.fps,
                start_time=trim_start,
                duration_time=trim_duration,
                reencode_video=True,
                on_progress=lambda value: report('converting', value * 100),
                cancellation=cancellation,
            )
            if cancellation.cancelled:
                raise ConversionCancelled('ยกเลิกงานแล้ว')
            report('finalizing', 90.0)
            validate_output(temporary, job.mode)
        else:
            try:
                convert_once(job.hardware, job.enhance)
            except FFmpegError as exc:
                if isinstance(exc, _EmptyEnhancedOutput):
                    # The enhance chain (leading-silence trim) removed every
                    # frame; keep the audio by encoding it without enhance.
                    restart()
                    convert_once(job.hardware, False)
                elif job.hardware and is_hardware_encoder_error(str(exc)):
                    # Hardware attempt failed: drop the partial file and
                    # rebuild the exact libx264 command on a fresh path.
                    restart()
                    convert_once(False, job.enhance)
                else:
                    raise
        finalize_output(temporary, target, overwrite=overwrite)
    finally:
        cleanup_temporary_output(temporary, target)
