---
description: Guide a Clipora release end-to-end, including version bump, tests, tag and release verification.
agent: build
---

Load the `release` skill and follow its checklist.

1. Bump `clipora/__init__.py` + `packaging/version_info.txt` + `packaging/clipora.iss` + README tag example → run the full test suite (test_packaging must pass) → update WORK_NOTES + release notes → tag `pc-vX.Y.Z` → push.
2. Only tag/push when the user explicitly confirms.

$ARGUMENTS
