# Clipora Architecture Reference

## Contents

1. Current architecture and risks
2. Target boundaries
3. Data model
4. Thread rules
5. Process lifecycle
6. Errors and diagnostics
7. File/naming safety
8. Settings
9. Extension patterns
10. Conventions

## 1. Current architecture and risks

```text
app.py -> CliporaApp (ui.py)
  -> startup tool check -> ToolSetupDialog
     -> dependency worker -> HTTPS/download limit/SHA-256/staging/atomic install
  -> snapshot local JobSpec or URL ImportSpec
  -> worker Thread
     -> local: probe -> build_command -> convert -> ffmpeg
     -> URL: validate -> build_import_command -> yt-dlp/ffmpeg
  <- root.after callbacks
```

Strengths: small entry point, FFmpeg mostly separated, argument-list commands, background media work, and command unit tests.

Address these pressure points only when relevant:

- Worker currently reads Tk variables; snapshot on the main thread.
- One module owns probe, naming, commands, and execution.
- Runner now has a cancellation token and exact FFmpeg process handle; preserve and extend this lifecycle.
- Sequential stdout/stderr reading can deadlock when stderr fills.
- Progress assumes valid duration and one field's unit.
- Naming lacks sanitization/collision alternatives.
- Errors lack stable categories.

Keep refactors reviewable; do not rewrite every pressure point opportunistically.

## 2. Target boundaries

Evolve as complexity requires:

```text
clipora/
  ui.py        widgets/dialogs/main-thread transitions
  setup_ui.py  first-run/repair dialog and worker-to-main-thread progress
  tools.py     managed/bundled/PATH executable discovery
  dependencies.py pinned manifest/download/checksum/safe staging/install record
  importer.py  public URL validation/yt-dlp/progress/temp/finalization
  models.py    immutable JobSpec, MediaInfo, Progress, Result
  media.py     probe and stream validation
  commands.py  pure argument construction and presets
  runner.py    process lifecycle/progress/cancellation/diagnostics
  naming.py    safe names, targets, collisions
  settings.py  local preferences
```

Dependency direction is UI -> application/core -> media/commands/runner. Core never imports Tkinter. Command construction never starts processes. Probe never shows dialogs. Split only when a module has multiple reasons to change, pure logic needs tests, or UI begins owning subprocess protocol.

## 3. Data model

Prefer immutable job input:

```python
@dataclass(frozen=True)
class JobSpec:
    source: Path
    destination: Path
    operation: Operation
    audio_format: AudioFormat | None
    video_quality: VideoQuality | None
    trim_start: float | None = None
    trim_end: float | None = None
    overwrite: bool = False
```

Use enums/validated literals for finite choices. Reject contradictory states while building the spec.

Probe information should include duration/format, video presence and codec/dimensions/frame rate/rotation, audio presence and codec/sample rate/channels, and only needed metadata.

Represent completion explicitly with status (`SUCCEEDED`, `FAILED`, `CANCELLED`), optional target, optional categorized error, and elapsed time. Do not use an exception as the normal UI representation of cancellation.

## 4. Thread rules

- Read Tk variables, widget state, and dialog results on the main thread.
- Create a frozen `JobSpec` before starting a worker.
- Run probe and FFmpeg in a worker.
- Never show dialogs or mutate widgets/variables in a worker.
- Send events with `after(...)` or `queue.Queue`.
- Assign a job ID so stale events cannot update a newer job.
- Lock inputs while owned by a running job.
- Define window-close behavior during work; never silently orphan FFmpeg.

For frequent progress use a queue polled every 50–100 ms to coalesce events and reject stale ones.

## 5. Process lifecycle

```text
CREATED -> STARTING -> RUNNING -> SUCCEEDED
                              -> CANCELLING -> CANCELLED
                              -> FAILED
```

- Use `Popen` with argument list and `shell=False`.
- Use `CREATE_NO_WINDOW` on Windows.
- Consume stdout/stderr without deadlock: separate readers, a diagnostic temp log, or another design that preserves parseability.
- Keep only a bounded diagnostic tail.
- Validate exit code and expected output existence/non-emptiness.
- Treat existing incomplete targets as explicit cleanup responsibility.
- On cancel, request graceful termination, wait a bounded interval off the GUI thread, then terminate the exact process tree if needed.
- Make cleanup idempotent.

Resolve tools only through `tools.py`. Setup-managed executables live under per-user application data and take priority over `PATH`; test overrides are explicit environment variables. yt-dlp receives the resolved FFmpeg directory and JavaScript runtime path.

Dependency installation must download into an owned temporary directory, allow HTTPS only, enforce a bounded size, verify the pinned archive SHA-256, extract only uniquely matched allowlisted members, stage every selected tool, and use atomic replacement. Cancellation never deletes the managed root or a previously working tool.

## 6. Errors and diagnostics

Use stable categories:

- `ValidationError`: missing/invalid input or settings.
- `ToolNotFoundError`: ffmpeg/ffprobe unavailable.
- `ProbeError`: metadata read failed.
- `UnsupportedMediaError`: missing stream or unsupported media.
- `DestinationError`: name, permission, or capacity.
- `ConversionError`: nonzero exit or invalid result.
- Normal cancelled result (or lower-level `CancelledError`).

Carry a safe user message, technical detail, optional exit code, operation stage, and suggested recovery. Avoid full private paths in telemetry. Clipora has no telemetry; never introduce it implicitly. Bound local logs and exclude credentials.

## 7. File and naming safety

Before destructive cleanup:

1. Resolve the exact job target.
2. Confirm it differs from source.
3. Confirm the job created/owns it.
4. Confirm it belongs in the destination when required.
5. Delete only that exact file.

Never recursively delete for one conversion.

Handle Windows invalid characters, reserved names (`CON`, `PRN`, `AUX`, `NUL`, `COM1..9`, `LPT1..9`), trailing dots/spaces, case-insensitive collisions, and practical long-path limits.

Collision policies: explicit overwrite, generated `name (1).ext`, or validated name editing. Test a target appearing between validation and start.

## 8. Settings

Persist only stable preferences: last destination/operation/format/quality, useful geometry, custom FFmpeg path, language/theme. Avoid retaining source history by default.

Store under per-user application data, not installation. Write atomically and tolerate corrupt/newer schemas. Use JSON with `schema_version`; never load settings with pickle.

## 9. Extension patterns

- **Format:** Define extension, container, codec arguments, quality controls, and stream requirements in data. Let UI enumerate and validate centrally.
- **Preset:** Store constraints as data; separate display labels from FFmpeg values.
- **Batch:** Create a queue/controller outside widgets. Give every job spec, state, progress, diagnostics, and target. Default to one active encode.
- **Import:** Create a separate importer returning an authorized local source. Define provenance, temp ownership, authentication, cancellation, limits, and cleanup first.
- **Current public URL import:** Preserve `--ignore-config`, single-item/no-live behavior, no credentials or cookies, bounded diagnostics, 10 GB limit, exact yt-dlp process-tree cancellation, and collision-free finalization from an owned workspace.

## 10. Conventions

- Type public/core functions and keep pure functions deterministic.
- Use `subprocess.run(check=False)` only when intentionally inspecting codes.
- Avoid broad `except Exception` in core; catch unexpected errors at UI boundary only to restore state and retain diagnostics.
- Keep user strings out of command logic.
- Prefer named data maps over unexplained flags.
- Document FFmpeg trade-offs, not obvious Python.
- Keep tests independent of the real Downloads folder.
