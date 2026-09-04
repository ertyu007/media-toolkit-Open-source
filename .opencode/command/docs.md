---
description: Audit and update Clipora docs to match the current implementation and version metadata.
agent: build
---

Load the `docs-sync` skill.

1. Verify docs claims against the code — read the implementation and grep for feature names before trusting the docs.
2. Fix stale version numbers, tag examples, dependency versions, and feature lists.
3. Never claim a feature that is not implemented, and never leave a real behavior undocumented.
4. Keep user-facing docs in Thai; keep code/config/workflow content in English.

$ARGUMENTS
