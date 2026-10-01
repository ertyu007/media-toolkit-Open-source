# Clipora (media-toolkit) — Agent Guidelines

Clipora is a **local-first media toolkit** shipped as a Windows desktop app (`app.py`, `clipora/`, `packaging/`, `scripts/`, `tests/`) with a Kivy/buildozer Android target in `android/`.

---

## 1. Version source of truth (PC)

- Source of truth: `clipora/__init__.py` → `__version__`.
- Must stay in sync with (enforced by `tests/test_packaging.py`):
  - `packaging/version_info.txt` (`filevers`, `FileVersion`, `ProductVersion`)
  - `packaging/clipora.iss` (`#define AppVersion`)
  - `README.md` tag example
- Release tag: `pc-vX.Y.Z`. Publishing `pc-vX.Y.Z` triggers the `build-windows` job.
- Android has its own version in `android/buildozer.spec`; tag `android-vX.Y.Z` triggers `build-android`. Do **not** bump the PC version for Android-only work.

## 2. Non-negotiable conventions (PC)

From `CONTRIBUTING.md` and `docs/DEVELOPMENT.md`:

- Keep Python 3.10+ compatibility; use type hints in core/public functions; use `pathlib.Path`.
- Use subprocess **argument lists**, never `shell=True`. Hide FFmpeg console on Windows.
- Never touch Tk widgets from a worker thread; snapshot a `JobSpec` before starting a worker; send UI updates via `after`/queue on the main thread.
- Never modify or delete source media. Keep the previous output until a new job fully succeeds.
- Adding a dependency: pin an immutable HTTPS URL + SHA-256, never `latest`. Update `clipora/dependencies.py` **and** `THIRD_PARTY_NOTICES.md` together.
- When behavior changes, update the related docs.
- URL download scope: public, single-item, authorized media only. No accounts, cookies, login, private media, or DRM bypass without an explicit product/security review.

## 2b. Non-negotiable conventions (Android)

- `android/core/` is a **port** of `clipora/ffmpeg.py` + the URL half of `clipora/importer.py`. Change one side, mirror the other — `tests/test_android_core.py` asserts they agree.
- Never touch a Kivy widget from a worker thread. `JobRunner` marshals `(kind, payload)` events through a queue; screens drain it from `Clock`. Snapshot a frozen `ConvertJob` / `DownloadJob` before starting a thread.
- No `creationflags` and no `taskkill` off Windows — `subprocess` rejects the kwarg on POSIX.
- The p4a `ffmpeg` recipe ships **no ffprobe**; `core.ffmpeg.probe()` falls back to parsing `ffmpeg -i`. It picks up a real ffprobe automatically if one is ever bundled.
- The p4a `ffmpeg` binary is `libffmpegbin.so` in `nativeLibraryDir`, and needs `LD_LIBRARY_PATH` set (see `core/tools.py`).
- `ffpyplayer_codecs` and `libx264` are required in `buildozer.spec`; without them there is no H.264 encoder and video conversion cannot work.
- No runtime storage permission: inputs come from SAF (plyer), outputs go to the app's own external files dir.
- Not ported (deliberate): Demucs stem separation, ProRes/After Effects, yt-dlp `--js-runtimes` and `--impersonate`, light theme.

## 3. Docs must match reality

- Update `README.md`, `docs/USER_GUIDE.md`, `docs/TROUBLESHOOTING.md` (and `THIRD_PARTY_NOTICES.md` for dependency changes) as needed.
- New feature / behavior change → record status in `docs/WORK_NOTES.md` when relevant.
- Never claim a feature in docs that is not implemented, and vice versa.

## 4. Testing

Run from the repo root:

```powershell
python -m compileall -q app.py clipora tests scripts android
python -W error::ResourceWarning -m unittest discover -s tests -v
```

Integration tests create small media in a temporary directory and skip when FFmpeg is missing. `test_packaging.py` guards version sync and dependency pinning — it must pass after any PC version/dependency change. `test_android_core.py` guards the Android port against drift from `clipora/`.

## 5. Never commit

- `.exe`, `build/`, `dist/`, `__pycache__/`, `.gradle/`
- `.apk`, `.aab`, `.keystore`, `.jks`, `android/.buildozer/`, `android/bin/`
- Media files (unless tiny, licensed fixtures), logs, credentials, cookies, tokens, local absolute paths
- Secrets in any form; never log or print secret values

## 6. Language

- Code, comments, config, workflow files: **English**.
- User-facing UI copy and user docs: **Thai** (matches the product).

## 7. Release recap

- PC: bump `__version__` (+ sync `version_info.txt`, `.iss`, README) → run `test_packaging` → tag `pc-vX.Y.Z` → push → GitHub Actions builds Setup + portable ZIP + `.sha256` and uploads to the `pc-vX.Y.Z` release.
- Android: bump `version` in `android/buildozer.spec` → tag `android-vX.Y.Z` → push → `build-android` builds a debug APK artifact.
