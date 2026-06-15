# AYZEN Dashboard

Mission control for crypto communities — manage tasks, members, Telegram broadcasts, and analytics from one web dashboard.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the Node.js API-server (port 8080, proxies /api/v1 to Python)
- `pnpm --filter @workspace/dashboard run dev` — run the React dashboard (port 3001)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks + Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string, `SESSION_SECRET` — JWT secret

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: FastAPI (Python) at `apps/api/` on port 8000
- Node.js Express proxy: `artifacts/api-server/` on port 8080 — handles /api and proxies /api/v1 → Python
- Dashboard: React + Vite + shadcn/ui at `artifacts/dashboard/` on port 3001
- DB: PostgreSQL + Drizzle ORM
- Auth: bcrypt + JWT (HttpOnly cookie `ayzen-token`, SESSION_SECRET)
- Validation: Zod, drizzle-zod
- API codegen: Orval (OpenAPI → React Query hooks)
- Build: esbuild (CJS bundle for api-server)

## Where things live

- `apps/api/main.py` — FastAPI app factory, router registrations
- `apps/api/app/routers/` — Python routers: analytics, members, tasks, progress, broadcasts, notifications, settings
- `apps/api/app/middleware/auth.py` — JWT auth middleware using SESSION_SECRET
- `artifacts/api-server/src/app.ts` — Express proxy (http-proxy-middleware with pathFilter)
- `artifacts/dashboard/src/App.tsx` — Routing + auth wiring
- `artifacts/dashboard/src/components/layout.tsx` — Sidebar navigation
- `artifacts/dashboard/src/lib/auth.tsx` — AuthProvider, AuthGuard, useAuth
- `artifacts/dashboard/src/pages/` — All 10 dashboard pages
- `lib/api-client-react/src/generated/api.ts` — Generated React Query hooks
- `lib/api-client-react/src/generated/api.schemas.ts` — Generated Zod schemas + enums

## Architecture decisions

- Node.js api-server proxies /api/v1 using `pathFilter` (NOT path-prefix mounting) to preserve the full path when forwarding to Python FastAPI
- Auth cookies use `samesite=none; secure=true` to work in the proxied iframe preview environment
- Redis unavailable → API runs stateless (no caching)
- Zod v4 (`zod/v4`) is used in server code; form validation in dashboard uses `zod` (v3 compat) for @hookform/resolvers compatibility
- Generated enum types (MemberUpdateRole, TaskUpdateStatus, TaskInputPriority) must be imported from @workspace/api-client-react and cast explicitly — Select's onValueChange returns `string`

## Product

- **Login / Register** — email+password auth, JWT cookie session
- **Dashboard** — KPI cards (total/completed/overdue tasks, active members), 30-day completion chart, leaderboard, recent completions
- **Projects** — create/delete projects, view task counts
- **Project Detail** — per-project task list with inline status/priority editing
- **Tasks** — global task list with status/priority filters, overdue alert, create/delete
- **Members** — roster with role management, leaderboard tab
- **Broadcasts** — compose and send Telegram broadcasts, view history
- **Analytics** — daily snapshots area chart, new-tasks bar chart, top members
- **Notifications** — list with mark-as-read
- **Settings** — language, quiet hours, notification toggles

## Gotchas

- PYTHONPATH must be /home/runner/workspace when running uvicorn
- Do NOT use `pnpm run dev` at workspace root — individual artifacts use workflow-provided PORT env
- The proxy uses pathFilter not `app.use("/api/v1", proxy)` — the latter strips the prefix, breaking FastAPI routing
- Telegram bot requires TELEGRAM_BOT_TOKEN env var — not yet set
- After any OpenAPI spec change: run `pnpm --filter @workspace/api-spec run codegen` before touching dashboard pages

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
