---
name: Proxy body-parser ordering
description: http-proxy-middleware must be registered before express.json() or POST bodies are lost
---

**Rule:** Always register `createProxyMiddleware(...)` BEFORE `express.json()` and `express.urlencoded()` in Express apps that proxy to a Python/other backend.

**Why:** `express.json()` reads and consumes the raw request body stream. Once consumed, the stream is empty. When the proxy middleware runs after it, it forwards an empty body to the target — POST/PUT requests reach the Python API with no payload and it hangs waiting or returns 422. This caused login/register to time out through the Node proxy on port 8080 while GET requests worked fine.

**How to apply:**
- In `artifacts/api-server/src/app.ts`, the middleware order must be:
  1. Healthcheck routes (before everything)
  2. pinoHttp (logging)
  3. cors
  4. `createProxyMiddleware` (pathFilter: "/api/v1") ← BEFORE body parsers
  5. `express.json()`
  6. `express.urlencoded()`
  7. Local `/api` router
- Body parsers only need to run for routes NOT handled by the proxy, so this ordering is safe.
