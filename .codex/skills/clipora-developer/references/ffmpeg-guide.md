# Clipora FFmpeg Guide

## Contents

1. Discovery and probing
2. Commands and streams
3. Audio formats
4. MP4 and quality
5. Progress
6. Trimming
7. Rotation and filters
8. Cancellation
9. Failure guide
10. Fixtures

## 1. Discovery and probing

Require ffmpeg and ffprobe from the same source. External mode uses configured absolute paths or `shutil.which`; bundled mode resolves both beside packaged resources. Record `ffmpeg -version` for diagnostics, not per job.

Probe JSON and request only needed fields. Validate exit code, JSON, finite duration if present, required streams, selected streams, and rotation metadata when dimensions/filters matter. Some valid media has unknown/unreliable duration; model unknown rather than coercing to zero.

## 2. Commands and streams

Always construct `list[str]`:

```python
[ffmpeg, -y, -i, str(source), -vn, -c:a, libmp3lame, str(target)]
```

Never manually quote or join for execution. Render a separately escaped diagnostic display if needed. Order global options, input options, `-i`, output/filter/codec options, progress options, and target deliberately.

Prefer explicit maps when behavior matters:

- extraction: `-map 0:a:0 -vn`;
- MP4: `-map 0:v:0 -map 0:a:0?`;
- omit subtitles/data/attachments unless supported.

The `?` makes audio optional. Silent video should normally convert; audio extraction must fail before start. Cover art can be a video stream, so expand stream selection based on probe/disposition, not type alone.

## 3. Audio formats

MP3 baseline:

```text
-map 0:a:0 -vn -c:a libmp3lame -q:a 2
```

`-q:a` is libmp3lame's VBR quality scale; do not describe it as a precise bitrate.

M4A/AAC baseline:

```text
-map 0:a:0 -vn -c:a aac -b:a 192k
```

Confirm encoder availability in the distributed build. Compatible original-audio stream copy uses `-c:a copy`, but only after validating input codec against target container. Never promise universal `Original`. Increasing sample rate/bitrate cannot restore lost data.

## 4. MP4 and quality

Compatibility baseline:

```text
-map 0:v:0 -map 0:a:0?
-c:v libx264 -crf 23 -preset medium
-c:a aac -b:a 192k
-movflags +faststart
```

Consider `-pix_fmt yuv420p` for older players, but document loss from higher bit-depth/chroma sources. `+faststart` relocates MP4 metadata; it does not improve quality.

| Label | CRF | Intent |
|---|---:|---|
| High | 18 | high visual quality, larger |
| Balanced | 23 | default trade-off |
| Small | 28 | smaller, more loss |

CRF is not percent; size is not predictable from duration alone. Preset affects speed/compression efficiency, not the quality target. Do not reuse H.264 CRF meanings for other encoders without a new definition.

Define policy before supporting alpha, HDR, variable frame rate, subtitles, multiple tracks, or surround audio.

## 5. Progress

Use machine-readable output:

```text
-progress pipe:1 -nostats
```

Parse recognized keys such as `out_time_us`, `out_time_ms`, `out_time`, `speed`, `total_size`, and `progress`. Verify units against the actual version; historical naming is confusing. Prefer a timestamp or verified microseconds.

Tolerate unknown keys, malformed/missing lines, repeated/non-monotonic values, and values beyond duration. Calculate `clamp(processed/effective_duration, 0, 1)`. Use trim duration when trimming and indeterminate mode for unknown duration. Keep displayed progress monotonic.

Never declare success only from `progress=end`; require zero exit and a valid finalized target.

## 6. Trimming

Input seeking (`-ss` before `-i`) is faster but has accuracy trade-offs. Output seeking (`-ss` after input) is often more accurate but may decode more. For transcoding, define accuracy first and test non-keyframe starts. Use `-t` or `-to` with deliberate placement.

Validate finite values, start >= 0, end > start, known-duration bounds, and a practical minimum duration. Never promise frame-accurate cuts with stream copy. Check A/V synchronization.

## 7. Rotation and filters

Phone videos may use rotation metadata, so stored width/height may not equal display orientation. Inspect side data/tags before aspect-ratio work.

Define filter order: rotation/autorotation policy, crop or fit, scale, pad, sample-aspect ratio, pixel format. Preserve even dimensions when required. Never stretch to a target ratio by default; offer fit/pad or crop with clear behavior.

## 8. Cancellation

Retain the exact process. On cancel:

1. Enter cancelling state.
2. Stop normal completion handling.
3. Request termination.
4. Wait a bounded interval off the UI thread.
5. Kill the exact process tree if required.
6. Consume/close pipes.
7. Mark cancelled.
8. Remove only this job's incomplete target.
9. Restore controls.

Never terminate by process name because unrelated FFmpeg work may exist.

## 9. Failure guide

| Symptom | Check |
|---|---|
| Tool not found | resolved paths, restart after PATH change |
| Empty probe JSON | exit/stderr, file validity, matching tool version |
| Extraction fails | audio stream and encoder availability |
| Silent MP4 fails | optional audio mapping |
| Progress stuck | key/unit/effective duration/raw progress tail |
| App freezes | main-thread blocking or pipe deadlock |
| Unplayable output | premature success, size, output probe |
| Unicode path fails | argument list and actual build |
| A/V drift | seeking/timestamp/filter policy |
| Huge output | CRF, stream copy, filters, source complexity |

## 10. Fixtures

Generate tiny deterministic lavfi fixtures outside committed source: A/V test pattern, silent video, audio-only, portrait, Unicode/spaces, corrupt/truncated, and unusual duration where feasible.

Probe successful targets for nonzero size, streams/codecs, duration tolerance, dimensions, and short decode when needed. Clearly skip integration tests when FFmpeg is unavailable; keep unit tests independent of user installation.
