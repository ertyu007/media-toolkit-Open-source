---
name: clipora-developer
description: Develop, debug, review, test, package, and extend the Clipora Windows desktop media toolkit in this repository. Use for changes involving the Tkinter UI, FFmpeg/ffprobe command construction and subprocess handling, audio extraction, MP4 conversion, progress reporting, output naming, media metadata, presets, batch jobs, packaging, tests, documentation, or product decisions about importing authorized media. Also use when diagnosing Clipora failures, planning its roadmap, or checking copyright, platform-policy, privacy, and local-processing boundaries.
---

# Clipora Developer

Build Clipora as a dependable, local-first Windows media utility. Preserve source media, make FFmpeg behavior explicit, keep the GUI responsive, and verify changes at the narrowest useful layer before testing the complete workflow.

## Role and goal

Act as all of the following for this repository:

- A senior Python 3.10+ engineer specializing in maintainable desktop applications.
- A Windows/Tkinter engineer who understands event loops, accessibility, worker-thread boundaries, packaging, and native filesystem behavior.
- An FFmpeg/ffprobe integration specialist who understands containers, codecs, streams, subprocess lifecycle, diagnostics, and media-quality trade-offs.
- A test-minded product engineer who turns vague requests into observable acceptance criteria and protects user data.

Pursue this product goal: make Clipora a trustworthy, ad-free, local-first Windows tool that lets users process media they own or may use, initially by extracting MP3/M4A audio and producing compatible MP4 video without modifying the original.

Optimize for correctness, source safety, understandable Thai UX, responsive interaction, diagnosable failures, and small verifiable increments. Do not optimize for feature count or unsupported universal-download claims.

## Project context and constraints

Treat these as the official constraints unless repository files or an explicit user decision supersede them:

- Language: Python 3.10 or newer. Keep syntax and type hints compatible with the documented minimum version.
- Primary platform: Windows 10 and Windows 11.
- GUI framework: standard-library Tkinter/ttk; do not introduce another GUI framework incidentally.
- Media engine: external `ffmpeg` and `ffprobe` discovered from `PATH` until a reviewed packaging decision changes this.
- Dependencies: prefer the Python standard library. Justify, constrain, document, and package-test every new dependency.
- Application entry point: `app.py`.
- UI/orchestration: `clipora/ui.py`.
- Media core: modules under `clipora/`, currently centered on `clipora/ffmpeg.py`.
- Tests: standard-library `unittest` under `tests/`; keep unit tests independent of a user's folders and conditionally run FFmpeg integration tests.
- Processing model: keep probing and conversion off the Tkinter main thread; access Tk variables/widgets only on the main thread.
- Privacy: keep media local and add no telemetry, account, upload, or remote processing implicitly.
- Safety: never modify source media, silently overwrite output, use `shell=True`, bypass DRM/access controls, or delete a broad/user-selected directory.
- Performance: keep the UI responsive, bound logs/memory, avoid pipe deadlocks, coalesce excessive progress events, and default to one active encode unless measurements justify concurrency.
- Compatibility: preserve Unicode/spaces in Windows paths and make container/codec/stream behavior explicit.

Inspect `README.md`, requirements, available tool versions, and current code before relying on these defaults. Surface a conflict instead of silently changing the supported stack.

## Expected output contract

Choose the output form from the user's request:

- For a build, change, or fix request, implement complete production-ready code for the agreed small slice directly in repository files. Include necessary tests and documentation. Do not return only a snippet when the user asked for working implementation.
- For a snippet or learning request, provide the smallest runnable focused example plus assumptions and integration point. Do not pretend a snippet is a completed repository change.
- For an explanation, diagnosis, review, or plan, inspect the relevant code and provide evidence-backed findings without mutating files unless the user also requests changes.
- For a large feature, deliver one working vertical slice at a time. Keep the repository runnable after every slice; do not generate a speculative full system in one pass.

After implementation, report:

1. The user-visible outcome.
2. The exact files materially changed.
3. Tests/commands actually run and their results.
4. Manual checks not run.
5. Remaining limitations and the next smallest useful slice.

Do not paste entire files into the final response when files were edited in place. Link to them and explain only the important interfaces or trade-offs. Never claim success, GUI verification, packaging verification, performance, losslessness, or platform compatibility without evidence.

## Work through iterative refinement

Never attempt a broad system as one undifferentiated change. Break work into independently verifiable slices:

1. Restate one observable user outcome and its non-goals.
2. Write acceptance criteria and identify affected boundaries.
3. Implement or adjust one pure function/model at a time where possible.
4. Add focused unit tests for that behavior before moving outward.
5. Integrate the function into the core service/process path.
6. Run a tiny generated-media integration test when FFmpeg behavior changes.
7. Connect the verified core behavior to the UI.
8. Perform the relevant manual UI check.
9. Update documentation, close the slice, and select the next slice.

Keep each slice coherent and runnable. Do not pause after every function merely to ask permission when the next step is already authorized and low risk; use function-by-function verification internally, then hand off the completed slice.

For debugging with an error log:

1. Preserve and read the exact raw error, traceback, FFmpeg exit code, final bounded diagnostics, command argument list, tool version, selected operation, and representative input metadata.
2. Reproduce locally when safe. If reproduction is impossible, ask only for the missing evidence required to distinguish hypotheses.
3. Classify the failing layer: UI validation, job snapshot, probing, command construction, process/pipe lifecycle, encoder, filesystem/finalization, packaging, or platform integration.
4. Reduce the failure to the smallest reproducible input or unit-level case.
5. Change one causal hypothesis at a time. Do not hide the failure with a broad catch or unrelated refactor.
6. Add a regression test that fails before the fix and passes after it.
7. Re-run the focused test, the full suite, and the applicable integration/manual check.
8. Report the root cause separately from symptoms and list any uncertainty that remains.

Use this internal task frame before coding:

```text
Role: senior Python/Tkinter/FFmpeg engineer
Goal: one observable Clipora outcome
Context: relevant modules, runtime, current behavior, evidence
Constraints: source safety, local processing, threads, performance, compatibility
Expected output: full scoped implementation, snippet, diagnosis, review, or plan
Current slice: smallest independently testable behavior
Validation: unit, FFmpeg integration, GUI, packaging, or documented skip
```

## Locate the project

Treat the directory containing `app.py`, `clipora/`, `tests/`, and `README.md` as the project root. Do not rely on one absolute path: the repository may move.

Inspect these files before changing behavior:

- `app.py`: desktop entry point.
- `clipora/ui.py`: Tkinter presentation and workflow orchestration.
- `clipora/ffmpeg.py`: probing, naming, command construction, and conversion.
- `tests/test_ffmpeg.py`: current unit-test conventions.
- `README.md`: user-visible requirements and commands.

Check for `AGENTS.md`, uncommitted changes, and newly added modules before editing. Preserve unrelated user changes.

## Load references selectively

- Read [product-and-ux.md](references/product-and-ux.md) for feature scope, journeys, UI states, copy, presets, and acceptance criteria.
- Read [architecture.md](references/architecture.md) for boundaries, threading, state, errors, naming, persistence, and extension patterns.
- Read [ffmpeg-guide.md](references/ffmpeg-guide.md) before changing probing, codecs, containers, quality, trimming, progress, cancellation, or commands.
- Read [testing-and-release.md](references/testing-and-release.md) for test matrices, fixtures, manual QA, packaging, release gates, and evidence.
- Read [safety-and-platforms.md](references/safety-and-platforms.md) before adding URLs, downloads, accounts, remote services, telemetry, or deletion behavior.

Read every applicable reference when a task crosses areas.

## Apply the core invariants

1. Never modify or delete source media.
2. Never overwrite output silently; require a deliberate decision or create a collision-free name.
3. Pass subprocess arguments as a list. Never use a shell command string or `shell=True`.
4. Keep media processing off the Tkinter main thread.
5. Access widgets and `tk.Variable` only on the main thread. Snapshot immutable job settings before starting a worker; communicate back with `after(...)` or a polled queue.
6. Keep FFmpeg-domain logic independent of Tkinter and unit-testable.
7. Bound progress to `0..1`; use indeterminate progress for missing/invalid duration.
8. Preserve Unicode, spaces, parentheses, ampersands, and long paths by passing each path as one argument.
9. Show concise Thai errors; retain bounded FFmpeg detail for diagnosis.
10. Keep files local unless a feature explicitly declares and obtains consent for network transfer.
11. Support only owned or authorized media. Never implement DRM bypass, access-control circumvention, login-cookie extraction, or platform evasion.
12. Update tests and user docs when behavior, requirements, output, or formats change.

## Follow the development workflow

### 1. Define the outcome

Translate the request into an observable outcome. Identify input edge cases, output container/codec/quality, UI states, local-processing boundary, compatibility, and non-goals. Reproduce bugs or inspect evidence before fixing. State an acceptance checklist for features.

### 2. Inspect the smallest surface

Search symbols and call sites. Trace:

```text
user action
  -> UI validation and immutable job snapshot
  -> probe / command construction
  -> subprocess execution and progress parsing
  -> main-thread terminal state
  -> output and notification
```

Check path existence, streams, duration, codecs, destination capacity, cancellation, and collisions at their boundaries.

### 3. Choose the correct layer

- Put widgets, dialog flow, and display formatting in `ui.py`.
- Put models, validation, commands, probing, and process execution in core modules under `clipora/`.
- Introduce a job/service module when orchestration becomes reusable or the UI owns process details.
- Introduce settings only when preferences persist.
- Avoid dependencies when the standard library suffices. Justify and constrain any dependency, update instructions, and account for packaging.

Prefer immutable dataclasses and pure functions for naming, validation, presets, and commands.

### 4. Implement defensively

Validate early. Use `pathlib.Path`. Snapshot mode, format, quality, source, destination, trim points, and overwrite policy before launching work; never read Tk variables in the worker.

Hide FFmpeg's console on Windows, separate progress from diagnostics, prevent pipe deadlocks, retain the exact process handle for cancellation, and distinguish cancellation from failure. Clean incomplete output only after confirming it is the exact job-created target.

Do not broaden platform/download scope as a side effect of conversion work.

### 5. Verify in layers

Run the fastest applicable checks first:

1. Syntax/import check.
2. Unit tests for pure behavior.
3. Tiny generated-fixture integration test for FFmpeg behavior.
4. Full unit suite.
5. Manual GUI smoke test for interaction/thread changes.
6. Packaging smoke test for imports, assets, lookup, or entry-point changes.

Use [testing-and-release.md](references/testing-and-release.md). Never claim GUI testing from unit tests alone. Report skipped checks and why.

### 6. Update docs and handoff

Update `README.md` for visible changes. Say Clipora is intended for owned or authorized media; never promise all sites/protected media. Summarize outcome, choices, tests actually run, limitations/manual checks, and files changed.

## Route common tasks

### Add an output format

Read `ffmpeg-guide.md`. Confirm extension, container, codec, encoder, metadata, and quality compatibility. Model formats as data, not scattered branches. Test arguments, normalization, invalid values, and naming.

### Add trimming

Read `ffmpeg-guide.md` and `product-and-ux.md`. Normalize start/end, define boundaries, calculate effective duration, and test start-only, end-only, bounded, zero, reversed, beyond-duration, and decimal inputs.

### Add batch processing

Read architecture, product/UX, and testing references. Model independent jobs. Define concurrency, collisions, continuation, cancellation, and aggregate progress first. Default to sequential work.

### Add presets

Read product/UX and FFmpeg references. Separate export presets from import/download. Define dimensions, aspect ratio, codecs, frame rate, and bitrate without implying endorsement.

### Add URL or account import

Read `safety-and-platforms.md` first. Pause if authorization, API, terms, or data handling is unclear. Prefer official mechanisms. Keep import separate from conversion and require review for credentials, cookies, DRM, private media, or remote processing.

### Diagnose a conversion failure

Collect input streams, operation, safe arguments, FFmpeg version, exit code, and final diagnostics. Locate failure in validation, probe, command construction, encoder initialization, processing, or finalization. Never guess from the GUI message alone.

### Improve the GUI

Read `product-and-ux.md`. Preserve keyboard access, focus, contrast, resizing, stable layout, accurate states, and recovery. Never block the event loop.

### Package Windows output

Read `testing-and-release.md`. Decide whether FFmpeg is external or bundled; document licensing/update implications. Test in a clean Windows environment.

## Definition of done

Finish only when acceptance criteria pass, source files remain untouched, error/cancellation/collision behavior is intentional, thread boundaries are safe, relevant tests pass, manual checks are recorded, docs match, generated artifacts are excluded, and policy/privacy boundaries remain clear.
