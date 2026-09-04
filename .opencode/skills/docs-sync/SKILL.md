---
name: docs-sync
description: Use when behavior, a feature, a version, or a dependency changed and docs must be updated to match reality. Trigger keywords: update docs, README, user guide, troubleshooting, third party notices, docs out of date, documentation.
---

# Keeping docs in sync with reality

Docs must match implemented behavior — never claim a feature that is not implemented, and never leave a documented behavior stale.

## PC changes

Update as relevant:

- `README.md` — capabilities, install/usage, roadmap, tag examples.
- `docs/USER_GUIDE.md` — every option and flow the user can reach.
- `docs/TROUBLESHOOTING.md` — new failure modes, error handling, log locations.
- `THIRD_PARTY_NOTICES.md` — **required together with any `clipora/dependencies.py` change** (versions, sources, licenses, checksums).
- `docs/WORK_NOTES.md` — feature/behavior status.

Version changes: after bumping, run `python -W error::ResourceWarning -m unittest tests.test_packaging -v` — `test_packaging.py` enforces version sync across `__init__.py`, `version_info.txt`, and `clipora.iss`.

## Step 2 — Verify claims against the code

Before editing, confirm the actual behavior:

- Read the implementation (`clipora/` modules) for the feature in question.
- Grep for the feature name in code before writing it into docs.
- Update version/format strings that are now stale.

## Step 3 — Keep copy Thai

User-facing docs stay in Thai (matches the product). Code/config/workflow language stays English.

## Step 4 — Final consistency check

- No stale version numbers or tag examples.
- No documented option that does not exist in the UI.
- No undocumented option either — but when unsure, prefer being explicit about scope.
