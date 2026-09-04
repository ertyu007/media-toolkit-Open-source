---
name: release
description: Use when releasing Clipora, bumping a version, creating a pc-v* tag, publishing release assets, or writing release notes. Trigger keywords: release, release notes, bump version, tag, publish, pc-v.
---

# Clipora Release

## PC release

1. Read current version from `clipora/__init__.py` → `__version__`.
2. Bump it (semantic). Update **all** PC version locations — `tests/test_packaging.py` enforces sync:
   - `clipora/__init__.py` → `__version__`
   - `packaging/version_info.txt` → `filevers=(X, Y, Z, 0)`, `FileVersion`, `ProductVersion`
   - `packaging/clipora.iss` → `#define AppVersion "X.Y.Z"`
   - `README.md` tag example (`pc-vX.Y.Z`) if shown
3. Run the full PC test suite; `tests/test_packaging.py` must pass:

   ```powershell
   python -m compileall -q app.py clipora tests scripts
   python -W error::ResourceWarning -m unittest discover -s tests -v
   ```

4. Update `docs/WORK_NOTES.md` with release status and prepare release notes (new features, fixes, dependency changes).
5. Commit, then tag and push:

   ```powershell
   git tag pc-vX.Y.Z
   git push origin pc-vX.Y.Z
   ```

6. The `build-windows` job in `.github/workflows/release.yml` runs **only** for `pc-v*` tags. It uploads to the `pc-vX.Y.Z` release:
   - `Clipora-Setup-<ver>-x64.exe` + `.sha256`
   - `Clipora-<ver>-x64.zip` + `.sha256`
7. Verify the release page has all four assets before telling the user it is done.

## Rules

- Never force-push a release tag, and never amend a release commit after pushing the tag.
