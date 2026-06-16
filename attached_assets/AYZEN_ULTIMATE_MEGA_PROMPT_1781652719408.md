# 🚀 AYZEN WORKSPACE — ULTIMATE REPLIT AGENT MEGA PROMPT (V3 FINAL)

---

> **PASTE THIS ENTIRE DOCUMENT INTO REPLIT AGENT. DO NOT SKIP ANY SECTION.**
> This is an end-to-end specification for a Web3 airdrop task management platform called **AYZEN WORKSPACE**.
> The agent must read, understand, and implement every section below — front-to-back — before writing a single line of code.

---

## 🧠 WHAT YOU ARE BUILDING

**AYZEN WORKSPACE** is a Web3 community task management platform where:
- An **ADMIN** manages projects, tasks, members, and XP/tier rewards
- **MEMBERS** complete tasks, earn XP, climb leaderboards, and track analytics
- Everything is themed around **Web3 airdrops, crypto quests, and gamified productivity**

**Admin credentials (pre-seed into DB):**
- Email: `bibappix420@gmail.com`
- Password: `12345678@Ba1`
- Role: `admin`

---

## 🔴 REPLIT DEPLOYMENT RULES — NON-NEGOTIABLE

1. **ONE PORT ONLY: `8080`** — Replit exposes only port 8080 to the public. Everything routes through it.
2. **Node.js Express on port 8080** acts as the main server AND reverse proxy to Python FastAPI on internal port 8000.
3. **`GET /api` MUST return HTTP 200 JSON within 5 seconds** of startup. This is the Replit healthcheck. No DB calls here.
4. **Never bind Python to `0.0.0.0`** — bind to `127.0.0.1:8000` only (internal, never publicly exposed).
5. **No `pm2`, `nodemon`, `forever`** in production. Single `node` process only.
6. **Startup order:** Node binds to 8080 FIRST → THEN spawns Python as a child process.
7. **`.replit` must have exactly ONE `[[ports]]` block** with `localPort = 8080, externalPort = 80`.
8. **Python environment:** use `.venv/` virtual environment. PYTHONPATH must include project root.
9. **Build script** at `scripts/build.sh` must: install Python deps → install Node deps → build React → bundle API server.
10. **All environment variables** go in Replit Secrets (never hardcoded). Use `process.env.*` in Node, `os.environ.get()` in Python.

---

## 📁 COMPLETE PROJECT STRUCTURE

```
AYZENWORKSPACE/
├── .replit                          ← Replit config (see exact content below)
├── replit.nix                       ← Nix environment
├── package.json                     ← pnpm workspace root
├── pnpm-workspace.yaml
├── tsconfig.base.json
├── scripts/
│   ├── build.sh                     ← Full build script
│   └── post-merge.sh
├── apps/
│   └── api/                         ← Python FastAPI (internal :8000)
│       ├── main.py                  ← FastAPI app factory
│       ├── requirements.txt
│       └── app/
│           ├── database.py          ← SQLAlchemy async engine
│           ├── models.py            ← All DB models
│           ├── schemas.py           ← Pydantic schemas
│           ├── seed.py              ← Admin user seeder
│           └── routers/
│               ├── auth.py
│               ├── projects.py
│               ├── tasks.py
│               ├── members.py
│               ├── analytics.py
│               ├── settings.py
│               └── health.py        ← Telemetry/health endpoint
├── artifacts/
│   ├── api-server/                  ← Node.js Express proxy (:8080)
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   │       └── index.ts
│   └── dashboard/                   ← React + Vite frontend
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.json
│       └── src/
│           ├── main.tsx
│           ├── App.tsx
│           ├── lib/
│           │   ├── auth.tsx         ← AuthProvider + AuthGuard + useAuth
│           │   ├── api.ts           ← Axios instance + interceptors
│           │   └── utils.ts
│           ├── components/
│           │   ├── layout.tsx       ← Sidebar + topbar shell
│           │   ├── ui/              ← shadcn/ui components
│           │   └── home/            ← Landing page components
│           └── pages/
│               ├── Home.tsx         ← PUBLIC landing page (Web3 animated hero)
│               ├── Login.tsx
│               ├── Register.tsx
│               ├── Dashboard.tsx
│               ├── Projects.tsx
│               ├── ProjectDetail.tsx
│               ├── Tasks.tsx
│               ├── Analysis.tsx
│               ├── Members.tsx
│               ├── Settings.tsx
│               ├── Developer.tsx    ← Admin-only developer options + .env config
│               └── Health.tsx       ← Admin-only telemetry/health page
└── lib/
    └── api-client-react/            ← Generated React Query hooks
```

---

## ⚙️ EXACT `.replit` FILE

```toml
modules = ["nodejs-20", "python-3.12", "web", "postgresql-16"]

[nix]
channel = "stable-25_05"
packages = ["cargo", "libiconv", "libxcrypt", "postgresql", "rustc"]

[deployment]
deploymentTarget = "vm"
build = ["bash", "-c", "bash scripts/build.sh"]
run = ["bash", "-c", "PYTHONPATH=/home/runner/workspace .venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000 & PORT=8080 NODE_ENV=production node --enable-source-maps artifacts/api-server/dist/index.mjs"]

[[ports]]
localPort = 8080
externalPort = 80

[workflows]
runButton = "Project"

[[workflows.workflow]]
name = "Project"
mode = "parallel"
author = "agent"

[[workflows.workflow.tasks]]
task = "workflow.run"
args = "AYZEN Dashboard"

[[workflows.workflow.tasks]]
task = "workflow.run"
args = "Node API Server"

[[workflows.workflow]]
name = "AYZEN Dashboard"
author = "agent"

[workflows.workflow.metadata]
outputType = "webview"

[[workflows.workflow.tasks]]
task = "shell.exec"
args = "PORT=5000 BASE_PATH=/ pnpm --filter @workspace/dashboard run dev"
waitForPort = 5000

[[workflows.workflow]]
name = "Node API Server"
author = "agent"

[[workflows.workflow.tasks]]
task = "shell.exec"
args = "PORT=8080 NODE_ENV=development node --enable-source-maps /home/runner/workspace/artifacts/api-server/dist/index.mjs"
waitForPort = 8080

[workflows.workflow.metadata]
outputType = "console"

[agent]
stack = "BEST_EFFORT_FALLBACK"
expertMode = true
```

---

## 🗄️ DATABASE SCHEMA (PostgreSQL + SQLAlchemy)

Create all tables in `apps/api/app/models.py`:

```python
# users table
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum("admin", "member", name="user_role"), default="member")
    xp = Column(Integer, default=0)
    tier = Column(String, default="Bronze")
    streak = Column(Integer, default=0)
    last_active = Column(DateTime, default=func.now())
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)

# projects table
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)       # e.g. "DeFi", "NFT", "L2", "GameFi"
    xp_reward_name = Column(String, nullable=False) # e.g. "AYZEN Points", "XP", "Stars"
    tier = Column(String, nullable=False)           # "Bronze", "Silver", "Gold", "Platinum"
    description = Column(Text, nullable=True)
    status = Column(String, default="active")       # "active", "completed", "archived"
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())

# tasks table
class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    xp_reward = Column(Integer, default=10)
    priority = Column(Enum("low", "medium", "high", "critical", name="task_priority"), default="medium")
    status = Column(Enum("pending", "in_progress", "completed", "overdue", name="task_status"), default="pending")
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)

# member_tasks (many-to-many: which member completed which task)
class MemberTask(Base):
    __tablename__ = "member_tasks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"))
    status = Column(String, default="pending")     # "pending", "completed"
    completed_at = Column(DateTime, nullable=True)
    xp_earned = Column(Integer, default=0)

# daily_activity (for streak and calendar heatmap)
class DailyActivity(Base):
    __tablename__ = "daily_activity"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, nullable=False)
    tasks_completed = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)
```

---

## 🌱 DATABASE SEED (`apps/api/app/seed.py`)

On startup, run this to ensure admin user exists:

```python
async def seed_admin(db: AsyncSession):
    existing = await db.execute(select(User).where(User.email == "bibappix420@gmail.com"))
    if not existing.scalar_one_or_none():
        admin = User(
            email="bibappix420@gmail.com",
            username="AyzenAdmin",
            password_hash=bcrypt.hashpw("12345678@Ba1".encode(), bcrypt.gensalt()).decode(),
            role="admin",
            xp=99999,
            tier="Platinum",
        )
        db.add(admin)
        await db.commit()
```

---

## 🐍 PYTHON FASTAPI ROUTES

### Auth (`/api/v1/auth/`)
- `POST /register` — create member account (role always = "member")
- `POST /login` — returns JWT in HttpOnly cookie (`ayzen-token`) + user object
- `POST /logout` — clears cookie
- `GET /me` — returns current user from JWT

### Projects (`/api/v1/projects/`) — ADMIN ONLY for POST/DELETE
- `GET /` — list all projects (members see all)
- `POST /` — **ADMIN ONLY** — create project with fields: `name`, `category`, `xp_reward_name`, `tier`, `description`
- `GET /{id}` — project detail with task count, completion %
- `DELETE /{id}` — **ADMIN ONLY**
- `GET /{id}/tasks` — tasks for this project

### Tasks (`/api/v1/tasks/`) — ADMIN ONLY for POST/DELETE
- `GET /` — list all tasks (filter by status, priority, project, assigned_to)
- `POST /` — **ADMIN ONLY** — create task: `project_id`, `title`, `description`, `xp_reward`, `priority`, `due_date`, `assigned_to`
- `GET /my` — tasks assigned to current logged-in member
- `PATCH /{id}/status` — member can update their own task status
- `DELETE /{id}` — **ADMIN ONLY**

### Members (`/api/v1/members/`)
- `GET /` — list all members with XP, tier, streak, completed task count
- `GET /leaderboard` — sorted by XP descending, with rank position
- `GET /{id}` — member profile
- `PATCH /{id}/role` — **ADMIN ONLY** — promote/demote member
- `DELETE /{id}` — **ADMIN ONLY**

### Analytics (`/api/v1/analytics/`)
- `GET /me` — current user's analytics: ROI (XP earned vs possible), task progress %, project progress %, streak, last_month_activity, this_month_activity
- `GET /overview` — admin dashboard: total tasks, completed tasks, overdue tasks, active members, daily completion chart (30 days)
- `GET /leaderboard` — top 10 members by XP with rank change (compare to last week)

### Settings (`/api/v1/settings/`)
- `GET /` — get user's settings (notification prefs, quiet hours, language)
- `PATCH /` — update settings
- `GET /env` — **ADMIN ONLY** — list all environment variable keys (NOT values) for UI display
- `PATCH /env` — **ADMIN ONLY** — update env var value via Replit Secrets API (or just validate and return instructions)

### Health (`/api/v1/health/`)
- `GET /` — **ADMIN ONLY** — full telemetry: server uptime, DB connection status, Python version, Node version, port assignments, all registered routes with method/path/handler name, memory usage, CPU usage, active connections, FastAPI startup time, last 10 API calls log

---

## ⚡ NODE.JS API SERVER (`artifacts/api-server/src/index.ts`)

```typescript
import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import cookieParser from 'cookie-parser';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = parseInt(process.env.PORT || '8080', 10);
const PYTHON_PORT = 8000;

const app = express();

// ── HEALTHCHECK (must be FIRST, no middleware, immediate 200) ──────────────
app.get('/api', (req, res) => {
  res.status(200).json({ status: 'ok', service: 'ayzen-workspace', ts: Date.now() });
});

app.use(cookieParser());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// ── CORS ──────────────────────────────────────────────────────────────────
app.use((req, res, next) => {
  const origin = req.headers.origin || '';
  res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PATCH,PUT,DELETE,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

// ── PROXY to Python FastAPI ───────────────────────────────────────────────
app.use(
  createProxyMiddleware({
    pathFilter: '/api/v1',
    target: `http://127.0.0.1:${PYTHON_PORT}`,
    changeOrigin: true,
    on: {
      error: (err, req, res: any) => {
        console.error('[Proxy Error]', err.message);
        res.status(502).json({ error: 'Python API unavailable', detail: err.message });
      },
    },
  })
);

// ── SERVE REACT DASHBOARD ─────────────────────────────────────────────────
const dashboardDist = path.resolve(__dirname, '../../../artifacts/dashboard/dist');
app.use(express.static(dashboardDist));

app.get('*', (req, res) => {
  if (req.path.startsWith('/api')) {
    return res.status(404).json({ error: 'Not found' });
  }
  res.sendFile(path.join(dashboardDist, 'index.html'));
});

// ── SPAWN PYTHON ──────────────────────────────────────────────────────────
function startPython() {
  const py = spawn(
    '/home/runner/workspace/.venv/bin/python',
    ['-m', 'uvicorn', 'apps.api.main:app', '--host', '127.0.0.1', '--port', String(PYTHON_PORT)],
    {
      cwd: '/home/runner/workspace',
      stdio: 'inherit',
      env: { ...process.env, PYTHONPATH: '/home/runner/workspace' },
    }
  );
  py.on('close', (code) => {
    console.warn(`[Python] exited ${code}. Restarting in 3s...`);
    setTimeout(startPython, 3000);
  });
}

app.listen(PORT, '0.0.0.0', () => {
  console.log(`✅ AYZEN running on :${PORT}`);
  console.log(`⚙️  Spawning Python on :${PYTHON_PORT}...`);
  startPython();
});
```

---

## 🎨 REACT FRONTEND — ALL PAGES SPECIFICATION

### ROUTING (`App.tsx`)
```
/ → <Home /> (PUBLIC — no auth required)
/login → <Login />
/register → <Register />
/dashboard → <Dashboard /> (protected)
/projects → <Projects /> (protected)
/projects/:id → <ProjectDetail /> (protected)
/tasks → <Tasks /> (protected)
/analysis → <Analysis /> (protected)
/members → <Members /> (protected)
/settings → <Settings /> (protected)
/developer → <Developer /> (admin-only)
/health → <Health /> (admin-only)
```

The `<AuthGuard>` component checks JWT cookie. If not authenticated, redirect to `/login`. Admin-only pages additionally check `user.role === 'admin'`.

---

### PAGE 1: HOME (PUBLIC LANDING PAGE) `/`

This is the **most visually impressive page** — it must look like a premium Web3 product.

**Hero Section:**
- Animated starfield or particle background (use CSS canvas or tsParticles)
- Large headline: `"AYZEN WORKSPACE"` with glowing gradient text (purple → cyan)
- Subheadline: `"Web3 Airdrop Task Management — Earn XP. Complete Quests. Dominate the Leaderboard."`
- Two CTA buttons: `[Get Started →]` (→ `/register`) and `[Login]` (→ `/login`)

**Animated Slides / Features Carousel (auto-playing, 4 slides):**

*Slide 1 — "Airdrop Quests"*
- Icon: 🪂 or rocket SVG
- Title: `"Complete Web3 Airdrop Tasks"`
- Body: `"Participate in curated airdrop campaigns. Complete quests, earn XP, and maximize your crypto rewards."`
- Visual: animated checklist items appearing one by one

*Slide 2 — "XP & Tier System"*
- Icon: 🏆
- Title: `"Climb the Tier Ladder"`
- Body: `"Earn XP for every completed task. Rise from Bronze → Silver → Gold → Platinum and unlock exclusive rewards."`
- Visual: animated tier progress bar filling up

*Slide 3 — "Leaderboard"*
- Icon: 📊
- Title: `"Compete on the Leaderboard"`
- Body: `"Real-time rankings. See where you stand among all members. Weekly streaks reward consistency."`
- Visual: animated leaderboard rows sliding in

*Slide 4 — "Analytics"*
- Icon: 📈
- Title: `"Track Your ROI"`
- Body: `"Deep analytics on your task progress, project completion rate, monthly activity heatmap, and XP ROI."`
- Visual: animated chart lines drawing themselves

**Slide navigation:** dots at bottom, auto-advance every 4 seconds, pause on hover, swipe support on mobile.

**Stats Bar (between hero and slides):**
- `🔥 500+ Active Members` | `✅ 10,000+ Tasks Completed` | `🪂 50+ Airdrop Projects` | `⭐ $2M+ XP Distributed`
- Numbers animate (count-up) when scrolled into view

**Footer:** `© 2025 AYZEN WORKSPACE — Web3 Community Platform`

---

### PAGE 2: LOGIN `/login`
- Card centered on dark background
- AYZEN logo/wordmark at top
- Fields: Email, Password (show/hide toggle)
- `[Login]` button → POST /api/v1/auth/login
- Link: `"Don't have an account? Register"`
- On success: redirect to `/dashboard`
- Error states: "Invalid credentials", "Account not found"

---

### PAGE 3: REGISTER `/register`
- Card layout
- Fields: Username, Email, Password, Confirm Password
- Role is always `"member"` — no role selector shown
- `[Create Account]` button → POST /api/v1/auth/register
- Link: `"Already have an account? Login"`
- On success: auto-login and redirect to `/dashboard`

---

### PAGE 4: DASHBOARD `/dashboard`

This is the **command center** — shows everything at a glance.

**Layout:** 2-column grid on desktop, stacked on mobile

**Top Row — KPI Cards (4 cards):**
1. `Total Tasks` — number of all tasks assigned to you (or all tasks if admin)
2. `Completed` — completed task count + green progress ring
3. `Overdue` — overdue count in red
4. `Your XP` — your total XP with tier badge (Bronze/Silver/Gold/Platinum)

**Second Row:**
- **Leaderboard Position Card** — "You are ranked #7 out of 42 members" with a small podium graphic showing top 3 names
- **Task Progress Card** — donut chart: pending / in_progress / completed / overdue breakdown
- **Project Progress Card** — horizontal bar chart: each active project with % completion

**Third Row:**
- **30-Day Activity Chart** — area chart showing tasks completed per day for last 30 days
- **Recent Completions** — last 5 completed tasks with timestamp and XP earned

**Admin Extra Section (only visible if `user.role === "admin"`):**
- Member count card
- Total projects card
- Quick links: `[+ Create Project]` → `/projects` | `[+ Create Task]` → `/tasks` | `[View Health]` → `/health`

---

### PAGE 5: PROJECTS `/projects`

**For ALL users:**
- Grid of project cards (2-3 columns)
- Each card shows: Project Name, Category badge, Tier badge (Bronze/Silver/Gold/Platinum), XP Reward Name, task count, completion %, status (active/completed/archived)
- Click card → navigates to `/projects/:id`
- Filter bar: by category, tier, status
- Search box

**Admin-only section at top (hidden from members):**
- `[+ Create Project]` button → opens a modal/drawer with form:
  - **Project Name** (text input, required)
  - **Category** (select: DeFi, NFT, L2, GameFi, Social, Bridge, DEX, Testnet, Other)
  - **XP Reward Name** (text input — e.g. "AYZEN Points", "Stars", "Credits")
  - **Tier** (select: Bronze, Silver, Gold, Platinum)
  - **Description** (textarea, optional)
  - `[Create Project]` button → POST /api/v1/projects/

---

### PAGE 6: PROJECT DETAIL `/projects/:id`

**Header:**
- Project name, category badge, tier badge, status badge
- Created date, creator username
- Completion % progress bar
- Total tasks / completed tasks count

**Task List (table or cards):**
- Columns: Title, Priority (color-coded), Status (dropdown editable by member for their tasks), Due Date, Assigned To, XP Reward
- Filter by: status, priority, assigned_to
- Sort by: due date, priority, status

**Admin-only controls:**
- `[+ Add Task to This Project]` button → modal with task creation form:
  - **Title** (required)
  - **Description** (textarea)
  - **XP Reward** (number input, default 10)
  - **Priority** (select: low, medium, high, critical)
  - **Due Date** (date picker)
  - **Assign To** (member select dropdown — search by username)
- Delete task button (trash icon) on each row

---

### PAGE 7: TASKS `/tasks`

**For Members — "MY TASKS" view:**
- Shows ONLY tasks assigned to the logged-in member (`GET /api/v1/tasks/my`)
- **Remaining Tasks counter** prominently displayed at top: `"You have X tasks remaining"`
- Task cards with: title, project name badge, priority badge, status badge, due date, XP reward
- Member can click status badge to change it (pending → in_progress → completed)
- Filter: by project, priority, status
- Overdue tasks highlighted in red with `⚠️ OVERDUE` badge

**For Admin — "ALL TASKS" view:**
- Full task list across all projects and all members
- Extra column: "Assigned To" showing member username
- Filter by: project, member, status, priority
- `[+ Create Task]` button at top → modal with full task creation form:
  - **Project** (select — required)
  - **Title** (required)
  - **Description**
  - **XP Reward** (number)
  - **Priority** (select)
  - **Due Date** (date picker)
  - **Assign To** (member select)
- Bulk status update option
- Delete button on each task

---

### PAGE 8: ANALYSIS `/analysis`

**Header:** `"Your Performance Analytics"` with date range selector (last 7d / 30d / 90d / all time)

**Row 1 — Key Metrics (4 cards):**
1. **ROI** — `"XP Earned / Total Possible XP = X%"` with circular progress gauge, colored green/yellow/red based on threshold
2. **Task Progress** — `"X of Y tasks completed (Z%)"` with donut chart
3. **Project Progress** — `"X of Y projects with tasks completed"` with horizontal progress bars per project
4. **Streak** — `"🔥 X day streak"` with a flame animation, shows current streak and best streak

**Row 2 — Activity Calendars:**
- **Last Month Activity** — calendar grid for previous month, each day colored by tasks completed (0 = gray, 1-2 = light green, 3-5 = green, 6+ = dark green) — like GitHub contribution graph
- **This Month Activity** — same format for current month, today's date highlighted with a circle

**Row 3 — Charts:**
- **XP Over Time** — line chart showing cumulative XP earned per day over selected period
- **Task Completion Rate** — bar chart showing tasks completed per week for last 8 weeks

**Row 4 — Per-Project Breakdown:**
- Table: Project Name | Tasks Assigned | Tasks Completed | Completion % | XP Earned | Status

---

### PAGE 9: MEMBERS `/members`

This is the **LEADERBOARD PAGE**.

**Leaderboard Table (top section):**
- Rank # | Avatar (initials circle if no avatar) | Username | Tier Badge | XP | Tasks Completed | Streak | Last Active
- Rank 1-3 have special styling: 🥇 gold, 🥈 silver, 🥉 bronze backgrounds
- Current logged-in user's row is highlighted in purple/blue
- Pagination: 20 per page
- Sort by: XP (default), Tasks Completed, Streak

**Search/Filter bar:**
- Search by username
- Filter by tier (Bronze/Silver/Gold/Platinum)

**Member Profile Modal (click any member row):**
- Avatar, username, tier badge, XP total
- Tasks completed, streak, last active
- Project participation count

**Admin-only controls on each member row:**
- Role badge is clickable → dropdown: "Promote to Admin" / "Demote to Member"
- Delete member button (with confirmation modal)
- `[+ Invite Member]` button at top (admin only) — opens a modal to pre-create a member account

---

### PAGE 10: SETTINGS `/settings`

**Sections:**

**Account:**
- Display: Username, Email, Role, Tier, XP
- `[Change Password]` form (current password + new password + confirm)

**Notification Preferences:**
- Toggle: Task Due Reminders (on/off)
- Toggle: Leaderboard Updates (on/off)
- Toggle: Project Announcements (on/off)
- Quiet Hours: Start time + End time (time pickers)

**Appearance:**
- Language selector (English / Bangla — for future i18n)
- Theme: Dark (default, only option for now — show as disabled toggle)

**Danger Zone (member):**
- `[Delete My Account]` — confirmation modal

---

### PAGE 11: DEVELOPER `/developer` — ADMIN ONLY

This page is ONLY accessible if `user.role === "admin"`. Non-admins are redirected to `/dashboard`.

**Section 1 — Environment Variables:**
- Display a table of all relevant environment variable KEYS with current values masked (show `***` for secrets, show actual value for non-sensitive ones like `NODE_ENV`, `PYTHON_ENV`, `BOT_USERNAME`, etc.)
- Variables shown: `DATABASE_URL`, `SESSION_SECRET`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `INTERNAL_WEBHOOK_TOKEN`, `CORS_ORIGINS`, `ALLOWED_HOSTS`, `STATELESS_MODE`, `BOT_USERNAME`, `DEFAULT_QUIET_START`, `DEFAULT_QUIET_END`, `REDIS_URL`, `NODE_ENV`, `PYTHON_ENV`, `UV_SYSTEM_PYTHON`, `UV_PROJECT_ENVIRONMENT`
- For each variable: a pencil icon to edit (opens inline edit field) with `[Save]`
- Note below table: `"Secrets are stored in Replit Secrets tab. Changes here update process.env for the current session only. For persistent changes, update Replit Secrets tab."`

**Section 2 — Virtual Environment (Python):**
- Show: Python version, pip version, .venv path, installed packages list (run `pip list` and display)
- `[Reinstall Dependencies]` button — runs `pip install -r requirements.txt` in subprocess and shows live output in a terminal-style black box

**Section 3 — Node.js Environment:**
- Show: Node version, npm/pnpm version, workspace packages list
- `[Rebuild Frontend]` button — runs build command and shows output

**Section 4 — Database:**
- Show: DATABASE_URL (masked), connection status (test on page load), table list with row counts
- `[Run Migrations]` button
- `[Seed Admin User]` button — re-runs the admin seed if missing

**Section 5 — Telegram Bot:**
- Show: BOT_USERNAME, TELEGRAM_BOT_TOKEN (masked), webhook URL configured
- `[Test Bot Connection]` button — sends a test request to Telegram API and shows response

---

### PAGE 12: HEALTH `/health` — ADMIN ONLY

This is the **A-to-Z Telemetry Page** — full system observability. Only accessible to admin.

**Section 1 — Server Status (live, refresh every 30 seconds):**
- Node.js API Server: Port 8080 — Status: ✅ Running
- Python FastAPI: Port 8000 (internal) — Status: ✅ Running
- PostgreSQL DB: Port 5432 (internal) — Status: ✅ Connected
- Last healthcheck timestamp

**Section 2 — System Info:**
- Server uptime (days, hours, minutes, seconds — live counter)
- Node.js version, platform, arch
- Python version
- Memory usage: used / total (MB) with progress bar
- CPU usage %
- Disk usage

**Section 3 — Registered Routes (A-to-Z Function Map):**
A full table of EVERY API route with:
- Method (GET/POST/PATCH/DELETE) — color coded (GET=blue, POST=green, PATCH=yellow, DELETE=red)
- Path (e.g. `/api/v1/auth/login`)
- Handler function name (e.g. `login_user`)
- Auth required? (Yes/No)
- Admin only? (Yes/No)
- Average response time (ms) — tracked in middleware

**Section 4 — Recent API Calls Log (last 50):**
- Table: Timestamp | Method | Path | Status Code | Response Time (ms) | User (email or "anonymous")
- Color: 2xx = green, 4xx = yellow, 5xx = red
- Auto-refresh toggle

**Section 5 — Database Stats:**
- Active connections
- Table row counts for all tables (users, projects, tasks, member_tasks, daily_activity)
- Query execution time for a test `SELECT 1`

**Section 6 — Python FastAPI Introspection:**
- All FastAPI routes pulled from `GET /api/v1/openapi.json` and displayed
- Startup time in ms
- Active async workers count

---

## 🎨 DESIGN SYSTEM

**Color Palette:**
```css
--bg-primary: #0a0a0f;       /* near-black background */
--bg-secondary: #12121a;      /* card backgrounds */
--bg-tertiary: #1a1a28;       /* input/table row backgrounds */
--border: #2a2a3f;            /* subtle borders */
--accent-purple: #7c3aed;     /* primary accent */
--accent-cyan: #06b6d4;       /* secondary accent */
--accent-gradient: linear-gradient(135deg, #7c3aed, #06b6d4);
--text-primary: #f1f5f9;      /* main text */
--text-secondary: #94a3b8;    /* muted text */
--success: #22c55e;
--warning: #f59e0b;
--danger: #ef4444;
--tier-bronze: #cd7f32;
--tier-silver: #c0c0c0;
--tier-gold: #ffd700;
--tier-platinum: #e5e4e2;
```

**Tier Badge Colors:**
- Bronze: `bg-amber-800 text-amber-200`
- Silver: `bg-gray-500 text-gray-100`
- Gold: `bg-yellow-500 text-yellow-900`
- Platinum: `bg-slate-300 text-slate-900`

**Priority Badge Colors:**
- Low: gray
- Medium: blue
- High: orange
- Critical: red (pulsing animation)

**Typography:** Use `Inter` font from Google Fonts

**Sidebar Navigation (authenticated pages):**
```
AYZEN WORKSPACE (logo)
────────────────
📊 Dashboard
📁 Projects
✅ Tasks
📈 Analysis
👥 Members
────────────────
⚙️ Settings
[Admin only:]
🛠️ Developer
💚 Health
────────────────
👤 [User avatar + username]
[Logout]
```

Sidebar is collapsible on mobile (hamburger menu).

---

## 🔐 AUTH IMPLEMENTATION

**JWT Configuration:**
- Secret: `process.env.SESSION_SECRET`
- Algorithm: HS256
- Expiry: 7 days
- Storage: HttpOnly cookie named `ayzen-token`
- Cookie flags: `samesite=none; secure=true; httponly=true; path=/`

**Python JWT middleware (`apps/api/app/middleware/auth.py`):**
```python
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("ayzen-token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        user = await db.get(User, int(user_id))
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

---

## 📦 REQUIRED ENVIRONMENT VARIABLES (Replit Secrets)

Set ALL of these in Replit → Secrets tab before running:

| Key | Example Value | Notes |
|-----|---------------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@localhost/ayzen` | PostgreSQL async |
| `SESSION_SECRET` | `your-random-64-char-string` | JWT signing key |
| `TELEGRAM_BOT_TOKEN` | `123456:ABC-DEF...` | Optional, for bot |
| `TELEGRAM_WEBHOOK_SECRET` | `random-secret` | Webhook validation |
| `INTERNAL_WEBHOOK_TOKEN` | `random-hex` | Internal API calls |
| `CORS_ORIGINS` | `https://${REPLIT_DEV_DOMAIN}` | Frontend origins |
| `NODE_ENV` | `production` | |
| `PYTHON_ENV` | `production` | |

---

## 🛠️ BUILD SCRIPT (`scripts/build.sh`)

```bash
#!/bin/bash
set -e

echo "📦 Installing Python dependencies..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r apps/api/requirements.txt

echo "📦 Installing Node.js dependencies..."
npm install -g pnpm
pnpm install

echo "🏗️ Building React dashboard..."
pnpm --filter @workspace/dashboard run build

echo "🏗️ Building Node.js API server..."
pnpm --filter @workspace/api-server run build

echo "✅ Build complete!"
```

---

## 🐛 COMMON ERRORS — FIX THESE PROACTIVELY

| Error | Cause | Fix |
|-------|-------|-----|
| `healthcheck /api returned 500` | Route has DB call or crashes | Make `/api` return `{status:"ok"}` immediately, no async, no DB |
| `port 8080 never opened` | Node crashed before `.listen()` | Wrap startup in try-catch, bind 8080 FIRST, spawn Python AFTER |
| `502 Bad Gateway on /api/v1/*` | Python not started yet | Add retry logic in proxy error handler; Python needs ~3-5s to start |
| `PYTHONPATH error on import` | Python can't find modules | Set `PYTHONPATH=/home/runner/workspace` in Python spawn env |
| `JWT cookie not sent` | Cookie flags wrong for Replit preview | Use `samesite=none; secure=true` |
| `React Router 404 on refresh` | SPA fallback missing | Catch-all route in Express serving `index.html` |
| `asyncpg can't connect` | Wrong DATABASE_URL format | Must be `postgresql+asyncpg://...` not `postgresql://...` |
| `pnpm workspace not found` | Missing pnpm-workspace.yaml | Create it with `packages: ['artifacts/*', 'lib/*']` |

---

## ✅ FINAL DEPLOYMENT CHECKLIST

Before clicking Deploy, verify:

- [ ] `.replit` has exactly ONE `[[ports]]` block: `localPort=8080, externalPort=80`
- [ ] `GET /api` returns HTTP 200 with `{"status":"ok"}` — no middleware before this route
- [ ] Python FastAPI binds to `127.0.0.1:8000` (NOT `0.0.0.0`)
- [ ] Admin user `bibappix420@gmail.com` / `12345678@Ba1` is seeded in DB
- [ ] Home page (`/`) is publicly accessible without login
- [ ] Login page properly sets `ayzen-token` HttpOnly cookie
- [ ] Admin can see Developer and Health pages; members cannot
- [ ] Admin can create projects on `/projects` page; members see create button hidden
- [ ] Admin can create tasks on `/tasks` page; members only see their own tasks
- [ ] Dashboard shows leaderboard position, task progress, project progress
- [ ] Analysis page shows ROI, streak, last/this month activity calendars
- [ ] Members page is leaderboard (sorted by XP)
- [ ] Health page shows all routes, ports, server status
- [ ] Developer page shows all env vars (masked) and .venv status
- [ ] `scripts/build.sh` runs without errors
- [ ] No hardcoded secrets anywhere in code

---

## 🎯 IMPLEMENTATION ORDER

Build in this exact order to avoid dependency issues:

1. **Database & Models** — create all SQLAlchemy models, run migrations
2. **Seed Admin** — verify `bibappix420@gmail.com` can log in
3. **Auth API** — `/api/v1/auth/login`, `/register`, `/me`, `/logout`
4. **Node.js proxy** — verify `/api/v1/auth/me` works end-to-end
5. **Projects API** — CRUD with admin guards
6. **Tasks API** — CRUD with admin guards + `/my` endpoint for members
7. **Members API** — list, leaderboard, role management
8. **Analytics API** — me analytics, overview
9. **Health API** — telemetry endpoint
10. **Settings API** — env vars + user prefs
11. **React: Auth pages** — Login, Register (test full auth flow)
12. **React: Layout shell** — Sidebar with role-based nav items
13. **React: Home page** — animated hero + 4 feature slides + stats bar
14. **React: Dashboard** — KPI cards + charts + leaderboard position
15. **React: Projects** — admin create modal + project grid
16. **React: Project Detail** — task list + admin create task modal
17. **React: Tasks** — member "my tasks" view + admin "all tasks" view
18. **React: Analysis** — ROI + streak + activity calendars + charts
19. **React: Members** — leaderboard table + admin controls
20. **React: Settings** — account + notifications + danger zone
21. **React: Developer** — env vars + venv status + rebuild buttons
22. **React: Health** — full telemetry dashboard

---

*AYZEN WORKSPACE — Ultimate Replit Mega Prompt V3*
*Generated: 2026-06-17 | Admin: bibappix420@gmail.com | Stack: Node 20 + Python 3.12 + React + PostgreSQL*
