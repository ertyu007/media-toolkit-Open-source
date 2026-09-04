---
name: feature
description: Use when adding a new feature, output format, converter behavior, URL download scope, or any behavior change to Clipora. Trigger keywords: new feature, add format, add option, feature request, implement, converter, stem, download, trim, batch.
---

# Adding a feature to Clipora

## Step 1 — Vertical slice

Follow the 8-step workflow from `docs/DEVELOPMENT.md` §5:

1. Write one outcome + acceptance criteria.
2. Identify modules and non-goals.
3. Change the smallest pure function/model first.
4. Add unit tests.
5. Wire the core process + add a generated-fixture integration test.
6. Connect the UI only after core passes.
7. Manual interaction checks.
8. Update docs (`docs-sync` skill).

## Step 2 — PC conventions (non-negotiable)

- Python 3.10+ compatible; type hints in core/public functions; `pathlib.Path` for paths.
- subprocess **argument lists**, never `shell=True`; hide FFmpeg console on Windows.
- Never touch Tk widgets from a worker thread; snapshot a `JobSpec` before the worker; UI updates via `after`/queue.
- Never modify/delete source media; keep the previous output until a job fully succeeds.
- New dependency: pin an immutable HTTPS URL + SHA-256, never `latest`. Update `clipora/dependencies.py` **and** `THIRD_PARTY_NOTICES.md` together.
- URL download scope: public, single-item, authorized media only. No accounts/cookies/DRM bypass without an explicit product/security review.
- Cancel: hold the exact process handle; kill the yt-dlp process tree (it may spawn FFmpeg). Use `--ignore-config`.

## Step 3 — Tests

Run from the repo root:

```powershell
python -m compileall -q app.py clipora tests scripts
python -W error::ResourceWarning -m unittest discover -s tests -v
```

- Unit test every pure function/model.
- Integration tests: generate small media fixtures via FFmpeg lavfi in a temporary directory; skip clearly when tools are missing; assert output is probed, not just that it exists; verify source unchanged where relevant.
- For bugs: capture exact error/traceback/exit code/diagnostic tail, add a regression test, change one causal hypothesis at a time.

## Step 4 — Known pitfalls (from `docs/WORK_NOTES.md`)

- `amix` filtergraph needs labeled inputs (`[0:a][1:a]...`) and `-map [aout]` or it fails with "Cannot find an unused audio input stream".
- Staging directories must be replaced shallow → deep; moving `python` first drops `site-packages` wheels.
- Test helpers that write zips must pass `zipfile.ZipInfo(name, (1980,1,1,0,0,0))` to `writestr`, otherwise timestamps make checksums flaky across runs.

## Step 5 — Docs + work notes

- Update docs per the `docs-sync` skill.
- Record status in `docs/WORK_NOTES.md` when relevant.
- Manual GUI checks you could not run must be reported in the summary, never implied as tested.
