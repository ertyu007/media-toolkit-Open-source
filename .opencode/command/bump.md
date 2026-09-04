---
description: Bump the Clipora version for PC and sync all version metadata.
agent: build
---

Load the `release` skill.

1. Read current `__version__` from `clipora/__init__.py`; bump it and sync `packaging/version_info.txt` (`filevers`, `FileVersion`, `ProductVersion`) and `packaging/clipora.iss` (`#define AppVersion`), plus the README tag example. Run `python -W error::ResourceWarning -m unittest tests.test_packaging -v` — it must pass.
2. Do not commit, tag, or push unless the user explicitly asks.
3. Report the new version and every file changed.

$ARGUMENTS
