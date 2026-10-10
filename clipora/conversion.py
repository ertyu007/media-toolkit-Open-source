"""Run one local conversion without UI dependencies."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from .ffmpeg import (
    CancellationToken,
    ConversionCancelled,
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


def run_local_conversion(
    job: JobSpec,
    target: Path,
    cancellation: CancellationToken,
    overwrite: bool = False,
    on_progress: ProgressCallback | None = None,
) -> None:
    """Convert one job, validating its temporary output before finalizing."""
    report = on_progress or (lambda _phase, _value: None)
    temporary = temporary_output_path(target)
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
        else:
            command = build_command(
                job.source,
                temporary,
                job.mode,
                job.quality,
                job.audio_format,
                job.video_format,
                job.fps,
                trim_start,
                trim_duration,
                job.enhance,
            )
            convert(
                command,
                temporary,
                effective_duration,
                lambda value: report('converting', value * 100),
                cancellation,
            )
        if cancellation.cancelled:
            raise ConversionCancelled('ยกเลิกงานแล้ว')
        report('finalizing', 90.0)
        validate_output(temporary, job.mode)
        finalize_output(temporary, target, overwrite=overwrite)
    finally:
        cleanup_temporary_output(temporary, target)
