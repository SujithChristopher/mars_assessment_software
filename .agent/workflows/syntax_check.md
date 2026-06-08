---
description: Check Python syntax using py_compile
---

This workflow runs a syntax check on a specified Python file to catch compile-time errors without executing the script.

Replace `<filename.py>` with the actual file you want to check.

```bash
uv run python -m py_compile <filename.py>
```
