# Clipora Testing and Release Reference

## Contents

1. Test strategy
2. Unit tests
3. FFmpeg integration
4. GUI/thread testing
5. Manual QA
6. Performance
7. Packaging
8. Release gates
9. Evidence

## 1. Test strategy

Use many pure unit tests, focused core/subprocess integration tests, a few GUI smoke tests, and clean-machine packaged-app checks. Make failures identify their layer. Never depend on manual GUI checks for command construction.

Baseline commands from project root:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py clipora
```

Add a test dependency only when it clearly improves value over `unittest`; update requirements/instructions.

## 2. Unit tests

### Naming

Test audio/video suffixes, format case, multiple dots, spaces/Thai, invalid/reserved editable names, collision strategy, and source-target inequality.

### Commands

Test every operation/format/quality, paths as single arguments, video exclusion for audio, required/optional maps, codec/container agreement, overwrite policy, trim combinations, invalid values, and progress flags.

### Progress

Test valid records, unknown fields, malformed lines, missing/zero duration, out-of-range/non-monotonic time, `progress=end`, newline styles, and encoding replacement.

### Validation

Test missing/moved source, bad/unwritable destination, missing tool, missing required stream, bad trim, source equals target, and every collision decision.

Use temporary directories; never write to real Downloads.

For URL import, test URL validation, forbidden credential/internal-network forms, yt-dlp arguments, no-playlist/no-config constraints, progress parsing, quality mapping, collision-free naming, job-owned workspace cleanup, and cancellation that preserves unrelated files.

## 3. FFmpeg integration

Gate on tool availability. Generate tiny fixtures in controlled temp space.

| Case | Expected |
|---|---|
| A/V MP4 -> MP3 | playable audio-only MP3 |
| A/V MP4 -> M4A | playable AAC/M4A |
| A/V -> MP4 | H.264 video and AAC audio |
| Silent video -> MP4 | valid video without audio failure |
| Silent video -> audio | clear unsupported-media result |
| Unicode/spaces path | success |
| Existing target/no overwrite | old bytes unchanged |
| Invalid input | categorized error |
| Cancel encode | cancelled and intentional cleanup |

Probe outputs for streams/codecs and duration tolerance, not existence alone. Test controlled subprocess failure with dependency injection/fake runner or a test-only invalid argument.

## 4. GUI/thread testing

Verify initial/default state, contextual option visibility, validation preserving valid data, controls locked during jobs, main-thread updates, terminal states re-enabling controls, stale-event rejection, close behavior, cancellation, and exact folder opening.

Keep GUI tests separable/skippable in headless environments. Audit:

- Worker receives frozen spec, not Tk variables.
- Worker shows no dialogs.
- Main thread consumes all events.
- Worker exceptions reach a terminal state.
- Threads do not unexpectedly block exit.
- Close does not orphan FFmpeg.
- Pipe readers cannot wait forever after exit.

## 5. Manual QA

### Environment

- Windows 10/11.
- Python launch and packaged launch.
- FFmpeg present and absent/moved.
- First-run with all tools missing; partial tools; Node already installed; repair mode.
- Setup download cancellation, network failure, checksum mismatch, retry, and successful reopen.
- 100%, 125%, 150% scaling after layout changes.

### Paths

- ASCII; spaces/parentheses; Thai/Unicode; long paths.
- Read-only/removed destination.
- Removed source.
- Existing output.
- Safely simulated low disk space where practical.

### Media

- H.264/AAC MP4; MOV/MKV; silent video; audio-only if selectable.
- Portrait/rotation; very short; long enough to observe progress.
- Corrupt; multiple audio streams; variable frame rate when relevant.

### Interaction

- Missing values; repeated mode switches; double start; resize; close during work.
- Early/mid/late cancel; retry after failure; open output folder.

Record exact version/result/untested rows; “looks good” is insufficient evidence.

## 6. Performance

Measure startup/probe/encode time, CPU, peak memory, output size, responsiveness, progress rate, and cancellation latency before optimizing. Default to one encode. Coalesce progress if it overwhelms Tkinter.

Check repeated jobs for leaked processes, threads, handles/pipes, temporary files, callbacks, and diagnostic buffers.

## 7. Packaging

Windows release uses PyInstaller onedir plus a per-user Inno Setup installer. Python/Tkinter are packaged; FFmpeg, yt-dlp and Deno are downloaded explicitly on first run from immutable pinned releases and are not embedded in Setup.

Build with:

```powershell
python -m pip install -r requirements-dev.txt
.\scripts\build_windows.ps1
```

Release configuration lives in `packaging/clipora.spec`, `packaging/clipora.iss`, `packaging/version_info.txt`, and `.github/workflows/release.yml`. Generated icon/build/dist/installer artifacts stay outside Git. Keep `THIRD_PARTY_NOTICES.md` synchronized with the dependency manifest.

Test on a clean Windows VM/account without source tree, developer Python, FFmpeg, yt-dlp, Deno, or Node. Required evidence is Setup install, first-run download, URL/local operation, close, repair, uninstall, and no broad leftover cleanup.

## 8. Release gates

### Code

- Unit/syntax and applicable integration tests pass.
- No deadlock, orphan process, source mutation, or stuck UI state.
- Generated artifacts/local media are ignored.

### Product

- Happy/recovery paths work.
- Labels match actual codec/quality behavior.
- Destination/collision behavior is clear.
- Thai copy fits.
- README matches reality.

### Safety

- Local claim remains true.
- No implicit credential/cookie handling or DRM bypass.
- Cleanup targets only owned incomplete files.
- Third-party licenses/notices are handled.

### Distribution

- Clean-machine launch/tool discovery/conversion succeed.
- App closes cleanly idle and busy.
- Version is visible/reproducible.
- Checksum and notes can be produced.

## 9. Evidence

Report facts:

```text
Passed:
- python -m unittest discover -s tests -v (N tests)
- python -m compileall -q app.py clipora
- MP4 -> MP3 generated-fixture integration

Not run:
- packaged smoke test (package not built)
- 150% scaling (no GUI session)
```

Map a bug to a regression test and feature criteria to tests/manual checks. Never claim “fully tested,” “lossless,” “all files/platforms,” or “secure” without precise evidence and scope.
