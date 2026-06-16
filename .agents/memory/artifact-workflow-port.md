---
name: Artifact workflow port detection
description: Artifact-managed workflows fail port detection even when the server actually starts; workaround is a separate console workflow.
---

The `artifacts/api-server: API Server` artifact-managed workflow consistently fails with `DIDNT_OPEN_A_PORT` even though the server binary starts correctly and serves requests. The workflow system kills the process after declaring it failed.

**Why:** The artifact workflow's `[services.development].run` command (`pnpm --filter @workspace/api-server run dev`) does NOT receive PORT from the artifact.toml `localPort` — the server requires `PORT` env var explicitly and exits immediately without it. Even after adding `PORT=8080` to the run command, the artifact workflow runtime's port-detection health check times out and marks the workflow "failed", then kills the process.

**How to apply:** When the artifact-managed `artifacts/api-server: API Server` workflow is stuck in "failed" state, create a separate console workflow named `Node API Server` using `configureWorkflow`:

```javascript
await configureWorkflow({
  name: "Node API Server",
  command: "PORT=8080 node --enable-source-maps /home/runner/workspace/artifacts/api-server/dist/index.mjs",
  waitForPort: 8080,
  outputType: "console",
  autoStart: true
});
```

This bypasses the artifact lifecycle entirely. Ensure `dist/index.mjs` is already built before starting (run `pnpm --filter @workspace/api-server run build` if needed). The artifact workflow can be left in "failed" state — it does not conflict when its port is not held.
