---
name: Firebase and Groq Python packages
description: Where optional Python packages live and how to import them safely
---

## Rule

`firebase_admin` (7.4.0) and `groq` (1.4.0) are installed in `.pythonlibs`, NOT `.venv`. However, `.venv/bin/python` includes `.pythonlibs` in its `sys.path`, so both are importable when running via the `Python API` workflow (which uses `.venv/bin/python`).

Both packages use **lazy import** inside their respective routers (`firebase_auth.py`, `ai_assistant.py`) — they are imported inside the function body, not at module level. This prevents startup crashes if the package is ever missing.

**Why:** Installing to `.pythonlibs` vs `.venv` can cause confusion; lazy imports are the safety net.

**How to apply:** When adding new optional Python packages, install with `pip install --target .pythonlibs/lib/python3.12/site-packages <pkg>` or via nix, and always use lazy imports inside endpoint functions, not at module level.
