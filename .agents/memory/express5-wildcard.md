---
name: Express 5 wildcard route
description: Express 5 uses path-to-regexp v8 which rejects bare "*" — use "*splat" for catch-all SPA fallback routes
---

## Rule
In Express 5, never use `app.get("*", handler)`. Use `app.get("*splat", handler)` instead.

**Why:** Express 5 upgraded to path-to-regexp v8, which requires named wildcards. Bare `*` throws `PathError: Missing parameter name at index ...` at startup, crashing the process before it can bind its port.

**How to apply:** Any catch-all route for SPA client-side routing (the `res.sendFile("index.html")` fallback) must use `"*splat"`. Also check any other wildcard route patterns in the app.
