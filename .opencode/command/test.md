---
description: Run the full PC test suite (compileall + unittest with ResourceWarning as error).
agent: build
---

Run the Clipora PC test suite from the repo root:

```powershell
python -m compileall -q app.py clipora tests scripts
python -W error::ResourceWarning -m unittest discover -s tests -v
```

Report the final pass/fail count and list any failures with their tracebacks. Do not change any code while running this command. $ARGUMENTS