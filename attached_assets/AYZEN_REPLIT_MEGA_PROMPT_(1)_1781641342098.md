# 🚀 AYZEN WORKSPACE — REPLIT DEPLOYMENT MEGA PROMPT

---

## PASTE THIS ENTIRE PROMPT TO REPLIT AGENT (NEW REPL):

---

You are setting up a production-ready full-stack workspace application called **AYZEN WORKSPACE** on Replit Free Tier. Your #1 priority is ensuring the app deploys successfully without port conflicts, healthcheck failures, or session timeouts.

---

## 🔴 CRITICAL RULES — READ BEFORE ANYTHING ELSE

1. **ONE SINGLE PORT ONLY: `8080`** — Replit Free Tier only allows one exposed port. Everything must run through port `8080`. No exceptions.
2. **NO separate Python port, NO separate frontend port** — The Node.js API server on port `8080` will act as a reverse proxy for everything.
3. **Healthcheck route `/api` must return HTTP 200** within 5 seconds of startup, or Replit will kill the process.
4. **Never use `process.env.PORT || 3000`** — Always hardcode `const PORT = 8080` or read `process.env.PORT` which Replit sets to `8080`.
5. **Free Tier = No background workers** — No `pm2`, no `forever`, no `nodemon` in production. Use a single `node` process.
6. **All services must start from ONE entry point** — Use a single `index.mjs` or `server.js` that spawns child processes internally.

---

## 📁 PROJECT ARCHITECTURE

```
AYZENWORKSPACE/
├── package.json              ← root monorepo (npm workspaces)
├── .replit                   ← Replit config
├── replit.nix                ← Nix packages (Node + Python)
├── packages/
│   ├── api-server/           ← Node.js Express (main server on :8080)
│   │   ├── src/
│   │   │   ├── index.mjs     ← ENTRY POINT — binds to :8080
│   │   │   ├── routes/
│   │   │   ├── middleware/
│   │   │   └── proxy.mjs     ← proxies /api/v1/* to FastAPI :8000 internally
│   ├── python-api/           ← FastAPI (runs internally on :8000, NOT exposed)
│   │   ├── main.py
│   │   └── requirements.txt
│   └── dashboard/            ← React frontend (built as static files)
│       ├── dist/             ← served by Node.js as static files
│       └── src/
└── artifacts/                ← Replit build output (DO NOT manually edit)
```

---

## 📄 REQUIRED FILES — CREATE EXACTLY AS SHOWN

### 1. `.replit` (ROOT)
```toml
modules = ["nodejs-20", "python-3.11"]

[nix]
channel = "stable-24_05"

[deployment]
deploymentTarget = "autoscale"
build = ["sh", "-c", "npm run build"]
run = ["sh", "-c", "npm run start"]

[[ports]]
localPort = 8080
externalPort = 80
```

### 2. `replit.nix` (ROOT)
```nix
{ pkgs }: {
  deps = [
    pkgs.nodejs-20_x
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.uvicorn
  ];
}
```

### 3. `package.json` (ROOT)
```json
{
  "name": "ayzen-workspace",
  "version": "1.0.0",
  "private": true,
  "workspaces": ["packages/*"],
  "scripts": {
    "build": "npm run build:dashboard && npm run build:api",
    "build:dashboard": "cd packages/dashboard && npm run build",
    "build:api": "cd packages/api-server && npm run build",
    "start": "node packages/api-server/dist/index.mjs",
    "dev": "node packages/api-server/src/index.mjs"
  }
}
```

---

## ⚙️ API SERVER — `packages/api-server/src/index.mjs`

```javascript
import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ✅ ALWAYS use port 8080 — this is what Replit exposes
const PORT = parseInt(process.env.PORT || '8080', 10);
const PYTHON_PORT = 8000; // Internal only, never exposed

const app = express();

// ─── 1. HEALTHCHECK — must respond 200 immediately ───────────────────────────
app.get('/api', (req, res) => {
  res.status(200).json({ status: 'ok', service: 'ayzen-workspace', timestamp: Date.now() });
});

// ─── 2. PARSE JSON ────────────────────────────────────────────────────────────
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// ─── 3. PROXY /api/v1/* → FastAPI on internal port 8000 ─────────────────────
// Using pathFilter (NOT app.use prefix) to preserve full /api/v1 path
app.use(
  createProxyMiddleware({
    pathFilter: '/api/v1',
    target: `http://localhost:${PYTHON_PORT}`,
    changeOrigin: true,
    on: {
      error: (err, req, res) => {
        console.error('[Proxy Error]', err.message);
        res.status(502).json({ error: 'Python API unavailable', detail: err.message });
      },
    },
  })
);

// ─── 4. SERVE REACT DASHBOARD (static) ───────────────────────────────────────
const dashboardDist = path.resolve(__dirname, '../../../packages/dashboard/dist');
app.use(express.static(dashboardDist));

// SPA fallback — all non-API routes serve index.html
app.get('*', (req, res) => {
  if (req.path.startsWith('/api')) {
    return res.status(404).json({ error: 'API route not found' });
  }
  res.sendFile(path.join(dashboardDist, 'index.html'));
});

// ─── 5. START PYTHON FASTAPI (internal subprocess) ───────────────────────────
function startPythonAPI() {
  const pythonProcess = spawn(
    'python3',
    ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(PYTHON_PORT), '--reload'],
    {
      cwd: path.resolve(__dirname, '../../../packages/python-api'),
      stdio: 'inherit',
      env: { ...process.env },
    }
  );

  pythonProcess.on('close', (code) => {
    console.log(`[Python API] exited with code ${code}. Restarting in 3s...`);
    setTimeout(startPythonAPI, 3000);
  });

  pythonProcess.on('error', (err) => {
    console.error('[Python API] Failed to start:', err.message);
  });
}

// ─── 6. START SERVER ──────────────────────────────────────────────────────────
app.listen(PORT, '0.0.0.0', () => {
  console.log(`✅ AYZEN API Server running on port ${PORT}`);
  console.log(`✅ Healthcheck: http://localhost:${PORT}/api`);
  console.log(`⚙️  Starting Python FastAPI on internal port ${PYTHON_PORT}...`);
  startPythonAPI();
});
```

---

## 🐍 PYTHON FASTAPI — `packages/python-api/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AYZEN Python API", root_path="/api/v1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "python-api"}

# Add your routes below:
# from routers import tasks, members, auth
# app.include_router(tasks.router)
```

---

## 🔧 ENVIRONMENT VARIABLES (Replit Secrets)

Set these in Replit → Secrets tab:

```
DATABASE_URL=postgresql://...
JWT_SECRET=your-super-secret-key-min-32-chars
NODE_ENV=production
PYTHON_ENV=production
```

---

## ✅ DEPLOYMENT CHECKLIST (Verify before hitting Deploy)

- [ ] `.replit` has `[[ports]] localPort = 8080 externalPort = 80` — only ONE port block
- [ ] `GET /api` returns `{"status":"ok"}` with HTTP 200
- [ ] Python FastAPI starts on `127.0.0.1:8000` (NOT `0.0.0.0:8000`)
- [ ] No code does `app.listen(3000)` or `app.listen(5000)` anywhere
- [ ] `npm run build` completes without errors
- [ ] Dashboard `dist/` folder exists before deployment
- [ ] No `nodemon` or `ts-node` in production start script

---

## 🐛 FIXING COMMON ERRORS FROM LOGS

### Error: `healthcheck /api returned status 500`
**Cause:** `/api` route is crashing before responding.
**Fix:** Make `/api` the very first route, with no middleware before it. Return plain `{status:"ok"}`, no DB calls.

### Error: `not all artifact ports opened within timeout expected=[8080] detected=0`
**Cause:** Server isn't binding to `0.0.0.0:8080` — it's binding to `localhost` or wrong port.
**Fix:** `app.listen(PORT, '0.0.0.0', callback)` — always specify `0.0.0.0`.

### Error: `a port configuration was specified but the required port was never opened`
**Cause:** `.replit` says port 8080 but process crashed before listening.
**Fix:** Add try-catch around startup, ensure Python spawn doesn't block Node from listening.

### Error: `seccomp port detection incomplete`
**Cause:** Process died too fast. Replit couldn't detect the open port.
**Fix:** Node must bind to 8080 FIRST, then spawn Python as a child process.

---

## 📦 DEPENDENCY INSTALL COMMANDS

Run in Replit Shell:
```bash
# Install Python deps
cd packages/python-api && pip install fastapi uvicorn httpx python-jose[cryptography] sqlalchemy asyncpg

# Install Node deps
cd / && npm install

# Build frontend
cd packages/dashboard && npm run build

# Test locally
cd / && npm run start
```

---

## 🎯 FREE TIER SURVIVAL TIPS

1. **Keep responses fast** — Replit kills idle instances. Add a `/api` ping in frontend every 4 minutes.
2. **No heavy startup** — Don't connect DB in startup. Use lazy connection on first request.
3. **Single process** — One Node process manages everything. Don't run separate servers.
4. **Small bundle** — Keep dashboard build under 5MB. Use code splitting.
5. **Startup under 30s** — Replit gives 30 seconds to open port 8080. Python must start fast.

---

*Generated for AYZEN WORKSPACE X1 — Replit Free Tier Deployment Fix*
*Port conflict resolved: Single port 8080, Node proxies to internal Python*
