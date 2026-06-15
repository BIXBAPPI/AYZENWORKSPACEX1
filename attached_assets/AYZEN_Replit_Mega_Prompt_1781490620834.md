# AYZEN — Replit Mega Prompt (Web, Design, Mobile UI, Desktop UI, Auth/Accounts, Domain, Bot)

> Copy-paste this entire prompt into Replit's AI Agent. It covers the full AYZEN platform: Telegram bot backend (FastAPI), web dashboard (Next.js), responsive design across desktop/tablet/mobile, login + account system, custom domain setup (AYZEN.tech), and bot execution/runtime.

---

## CONTEXT — What AYZEN Is

AYZEN is a crypto/community task-management platform operated **primarily through a Telegram bot**, with a **Next.js web dashboard** for admins and members. Stack:

- **Backend API**: FastAPI (Python 3.11) — `apps/api/` — runs the REST API + Telegram bot webhook + APScheduler background jobs
- **Frontend**: Next.js 14 (App Router) — `apps/web/` — admin dashboard, auth pages, Telegram Mini App (TMA) views
- **Database**: PostgreSQL (Supabase) via SQLAlchemy async + asyncpg
- **Cache/State**: Redis (Upstash) — bot conversation state, rate limiting, idempotency
- **Auth**: Supabase JWT (web dashboard) + Telegram-native auth (bot) + TMA HMAC verification (Mini App)
- **Monorepo**: pnpm workspaces — `lib/*`, `artifacts/*`, `scripts/`

Do NOT rewrite the architecture, rename folders, or introduce new frameworks. Work WITHIN the existing structure (`apps/api`, `apps/web`, `lib/`, `artifacts/`).

---

## PART 1 — ENVIRONMENT & DEPENDENCY SETUP

1. Confirm Replit modules are set: `nodejs-24`, `python-3.11` (already in `.replit`).
2. Run `pnpm install` at repo root (installs all workspace packages: `apps/web`, `lib/*`, `artifacts/*`, `scripts`).
3. Run `pip install -r apps/api/requirements.txt`.
4. Copy `.env.example` → `.env` and populate using Replit Secrets (never hardcode secrets in code):
   - `DATABASE_URL` — use Replit's built-in Postgres if available, else Supabase pooler URL (format: `postgresql+asyncpg://...`)
   - `REDIS_URL` — Upstash Redis URL (TLS)
   - `TELEGRAM_BOT_TOKEN`, `BOT_USERNAME` — from @BotFather
   - `INTERNAL_WEBHOOK_TOKEN`, `TELEGRAM_WEBHOOK_SECRET` — generate via `openssl rand -hex 32`
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
   - `SESSION_SECRET` — 32+ random chars for TMA JWT signing
   - `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `CF_WORKER_URL`, `CORS_ORIGINS` (set to `https://ayzen.tech,https://www.ayzen.tech`)
   - `ENVIRONMENT=production`, `STATELESS_MODE=false`
5. Verify the FastAPI app boots cleanly: `uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload` and check `curl http://localhost:8000/api/v1/health` returns `200`.
6. Verify Next.js dev server boots: `pnpm --filter <web-app-name> dev` (check `apps/web/package.json` for the exact workspace name) on its configured port.

---

## PART 2 — WEB DEVELOPMENT (Next.js Dashboard)

Working directory: `apps/web/`

1. **Audit existing routes** in `apps/web/app/`:
   - `app/auth/` — login/signup pages
   - `app/(dashboard)/` and `app/dashboard/` — main admin dashboard
   - `app/tma/` — Telegram Mini App views
   - `middleware.ts` — route protection logic
2. **Fix any broken routes or missing pages** without changing the App Router folder convention.
3. **Connect dashboard pages to the FastAPI REST API** (`apps/api/app/routers/`):
   - `auth.py` → login/session endpoints
   - `projects.py`, `tasks.py`, `members.py`, `progress.py`, `analytics.py`, `broadcasts.py`, `exports.py`, `settings.py`, `notifications.py`
   - Use `NEXT_PUBLIC_API_URL` for all client-side fetches; use server-side fetch with service-role credentials for SSR pages that need elevated access.
4. Ensure all forms have proper validation (Zod schemas from `lib/api-zod/` if present) and error states.
5. Implement loading states, empty states, and error boundaries for every data-driven page.

---

## PART 3 — DESIGN SYSTEM (Visual Identity)

1. Audit `apps/web/components/ui/` for the existing component library (likely shadcn/ui based, using Tailwind).
2. Establish/confirm a consistent design system:
   - **Color palette**: primary brand color reflecting "AYZEN" identity (crypto/productivity — suggest deep blue/teal + accent gold or green for "tasks completed" states)
   - **Typography**: one display font for headings, one readable sans-serif for body (load via `next/font`)
   - **Spacing scale**: Tailwind default scale (4px base) — keep consistent across all pages
   - **Component states**: every interactive element (buttons, inputs, cards) needs default/hover/active/disabled/focus states
3. Avoid generic "AI-template" look — add intentional touches: subtle gradients, custom icons (lucide-react is already a dependency), micro-interactions via `framer-motion` (already in catalog).
4. Dark mode: if Telegram Mini App requires it (Telegram clients can be dark/light), implement theme switching using Telegram's `theme_params` from the WebApp API for `app/tma/` routes, and a manual toggle for `app/dashboard/`.

---

## PART 4 — MOBILE UI (Responsive + Telegram Mini App)

1. **Telegram Mini App (`app/tma/`)**: This is the PRIMARY mobile experience.
   - Must work within Telegram's WebView (viewport constraints, no browser chrome)
   - Use Telegram WebApp JS SDK (`window.Telegram.WebApp`) for: `expand()`, `ready()`, `BackButton`, `MainButton`, haptic feedback, theme colors
   - Bottom-anchored primary actions (thumb-reachable zone)
   - Avoid hover-only interactions — everything must work with tap
   - Respect safe-area insets (`env(safe-area-inset-*)`) for notched devices
2. **Dashboard mobile responsiveness** (`app/(dashboard)/`, `app/dashboard/`):
   - Test at breakpoints: 375px (small phone), 414px (large phone), 768px (tablet portrait)
   - Convert multi-column layouts to single-column stacks below `md:` breakpoint
   - Replace desktop data tables with mobile card layouts on small screens
   - Ensure tap targets are minimum 44x44px
3. Test using Replit's webview device toolbar or Chrome DevTools device emulation.

---

## PART 5 — DESKTOP UI

1. Dashboard layouts (`app/(dashboard)/`, `app/dashboard/`) should use the full viewport width on screens ≥1280px:
   - Sidebar navigation (collapsible) + main content area + optional right-rail for context/notifications
   - Data tables with sortable columns for projects/tasks/members/analytics
2. Keyboard navigation: all interactive elements reachable via Tab, with visible focus rings (don't remove `:focus-visible` styles)
3. Multi-pane views for power users (e.g., task list + task detail side-by-side on wide screens, single-pane with navigation on narrow screens)

---

## PART 6 — LOGIN & ACCOUNT SYSTEM

1. **Web dashboard auth** (`apps/web/app/auth/`, `apps/api/app/routers/auth.py`, `apps/api/app/middleware/auth.py`):
   - Supabase Auth for email/password + OAuth providers (configure providers in Supabase dashboard if needed)
   - `verify_token()` / `require_admin()` in `apps/api/app/middleware/auth.py` validate Supabase JWTs via `SUPABASE_JWT_SECRET` — ensure this is set correctly
   - Session handling: HttpOnly cookies (per `replit.md`/README architecture notes) — do not store JWTs in localStorage
   - Implement: login page, signup page (if applicable), password reset flow, logout, session expiry handling/redirect to login
2. **Telegram-native auth** (bot users):
   - Users are identified by `telegram_user_id` — `apps/api/app/services/bot_user_service.py`
   - `/start` command links a Telegram account to the platform — verify `apps/api/app/services/deeplink_service.py` and `onboarding_service.py` are wired into `start_handler` for invite-link based account linking
3. **Telegram Mini App auth** (`apps/api/app/routers/tma_auth.py`):
   - Verifies Telegram WebApp `initData` via HMAC-SHA256 using `TELEGRAM_BOT_TOKEN`
   - Issues a session JWT signed with `SESSION_SECRET` for subsequent API calls from the Mini App
4. **Account/profile management**:
   - `apps/api/app/services/user_settings_service.py` + `apps/api/app/integrations/telegram/handlers/settings.py` (bot) and corresponding dashboard settings page (web)
   - Ensure both surfaces (bot `/settings` and web dashboard settings page) read/write the same underlying user settings table — no duplicated logic
5. **Roles & permissions**: confirm `require_admin()` correctly gates admin-only routes/pages, and that the bot's admin commands (`admin:*` callback prefix, `apps/api/app/integrations/telegram/middleware/role.py`) use the same role definitions as the web dashboard.

---

## PART 7 — DOMAIN SETUP (AYZEN.tech)

1. **Replit deployment**: Use Replit's "Deployments" feature (autoscale, per `.replit`'s `deploymentTarget = "autoscale"`) to deploy:
   - The FastAPI app (`apps/api/main.py`) — bind to `0.0.0.0:8000`
   - The Next.js app (`apps/web/`) — bind to its configured port
2. **Custom domain binding**:
   - In Replit Deployments settings, add custom domain `ayzen.tech` (and `www.ayzen.tech`)
   - Replit will provide DNS records (typically a `CNAME` for `www` and an `A`/`ALIAS` record for the apex domain) — add these at your domain registrar's DNS settings
   - Wait for SSL certificate provisioning (automatic via Replit/Let's Encrypt)
3. **Routing strategy** — decide and implement ONE of:
   - **Option A (recommended)**: `ayzen.tech` → Next.js frontend; `api.ayzen.tech` (subdomain) → FastAPI backend. Set `NEXT_PUBLIC_API_URL=https://api.ayzen.tech`
   - **Option B**: Single deployment with reverse-proxy/rewrites in `next.config.js` routing `/api/*` to the FastAPI service
4. Update `CORS_ORIGINS` env var on the FastAPI side to include `https://ayzen.tech` and `https://www.ayzen.tech` (and `https://api.ayzen.tech` if using subdomain split) — `apps/api/main.py` reads this for `CORSMiddleware`.
5. **Cloudflare Worker** (`apps/workers/cloudflare/`): if used as the Telegram webhook proxy, update `CF_WORKER_URL` to point at the production domain and set `TELEGRAM_WEBHOOK_SECRET` to match `apps/api/app/integrations/telegram/webhook.py`'s expected secret header.
6. **Telegram webhook registration**: after domain is live, call Telegram's `setWebhook` API pointing to `https://api.ayzen.tech/api/v1/bot/webhook` (or via the Cloudflare Worker URL), including the `secret_token` matching `TELEGRAM_WEBHOOK_SECRET`.

---

## PART 8 — BOT EXECUTION (Telegram Bot Runtime)

1. **Startup verification** — `apps/api/main.py`'s `lifespan()` must:
   - Connect to Postgres (`DATABASE_URL`) and Redis (`REDIS_URL`) — Redis failure should degrade to "stateless mode" gracefully (logged, not fatal)
   - Start APScheduler with all 5 jobs registered: `deadline_reminder`, `daily_digest`, `analytics_job`, `quiet_queue_job`, `stale_user_job` (`apps/api/app/jobs/`)
   - Initialize `TelegramClient` (`apps/api/app/integrations/telegram/client.py`) using `TELEGRAM_BOT_TOKEN`
2. **Webhook endpoint** — `POST /api/v1/bot/webhook` (`apps/api/app/integrations/telegram/webhook.py`):
   - Validates `X-Telegram-Bot-Api-Secret-Token` header against `TELEGRAM_WEBHOOK_SECRET`
   - Lazily builds `BotRouter` via `get_bot_router(app)` on first call, caches on `app.state.bot_router`
   - Dispatches updates to command/callback/state handlers in `apps/api/app/integrations/telegram/handlers/` and `wizards/`
3. **Verify all core commands work end-to-end** (test via real Telegram client against the deployed webhook, or local polling mode for dev):
   - `/start`, `/help`, `/profile`, `/status`, `/settings`
   - Menu-driven flows: Projects, Tasks, Progress, Leaderboard, Wallet/Points, Achievements, Referral, Search, Admin panel (members, broadcast, exports, project settings, owner transfer, analytics)
4. **Background jobs** — confirm APScheduler cron jobs run on schedule (check logs for `daily_digest` at 08:00 UTC, `stale_user_job` at 03:00 UTC, etc.) and that they correctly use `session_factory`/`redis_client` from `apps.api.main`.
5. **Error handling/observability**: `apps/api/app/services/bot_audit_service.py` logs dispatch errors to a DB audit table — confirm this table exists (check `apps/api/migrations/`) and errors are queryable for debugging in production.
6. **Rate limiting & idempotency** (`apps/api/app/integrations/telegram/middleware/rate_limit.py`, `idempotency.py`) — confirm these use Redis correctly and degrade gracefully if Redis is unavailable.

---

## EXECUTION PRIORITY ORDER

1. Environment setup (Part 1) — nothing else works without this
2. Bot execution core (Part 8, items 1-2) — verify webhook + dispatch work
3. Login/account system (Part 6) — auth must work before dashboard features are testable
4. Web development core routes (Part 2)
5. Design system (Part 3) — apply consistently as pages are built/fixed
6. Desktop UI (Part 5) then Mobile UI / TMA (Part 4) — desktop-first, then adapt down
7. Domain setup (Part 7) — last, once the app is feature-stable and ready for production traffic
8. Full bot command verification (Part 8, items 3-6)

## CONSTRAINTS (apply throughout)

- Do NOT rewrite existing architecture, rename folders/files, or introduce new frameworks/state-management libraries
- Preserve all existing handler/router/service naming conventions
- All secrets via Replit Secrets — never commit `.env` or hardcode tokens
- Prefer fixing/wiring existing code over generating new abstractions
- Test incrementally — verify each part boots/works before moving to the next
