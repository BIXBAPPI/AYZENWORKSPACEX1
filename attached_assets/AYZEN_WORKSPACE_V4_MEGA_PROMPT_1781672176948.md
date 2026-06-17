# 🚀 AYZEN WORKSPACE — ULTIMATE REPLIT AGENT MEGA PROMPT (V4 FINAL)

---

> **PASTE THIS ENTIRE DOCUMENT INTO REPLIT AGENT. DO NOT SKIP ANY SECTION.**
> This is the complete end-to-end specification for **AYZEN WORKSPACE** V4.
> Read every section fully before writing a single line of code.
> This is a FULL REBUILD from V3 with major new features added.

---

## 🧠 WHAT YOU ARE BUILDING

**AYZEN WORKSPACE** is a Web3 community task management platform where:
- An **ADMIN** manages projects, tasks, members, referrals, activations, and XP/tier rewards
- **MEMBERS** complete tasks, earn XP, climb leaderboards, track analytics, manage wallets
- Everything is themed around **Web3 airdrops, crypto quests, and gamified productivity**
- **Invite-only system**: New accounts require an admin-issued activation code OR a referral from an existing member (with admin approval)

**Admin credentials (pre-seed into DB):**
- Email: `bibappix420@gmail.com`
- Password: `12345678@Ba1`
- Role: `admin`

---

## 🔴 REPLIT DEPLOYMENT RULES — NON-NEGOTIABLE

1. **ONE PORT ONLY: `8080`** — Replit exposes only port 8080 to the public. Everything routes through it.
2. **Node.js Express on port 8080** acts as the main server AND reverse proxy to Python FastAPI on internal port 8000.
3. **`GET /api` MUST return HTTP 200 JSON within 5 seconds** of startup. No DB calls here.
4. **Never bind Python to `0.0.0.0`** — bind to `127.0.0.1:8000` only.
5. **No `pm2`, `nodemon`, `forever`** in production. Single `node` process only.
6. **Startup order:** Node binds to 8080 FIRST → THEN spawns Python as a child process.
7. **`.replit` must have exactly ONE `[[ports]]` block** with `localPort = 8080, externalPort = 80`.
8. **Python environment:** use `.venv/` virtual environment. PYTHONPATH must include project root.
9. **Build script** at `scripts/build.sh` must: install Python deps → install Node deps → build React → bundle API server.
10. **All environment variables** go in Replit Secrets. Use `process.env.*` in Node, `os.environ.get()` in Python.

---

## 📁 COMPLETE PROJECT STRUCTURE

```
AYZENWORKSPACE/
├── .replit
├── replit.nix
├── package.json
├── pnpm-workspace.yaml
├── tsconfig.base.json
├── scripts/
│   ├── build.sh
│   └── post-merge.sh
├── apps/
│   └── api/
│       ├── main.py
│       ├── requirements.txt
│       └── app/
│           ├── database.py
│           ├── models.py
│           ├── schemas.py
│           ├── seed.py
│           └── routers/
│               ├── auth.py
│               ├── projects.py
│               ├── tasks.py
│               ├── members.py
│               ├── analytics.py
│               ├── settings.py
│               ├── health.py
│               ├── referral.py        ← NEW: referral + activation system
│               ├── wallet.py          ← NEW: wallet + XP reward system
│               ├── gas_tracker.py     ← NEW: 20-25 mainnet gas tracker
│               ├── two_fa.py          ← NEW: 2FA TOTP + email code
│               └── ai_assistant.py   ← NEW: AI assistant endpoint
├── artifacts/
│   ├── api-server/
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   │       └── index.ts
│   └── dashboard/
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.json
│       └── src/
│           ├── main.tsx
│           ├── App.tsx
│           ├── lib/
│           │   ├── auth.tsx
│           │   ├── api.ts
│           │   └── utils.ts
│           ├── components/
│           │   ├── layout.tsx
│           │   ├── ui/
│           │   └── home/
│           └── pages/
│               ├── Home.tsx           ← PUBLIC landing page
│               ├── Login.tsx
│               ├── Register.tsx       ← activation code required
│               ├── Dashboard.tsx
│               ├── Projects.tsx
│               ├── ProjectDetail.tsx
│               ├── Tasks.tsx
│               ├── Analysis.tsx
│               ├── Members.tsx
│               ├── Settings.tsx
│               ├── Developer.tsx
│               ├── Health.tsx
│               ├── AccountVault.tsx   ← NEW: account vault with 2FA, email codes
│               ├── Profile.tsx        ← NEW: user profile with social/wallet details
│               ├── GasTracker.tsx     ← NEW: gas tracker dashboard
│               └── AIAssistant.tsx   ← NEW: AI assistant page
└── lib/
    └── api-client-react/
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

### CRITICAL FIX: Session Isolation
**Each user must have their OWN session stored independently in the DB. DO NOT share session state between users. The `sessions` table must store `user_id` with a unique constraint per active token. Login must create a NEW session row — not overwrite any existing one. Two users logging in simultaneously must each have separate rows.**

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
    # NEW fields
    referred_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    activation_code_used = Column(String, nullable=True)
    google_id = Column(String, unique=True, nullable=True)   # Google OAuth
    totp_secret = Column(String, nullable=True)              # 2FA TOTP secret
    two_fa_enabled = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    wallet_address = Column(String, nullable=True)           # primary wallet
    twitter_handle = Column(String, nullable=True)
    discord_handle = Column(String, nullable=True)
    telegram_handle = Column(String, nullable=True)
    github_handle = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    xp_transferable = Column(Integer, default=0)             # transferable XP balance

# sessions table — CRITICAL: one row per login, never shared
class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=False)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

# activation_codes table — admin issues these for new accounts
class ActivationCode(Base):
    __tablename__ = "activation_codes"
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)         # e.g. "AYZEN-XXXX-YYYY"
    created_by = Column(Integer, ForeignKey("users.id"))       # always admin
    used_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)               # optional expiry

# referral_requests table — when an existing member refers someone
class ReferralRequest(Base):
    __tablename__ = "referral_requests"
    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer, ForeignKey("users.id"))      # existing member who referred
    referred_email = Column(String, nullable=False)
    referred_username = Column(String, nullable=True)
    status = Column(String, default="pending")                 # "pending", "approved", "rejected"
    admin_note = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    # After approval, this referral generates an activation code
    activation_code_id = Column(Integer, ForeignKey("activation_codes.id"), nullable=True)

# projects table
class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    xp_reward_name = Column(String, nullable=False)
    tier = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="active")
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

# member_tasks
class MemberTask(Base):
    __tablename__ = "member_tasks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"))
    status = Column(String, default="pending")
    completed_at = Column(DateTime, nullable=True)
    xp_earned = Column(Integer, default=0)

# project_members — who is added to which project
class ProjectMember(Base):
    __tablename__ = "project_members"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    joined_at = Column(DateTime, default=func.now())
    eligibility = Column(String, default="not_set")   # "not_set", "eligible", "ineligible"

# daily_activity
class DailyActivity(Base):
    __tablename__ = "daily_activity"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, nullable=False)
    tasks_completed = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)

# account_vault — stores 2FA codes, wallet addresses per user
class AccountVault(Base):
    __tablename__ = "account_vault"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    # Wallet addresses
    evm_address = Column(String, nullable=True)
    solana_address = Column(String, nullable=True)
    cosmos_address = Column(String, nullable=True)
    sui_address = Column(String, nullable=True)
    aptos_address = Column(String, nullable=True)
    btc_address = Column(String, nullable=True)
    # Social accounts
    twitter = Column(String, nullable=True)
    discord = Column(String, nullable=True)
    telegram = Column(String, nullable=True)
    github = Column(String, nullable=True)
    # 2FA TOTP
    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Boolean, default=False)
    # Email verification code (temporary, stored as hash)
    email_code_hash = Column(String, nullable=True)
    email_code_expires = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# xp_transfers — internal XP transfer log
class XpTransfer(Base):
    __tablename__ = "xp_transfers"
    id = Column(Integer, primary_key=True)
    from_user_id = Column(Integer, ForeignKey("users.id"))
    to_user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer, nullable=False)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())

# error_log — telemetry error logging
class ErrorLog(Base):
    __tablename__ = "error_logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now())
    level = Column(String, default="error")          # "debug", "info", "warning", "error", "critical"
    function_name = Column(String, nullable=True)
    route = Column(String, nullable=True)
    error_type = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    request_data = Column(Text, nullable=True)

# api_call_log — for telemetry
class ApiCallLog(Base):
    __tablename__ = "api_call_logs"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now())
    method = Column(String)
    path = Column(String)
    status_code = Column(Integer)
    response_time_ms = Column(Float)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_email = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)

# function_telemetry — tracks every function call
class FunctionTelemetry(Base):
    __tablename__ = "function_telemetry"
    id = Column(Integer, primary_key=True)
    function_name = Column(String, nullable=False)
    module = Column(String, nullable=True)
    call_count = Column(Integer, default=0)
    total_time_ms = Column(Float, default=0)
    avg_time_ms = Column(Float, default=0)
    error_count = Column(Integer, default=0)
    last_called = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
```

---

## 🌱 DATABASE SEED

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
            is_active=True,
            email_verified=True,
        )
        db.add(admin)
        await db.commit()
```

---

## 🔐 AUTH SYSTEM — V4 (Google OAuth + Activation Code + Referral)

### Registration Flow (INVITE-ONLY):

**Option A — Admin Activation Code:**
1. User goes to `/register`
2. Enters: Username, Email, Password, Confirm Password, **Activation Code**
3. Backend validates: code exists + is unused + not expired
4. If valid: create account, mark code as used, set `activation_code_used = code`
5. Account is immediately active

**Option B — Referral from Existing Member:**
1. Existing member goes to their profile → "Refer a Friend" section
2. Enters the email of the person they want to refer
3. A `ReferralRequest` row is created with status = "pending"
4. Admin sees this request in the Admin panel → Referral Requests tab
5. Admin approves → system auto-generates an activation code and sends it to the referred email (OR admin copies it and gives manually)
6. Referred person uses that activation code to register

**Option C — Google OAuth:**
1. User clicks `[Sign in with Google]` on login/register page
2. OAuth callback: if Google email matches an existing user → log them in
3. If new Google user: check if their email has a pending approved referral → if yes, auto-create account
4. If no approved referral: show message "Your email is not yet approved. Please request an invitation."

### Login Flow:
1. POST `/api/v1/auth/login` with email + password
2. Verify password hash
3. If `two_fa_enabled = true`: return `{requires_2fa: true, temp_token: "..."}` — frontend shows 2FA input
4. User submits TOTP code OR email OTP → verify → issue full JWT in HttpOnly cookie
5. Create a new row in `sessions` table (NEVER reuse/overwrite existing rows)
6. Return user object

### JWT Configuration:
- Secret: `process.env.SESSION_SECRET`
- Algorithm: HS256
- Expiry: 7 days
- Storage: HttpOnly cookie named `ayzen-token`
- Cookie flags: `samesite=none; secure=true; httponly=true; path=/`

### Google OAuth Setup:
- Use `authlib` Python library for Google OAuth2
- Callback URL: `https://${REPLIT_DEV_DOMAIN}/api/v1/auth/google/callback`
- Required env vars: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- On successful OAuth, set the same `ayzen-token` HttpOnly cookie

---

## 🐍 PYTHON FASTAPI ROUTES — V4 COMPLETE

### Auth (`/api/v1/auth/`)
- `POST /register` — requires activation_code field; validates code; creates member account
- `POST /login` — email+password; returns 2FA challenge if enabled
- `POST /login/2fa` — submit TOTP or email OTP to complete login
- `POST /logout` — clears cookie, invalidates session row
- `GET /me` — returns current user from JWT
- `GET /google` — redirects to Google OAuth
- `GET /google/callback` — handles OAuth callback
- `POST /send-email-otp` — sends a 6-digit OTP to user's email for 2FA

### Activation Codes (`/api/v1/activation/`) — ADMIN ONLY for POST/DELETE
- `GET /` — **ADMIN ONLY** — list all codes with status (used/unused)
- `POST /generate` — **ADMIN ONLY** — generate N new codes (body: `{count: 5, expires_in_days: 30}`)
- `DELETE /{code_id}` — **ADMIN ONLY** — revoke unused code

### Referrals (`/api/v1/referrals/`)
- `POST /request` — authenticated member submits referral request (body: `{referred_email, referred_username}`)
- `GET /my` — member sees their own referral requests and status
- `GET /pending` — **ADMIN ONLY** — list pending referral requests
- `POST /{id}/approve` — **ADMIN ONLY** — approve request, auto-generate activation code
- `POST /{id}/reject` — **ADMIN ONLY** — reject with optional note

### Projects (`/api/v1/projects/`)
- `GET /` — list all projects (all users)
- `POST /` — **ADMIN ONLY** — create project
- `GET /{id}` — project detail with members and tasks
- `DELETE /{id}` — **ADMIN ONLY**
- `GET /{id}/tasks` — tasks for this project
- `POST /{id}/members` — **ADMIN ONLY** — add user(s) to project (body: `{user_ids: [1,2,3]}`)
- `DELETE /{id}/members/{user_id}` — **ADMIN ONLY** — remove member from project
- `PATCH /{id}/members/{user_id}/eligibility` — **ADMIN ONLY** — set eligibility: `{eligibility: "eligible"|"ineligible"|"not_set"}`

### Tasks (`/api/v1/tasks/`)
- `GET /` — list all tasks (filter by status, priority, project, assigned_to)
- `POST /` — **ADMIN ONLY**
- `GET /my` — tasks assigned to current user
- `PATCH /{id}/status` — member updates their task status
- `DELETE /{id}` — **ADMIN ONLY**

### Members (`/api/v1/members/`)
- `GET /` — list all members
- `GET /leaderboard` — sorted by XP
- `GET /{id}` — member profile
- `GET /{id}/vault` — **ADMIN ONLY** — view any member's vault data
- `PATCH /{id}/role` — **ADMIN ONLY**
- `DELETE /{id}` — **ADMIN ONLY**

### Profile (`/api/v1/profile/`)
- `GET /me` — full profile (username, email, socials, wallets, bio, tier, xp)
- `PATCH /me` — update profile fields (bio, socials, wallet addresses, avatar_url)
- `GET /{username}` — public profile of any member

### Account Vault (`/api/v1/vault/`)
- `GET /` — current user's vault (all wallet addresses, social handles)
- `PATCH /` — update vault fields (wallets, socials)
- `POST /totp/enable` — generate TOTP secret, return QR code URI
- `POST /totp/verify` — verify TOTP code to confirm and activate 2FA
- `POST /totp/disable` — disable 2FA (requires current TOTP code)
- `POST /email-otp/send` — send 6-digit OTP to user's email
- `POST /email-otp/verify` — verify OTP (returns `{valid: true/false}`)
- `GET /totp/generate` — returns TOTP code for the current 30-second window (for the logged-in user's own account — the "2FA code display" feature)

### XP & Wallet (`/api/v1/wallet/`)
- `GET /balance` — current user's XP balance and transferable XP
- `GET /transactions` — XP transfer history (sent + received)
- `POST /transfer` — transfer XP to another user (body: `{to_username, amount, note}`)
- `GET /rewards` — admin overview of all rewards distributed
- `GET /rank` — current user's rank + tier info
- `GET /streak` — streak info

### Gas Tracker (`/api/v1/gas/`)
- `GET /` — fetch live gas prices for 20-25 mainnets
- Mainnets to cover: Ethereum, Arbitrum, Optimism, Base, Polygon, BSC, Avalanche, Fantom, zkSync Era, Starknet, Scroll, Linea, Mantle, Blast, Zora, Mode, Manta, Taiko, Berachain, Sonic, Monad (testnet flag), Sei, Injective, Sui, Aptos
- Use public RPC endpoints or free gas APIs (blocknative, ethgasstation, etc.)
- Cache results for 30 seconds in memory to avoid rate limits
- Return: `{network, symbol, slow_gwei, standard_gwei, fast_gwei, usd_slow, usd_standard, usd_fast, updated_at}`

### AI Assistant (`/api/v1/ai/`)
- `POST /ask` — body: `{question: string, context?: "vault"|"member"|null}`
- The AI assistant has access to the ENTIRE user database (all members' wallet addresses, account details, profiles)
- It can answer: "Who owns wallet 0x1234...", "What is Alice's Discord", "List all Platinum members", "Show me all wallets", etc.
- Uses Anthropic Claude API (`claude-sonnet-4-6`) via `process.env.ANTHROPIC_API_KEY`
- System prompt to Claude: "You are AYZEN Assistant. You have access to all member data in the AYZEN WORKSPACE platform. Answer questions about members, wallets, accounts, tasks, and projects. Be concise and helpful. Data: {injected_member_data}"
- Admin-only endpoint

### Analytics (`/api/v1/analytics/`)
- `GET /me` — user analytics
- `GET /overview` — admin overview
- `GET /leaderboard` — top 10 by XP

### Telemetry & Error Log (`/api/v1/telemetry/`)
- `GET /functions` — **ADMIN ONLY** — list all 250+ tracked functions with call count, avg time, error count
- `GET /errors` — **ADMIN ONLY** — recent error log (last 100)
- `GET /errors/summary` — group errors by type/module
- `POST /errors` — internal endpoint to log errors from frontend
- `GET /api-calls` — **ADMIN ONLY** — last 50 API call logs
- `GET /function/{name}` — stats for a specific function

### Settings (`/api/v1/settings/`)
- `GET /` — user settings
- `PATCH /` — update settings
- `GET /env` — **ADMIN ONLY**
- `PATCH /env` — **ADMIN ONLY**

### Health (`/api/v1/health/`)
- `GET /` — **ADMIN ONLY** — full telemetry

---

## 🔧 TELEMETRY SYSTEM — 250+ FUNCTION TRACKING

Create a telemetry middleware decorator for Python:

```python
import functools
import time
from app.database import get_telemetry_db

def track_function(func):
    """Decorator to track every function call for telemetry."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        error_occurred = None
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            error_occurred = e
            # Log to error_logs table
            await log_error(
                function_name=func.__name__,
                error_type=type(e).__name__,
                message=str(e),
                stack_trace=traceback.format_exc()
            )
            raise
        finally:
            elapsed_ms = (time.time() - start) * 1000
            await update_function_telemetry(
                function_name=func.__name__,
                module=func.__module__,
                elapsed_ms=elapsed_ms,
                had_error=error_occurred is not None
            )
    return wrapper
```

Apply `@track_function` decorator to ALL router handler functions across:
- All auth handlers (login, register, logout, me, google, 2fa) — ~8 functions
- All project handlers (list, create, detail, delete, add_member, remove_member, set_eligibility) — ~7 functions
- All task handlers — ~6 functions
- All member handlers — ~6 functions
- All analytics handlers — ~5 functions
- All vault handlers (totp_enable, totp_verify, totp_disable, email_otp_send, email_otp_verify, get_vault, update_vault, generate_totp_code) — ~8 functions
- All wallet handlers — ~6 functions
- All gas tracker handlers — ~5 functions
- All referral handlers — ~6 functions
- All activation code handlers — ~4 functions
- All telemetry handlers — ~5 functions
- All settings handlers — ~4 functions
- All health handlers — ~3 functions
- All AI assistant handlers — ~3 functions
- All profile handlers — ~4 functions
- All helper/utility functions in database.py, models.py — ~20 functions
- All seed functions — ~3 functions
- All middleware functions — ~5 functions
- All error logging functions — ~5 functions
- Add 20-30 new utility functions for:
  - `calculate_tier_from_xp(xp)` — Bronze <1000, Silver 1000-4999, Gold 5000-19999, Platinum 20000+
  - `calculate_streak(user_id)` — count consecutive days with activity
  - `calculate_roi(user_id)` — XP earned / total possible XP
  - `format_gas_price(wei)` — convert wei to gwei
  - `generate_activation_code()` — "AYZEN-XXXX-YYYY" format
  - `hash_totp_secret(secret)` — encrypt TOTP secret at rest
  - `verify_totp_code(secret, code)` — verify TOTP
  - `send_email_otp(email, code)` — send OTP via email
  - `mask_wallet_address(address)` — "0x1234...5678" format
  - `get_gas_color(gwei)` — "green"/"yellow"/"red" based on price
  - `rank_users_by_xp(users)` — return sorted list with ranks
  - `check_eligibility(user_id, project_id)` — look up eligibility
  - `transfer_xp(from_id, to_id, amount)` — atomic XP transfer
  - `get_leaderboard_position(user_id)` — rank number
  - `check_activation_code(code)` — validate code
  - `approve_referral(referral_id, admin_id)` — approve + generate code
  - `build_ai_context(db)` — gather all member data for AI
  - `log_api_call(method, path, status, time_ms, user_id)` — log API call
  - `get_telemetry_summary()` — aggregate telemetry stats
  - `cleanup_expired_codes()` — remove expired activation codes
  - `cleanup_expired_sessions()` — remove old session rows

Total tracked functions: **250+**

---

## 🌐 NODE.JS API SERVER

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

// HEALTHCHECK — must be FIRST, no middleware, immediate 200
app.get('/api', (req, res) => {
  res.status(200).json({ status: 'ok', service: 'ayzen-workspace', ts: Date.now() });
});

app.use(cookieParser());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// CORS
app.use((req, res, next) => {
  const origin = req.headers.origin || '';
  res.setHeader('Access-Control-Allow-Origin', origin);
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PATCH,PUT,DELETE,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
});

// PROXY to Python FastAPI
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

// SERVE REACT DASHBOARD
const dashboardDist = path.resolve(__dirname, '../../../artifacts/dashboard/dist');
app.use(express.static(dashboardDist));

app.get('*', (req, res) => {
  if (req.path.startsWith('/api')) return res.status(404).json({ error: 'Not found' });
  res.sendFile(path.join(dashboardDist, 'index.html'));
});

// SPAWN PYTHON
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
  startPython();
});
```

---

## 🎨 REACT FRONTEND — ALL PAGES (V4)

### ROUTING (`App.tsx`)
```
/ → <Home /> (PUBLIC)
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
/vault → <AccountVault /> (protected)
/profile → <Profile /> (protected)
/profile/:username → <PublicProfile /> (protected)
/gas → <GasTracker /> (protected)
/ai → <AIAssistant /> (admin-only)
```

---

### PAGE 0: HOME (PUBLIC LANDING PAGE) `/`

This is the **most visually impressive page** — premium Web3 aesthetic.

**Top Navigation Bar:**
- Left: AYZEN WORKSPACE logo (gradient text, purple→cyan)
- Right: `[Login]` button + `[Sign Up]` button — both pill-shaped

**Hero Section:**
- Full-screen animated starfield/particle background (dark, like space)
- Centered content:
  - Large gradient headline: `"AYZEN WORKSPACE"`
  - Subheadline: `"Web3 Airdrop Task Management — Earn XP. Complete Quests. Dominate the Leaderboard."`
  - Two CTA buttons centered: `[Get Started →]` (→ `/register`) and `[Login]` (→ `/login`)

**Stats Bar:**
- `🔥 500+ Active Members` | `✅ 10,000+ Tasks Completed` | `🪂 50+ Airdrop Projects` | `⭐ $2M+ XP Distributed`
- Numbers animate (count-up) when scrolled into view

**Feature Slides Carousel (4 slides, auto-play 4s, pause on hover):**
- Slide 1: 🪂 "Complete Web3 Airdrop Tasks"
- Slide 2: 🏆 "Climb the Tier Ladder" (Bronze → Silver → Gold → Platinum)
- Slide 3: 📊 "Compete on the Leaderboard"
- Slide 4: 📈 "Track Your ROI"
- Dot navigation at bottom, swipe support on mobile

**Footer:** `© 2025 AYZEN WORKSPACE — Web3 Community Platform`

---

### PAGE 1: LOGIN `/login`
- Card centered on dark background
- AYZEN logo at top
- Fields: Email, Password (show/hide toggle)
- `[Login]` button
- `[Sign in with Google]` button (Google OAuth — uses real Google OAuth flow)
- Link: "Don't have an account? Sign Up"
- **2FA Step**: if server returns `{requires_2fa: true}`, show a second card:
  - Title: "Two-Factor Authentication"
  - Tab options: "Authenticator App" | "Email Code"
  - Authenticator App tab: 6-digit input for TOTP code
  - Email Code tab: button `[Send Code to Email]` → then 6-digit input
  - `[Verify]` button

---

### PAGE 2: REGISTER `/register` (INVITE-ONLY)

- Card layout
- Fields: Username, Email, Password, Confirm Password
- **Activation Code field** (required): label "Activation Code" with placeholder "AYZEN-XXXX-YYYY"
- Help text below code field: "Need an activation code? Ask an admin or get referred by an existing member."
- `[Create Account]` button → POST /api/v1/auth/register
- `[Sign up with Google]` button → if Google email has an approved referral, auto-activates; otherwise shows "not approved" message
- Link: "Already have an account? Login"
- On success: auto-login → redirect to `/dashboard`
- Error states: "Invalid activation code", "Code already used", "Code expired"

---

### PAGE 3: DASHBOARD `/dashboard`

**Layout:** 2-column grid desktop, stacked mobile

**Top Row — KPI Cards (4):**
1. Total Tasks (yours or all if admin)
2. Completed + green progress ring
3. Overdue in red
4. Your XP with tier badge

**Second Row:**
- Leaderboard Position Card
- Task Progress donut chart
- Project Progress horizontal bars

**Third Row:**
- 30-Day Activity area chart
- Recent Completions (last 5)

**Admin Extra Section:**
- Member count, total projects, pending referral requests count (badge)
- Quick links: Create Project, Create Task, View Health, View Referrals

---

### PAGE 4: PROJECTS `/projects`

**For ALL users:** grid of project cards with name, category, tier, XP name, task count, completion %, status

**Each project card shows:**
- Project name, category badge, tier badge
- Completion % progress bar
- Members joined count
- **Your Eligibility badge** for this project: gray "Not Set" / green "Eligible" / red "Ineligible"

**Project Detail click → `/projects/:id`**

**Admin-only:**
- `[+ Create Project]` button
- For each project card: `[Manage Members]` button

---

### PAGE 5: PROJECT DETAIL `/projects/:id`

**Header:** name, category, tier, status, completion %, total/completed tasks

**Members Section (new):**
- List of all members added to this project
- Each member row: avatar, username, tier, tasks completed in project, eligibility badge
- Eligibility column has dropdown (admin only): "Not Set" / "Eligible" / "Ineligible"
- Admin can add members: `[+ Add Members]` button → searchable user list → select multiple → `[Add to Project]`

**Task List:** same as before but also shows which member is doing what task

**When a member opens a project they're in:**
- Task list shows their assigned tasks with status toggle
- Eligibility badge shows their status

**2FA / Email Code in Project Context:**
- If the project has "2FA Required" flag (admin can set): members see a "Verify 2FA to access tasks" prompt
- After verification, tasks are revealed

---

### PAGE 6: TASKS `/tasks`

**For Members (MY TASKS):**
- Only their tasks
- "You have X tasks remaining" counter
- Task cards: title, project badge, priority, status toggle, due date, XP reward
- **Airdrop Action section per task**: if task is in progress, show "2FA Code" button → pops a mini-modal showing current TOTP code (30-second countdown) AND option to send email code

**For Admin (ALL TASKS):**
- All tasks across all projects
- Extra column: Assigned To
- Filter by project/member/status/priority
- `[+ Create Task]` modal

---

### PAGE 7: ACCOUNT VAULT `/vault`

This is the **secure storage page** for all account credentials and 2FA.

**Layout: Tabs**

**Tab 1 — Wallet Addresses:**
- EVM Address (Ethereum, Arbitrum, Base, etc.)
- Solana Address
- Cosmos Address
- Sui Address
- Aptos Address
- Bitcoin Address
- Each field: text input + save button + copy button
- Masked display by default (show/hide toggle)

**Tab 2 — Social Accounts:**
- Twitter / X handle
- Discord username (e.g. user#1234)
- Telegram username
- GitHub username
- Each field: text input + save button + verification link

**Tab 3 — Two-Factor Authentication (2FA):**
- Section 1: **Authenticator App (TOTP)**
  - If not enabled: button `[Enable 2FA]` → POST /api/v1/vault/totp/enable → returns QR code URI + manual secret
  - Show QR code image (use `qrcode` library client-side to render from URI)
  - Enter 6-digit code to confirm → POST /api/v1/vault/totp/verify
  - If enabled: show "2FA is ACTIVE ✅" + `[Disable 2FA]` button
  - **Live 2FA Code Display**: if 2FA is enabled, show the current TOTP code with a circular countdown timer (30 seconds). Refresh automatically. This is so the user can copy their code for use in airdrops.
  
- Section 2: **Email OTP**
  - "Receive a 6-digit OTP to your email"
  - Button: `[Send Code to my Email]` → POST /api/v1/vault/email-otp/send → shows success toast
  - 6-digit input field → `[Verify Code]` → POST /api/v1/vault/email-otp/verify
  - Shows last OTP sent timestamp

**Tab 4 — XP Wallet:**
- Your XP balance (total + transferable)
- Transfer form: "Send XP to: [username input] Amount: [number] Note: [text]" → `[Transfer]` button
- Transaction history table: Date | To/From | Amount | Note | Type (sent/received)
- Rank badge + tier display

**Admin View — Member Vault Access:**
- Admin can navigate to `/vault?user_id=X` OR click "View Vault" from Members page
- Shows ALL vault data for that member (wallets, socials, 2FA status, XP)
- Read-only for admin (admin cannot modify other users' vault data)

---

### PAGE 8: PROFILE `/profile`

**Your Profile Page:**
- Large avatar (upload image button → base64 or URL input)
- Username (large), Email, Role badge, Tier badge with XP
- Bio text (editable, textarea)
- **Streak counter** with flame animation
- **Social handles** displayed as clickable chips (Twitter, Discord, Telegram, GitHub)
- **Wallet addresses** (masked, with copy button, click to reveal)
- **Description** section: free text about themselves
- Stats: Tasks Completed, Projects Joined, XP Earned this month, Rank

**Edit Mode:** click `[Edit Profile]` → fields become editable → `[Save Changes]`

**Public Profile `/profile/:username`:**
- Same view but read-only for other members
- Shows: username, bio, tier, XP, streak, social handles, description
- Does NOT show wallet addresses for privacy (unless admin viewing)

---

### PAGE 9: ANALYSIS `/analysis`

Same as V3 but add:
- **Referral Stats**: how many people you've referred, how many were approved
- **Eligibility Overview**: list of projects and your eligibility status in each

---

### PAGE 10: MEMBERS `/members` (LEADERBOARD)

Same as V3 plus:
- Each member row: click "View Vault" (admin only) → opens vault modal for that member
- Eligibility column for selected project (dropdown to filter by project)
- `[Refer New Member]` button → opens referral modal

**Referral Modal (for members):**
- "Refer a Friend to AYZEN"
- Fields: Email, Username (optional), Note
- `[Submit Referral Request]` → POST /api/v1/referrals/request
- Shows pending referrals below

**Admin: Referral Requests Tab** (separate section at top of Members page, admin only):
- List of pending referral requests: Referred By | Referred Email | Date | Status
- `[Approve]` → generates activation code + shows it to admin to share
- `[Reject]` → with optional note

---

### PAGE 11: GAS TRACKER `/gas`

**Header:** "⛽ Live Gas Tracker" with last updated timestamp + auto-refresh every 30s

**Grid of gas cards (20-25 mainnets):**

Each card shows:
- Network name + logo/icon (use chain logos from public CDN)
- Three columns: Slow | Standard | Fast
- Each column: gwei value + USD estimate
- Color indicator: green (cheap) / yellow (moderate) / red (expensive)
- Based on ETH price for USD calculation (fetch from CoinGecko free API)

**Networks covered:**
1. Ethereum (ETH)
2. Arbitrum One
3. Optimism
4. Base
5. Polygon
6. BNB Smart Chain
7. Avalanche C-Chain
8. Fantom
9. zkSync Era
10. Starknet
11. Scroll
12. Linea
13. Mantle
14. Blast
15. Zora
16. Mode
17. Manta Pacific
18. Taiko
19. Berachain
20. Sonic
21. Sei Network
22. Injective
23. Abstract
24. Unichain
25. MegaETH (if mainnet by launch, else show "Coming Soon")

**Implementation:** Use public RPC `eth_gasPrice` calls for EVM chains. Cache in memory for 30 seconds. For non-EVM (Solana, Sui, etc.) show static "~$0.001" or fetch from their respective APIs.

---

### PAGE 12: AI ASSISTANT `/ai` — ADMIN ONLY

**Layout:** Chat interface

**Header:** "🤖 AYZEN AI Assistant" with subtitle "Ask anything about your workspace members, wallets, and accounts"

**Chat interface:**
- Message bubbles (user = right, AI = left)
- Input bar at bottom with send button
- "Suggested queries" chips at top when no messages:
  - "List all Platinum tier members"
  - "Who owns wallet 0x..."
  - "Show me all Discord handles"
  - "Which members haven't completed any tasks?"
  - "List all wallet addresses"

**AI Behavior:**
- POST `/api/v1/ai/ask` with the question
- Backend gathers all member data (name, email, tier, wallets, socials, tasks, XP) and injects into Claude system prompt
- Claude responds with the answer
- Display markdown-formatted responses

**Privacy Notice at top:** "⚠️ This assistant has access to all member data. All queries are logged."

---

### PAGE 13: SETTINGS `/settings`

Same as V3 plus:
- **Google Account** section: shows if Google account is linked, `[Link Google Account]` button
- **2FA Settings** shortcut: link to Vault → 2FA tab
- **Profile Visibility** toggle: "Show my wallet addresses to other members" (on/off)

---

### PAGE 14: HEALTH `/health` — ADMIN ONLY

**All sections from V3 plus:**

**Section 7 — Error Log (new):**
- Table: Timestamp | Level | Function | Route | Error Type | Message | User
- Color: debug=gray, info=blue, warning=yellow, error=red, critical=dark red
- Filter by level, date range
- `[Clear Logs]` button (with confirmation)
- Export to CSV button

**Section 8 — Function Telemetry (new):**
- Table: Function Name | Module | Call Count | Avg Time (ms) | Error Count | Last Called | Error Rate %
- 250+ rows (paginated, 25 per page)
- Sort by call count, avg time, error count
- Search by function name
- Bar charts for top 10 most-called functions
- Bar charts for top 10 slowest functions
- Bar charts for top 10 most-errored functions

**Section 9 — User Sessions (new):**
- Active sessions table: User | IP | Started | Expires | User Agent
- Admin can revoke any session (DELETE that session row)

---

### PAGE 15: DEVELOPER `/developer` — ADMIN ONLY

Same as V3 plus:
- **Section 6 — Referral System Status**: count of pending requests, used codes, unused codes
- **Section 7 — Google OAuth Status**: show if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are configured

---

## 🎨 DESIGN SYSTEM

```css
--bg-primary: #0a0a0f;
--bg-secondary: #12121a;
--bg-tertiary: #1a1a28;
--border: #2a2a3f;
--accent-purple: #7c3aed;
--accent-cyan: #06b6d4;
--accent-gradient: linear-gradient(135deg, #7c3aed, #06b6d4);
--text-primary: #f1f5f9;
--text-secondary: #94a3b8;
--success: #22c55e;
--warning: #f59e0b;
--danger: #ef4444;
--tier-bronze: #cd7f32;
--tier-silver: #c0c0c0;
--tier-gold: #ffd700;
--tier-platinum: #e5e4e2;
```

**Tier Badges:** Bronze=amber-800, Silver=gray-500, Gold=yellow-500, Platinum=slate-300

**Typography:** Inter font from Google Fonts

**Sidebar Navigation (authenticated):**
```
AYZEN WORKSPACE (gradient logo)
────────────────
📊 Dashboard
📁 Projects
✅ Tasks
📈 Analysis
👥 Members
🔐 Vault         ← NEW
👤 Profile        ← NEW
⛽ Gas Tracker    ← NEW
────────────────
⚙️ Settings
[Admin only:]
🤖 AI Assistant   ← NEW
🛠️ Developer
💚 Health
────────────────
👤 [User avatar + username]
[Logout]
```

---

## 📦 ENVIRONMENT VARIABLES (Replit Secrets)

| Key | Example | Notes |
|-----|---------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@localhost/ayzen` | Required |
| `SESSION_SECRET` | 64-char random string | JWT signing |
| `GOOGLE_CLIENT_ID` | `123456-abc.apps.googleusercontent.com` | Google OAuth |
| `GOOGLE_CLIENT_SECRET` | `GOCSPX-...` | Google OAuth |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | AI Assistant |
| `SMTP_HOST` | `smtp.gmail.com` | Email OTP |
| `SMTP_PORT` | `587` | Email OTP |
| `SMTP_USER` | `your@gmail.com` | Email OTP |
| `SMTP_PASS` | `app-password` | Email OTP |
| `TELEGRAM_BOT_TOKEN` | `123456:ABC...` | Optional |
| `INTERNAL_WEBHOOK_TOKEN` | random hex | Internal API |
| `CORS_ORIGINS` | `https://${REPLIT_DEV_DOMAIN}` | Frontend |
| `NODE_ENV` | `production` | |
| `PYTHON_ENV` | `production` | |

---

## 🐍 PYTHON REQUIREMENTS (`apps/api/requirements.txt`)

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy[asyncio]==2.0.36
asyncpg==0.29.0
alembic==1.13.3
bcrypt==4.2.0
python-jose[cryptography]==3.3.0
python-multipart==0.0.12
pydantic==2.9.2
pydantic-settings==2.5.2
httpx==0.27.2
authlib==1.3.2
pyotp==2.9.0
qrcode==8.0
pillow==10.4.0
aiosmtplib==3.0.2
psutil==6.1.0
anthropic==0.34.2
email-validator==2.2.0
python-dotenv==1.0.1
```

---

## 🛠️ BUILD SCRIPT

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

## 🐛 COMMON ERRORS — FIX PROACTIVELY

| Error | Cause | Fix |
|-------|-------|-----|
| Two users see same account | Shared session state | Use sessions table, unique token per login |
| `healthcheck /api 500` | DB call in healthcheck | Return `{status:"ok"}` immediately, no DB |
| `port 8080 never opened` | Node crashed | Bind 8080 first, spawn Python after |
| `502 on /api/v1/*` | Python not ready | Add retry in proxy error handler |
| `PYTHONPATH error` | Module not found | Set `PYTHONPATH=/home/runner/workspace` |
| `JWT cookie not sent` | Wrong cookie flags | `samesite=none; secure=true` |
| `React 404 on refresh` | Missing SPA fallback | Catch-all route serving index.html |
| `Google OAuth redirect` | Wrong callback URL | Set to `https://${REPLIT_DEV_DOMAIN}/api/v1/auth/google/callback` |
| `TOTP code invalid` | Time drift | Use `pyotp` with valid_window=1 |
| `asyncpg can't connect` | Wrong URL format | Use `postgresql+asyncpg://...` |

---

## ✅ FINAL DEPLOYMENT CHECKLIST

- [ ] `.replit` has exactly ONE `[[ports]]` block: `localPort=8080, externalPort=80`
- [ ] `GET /api` returns HTTP 200 `{status:"ok"}` immediately, no DB
- [ ] Python FastAPI binds to `127.0.0.1:8000`
- [ ] Admin seeded: `bibappix420@gmail.com` / `12345678@Ba1`
- [ ] Two different users can log in simultaneously and see DIFFERENT accounts
- [ ] Home page `/` is publicly accessible, has Login + SignUp buttons in top-right
- [ ] Register page requires valid activation code
- [ ] Google OAuth works (if configured)
- [ ] Account Vault page shows wallet addresses, socials, 2FA setup
- [ ] Live TOTP code display works (30-second countdown)
- [ ] Email OTP send/verify works
- [ ] Referral request system works (member submit → admin approve → code generated)
- [ ] Project members can be added, eligibility can be set (not_set/eligible/ineligible)
- [ ] Gas tracker shows 20+ mainnets with live prices
- [ ] AI Assistant answers questions about member data (admin only)
- [ ] Health page shows function telemetry (250+ functions)
- [ ] Error log table in Health page
- [ ] XP transfer between users works
- [ ] Profile page with image upload, bio, socials, wallets
- [ ] Sidebar shows all new pages (Vault, Profile, Gas Tracker, AI Assistant)
- [ ] Admin can see all member vaults from Members page
- [ ] `scripts/build.sh` runs without errors
- [ ] No hardcoded secrets anywhere

---

## 🎯 IMPLEMENTATION ORDER (V4)

Build in this exact order:

1. **Database & Models** — all tables including new ones (activation_codes, referral_requests, account_vault, xp_transfers, error_logs, api_call_logs, function_telemetry, sessions, project_members)
2. **Seed Admin** — verify login works
3. **Auth API** — login/register/logout/me WITH activation code validation
4. **Sessions table** — fix dual-account bug, each login creates unique session row
5. **Google OAuth** — authlib integration
6. **Activation Codes API** — admin generate/list/revoke
7. **Referral System API** — submit/list/approve/reject
8. **Node.js proxy** — verify end-to-end
9. **Projects API** — with member management + eligibility
10. **Tasks API** — with 2FA requirement flag
11. **Members API** — with vault access endpoint
12. **Profile API** — full profile CRUD
13. **Account Vault API** — wallets, socials, TOTP, email OTP
14. **XP Wallet API** — transfer, balance, history
15. **Gas Tracker API** — fetch live gas, 25 networks, 30s cache
16. **AI Assistant API** — Claude integration
17. **Telemetry System** — @track_function decorator on all 250+ functions
18. **Analytics API**
19. **Health API** — with error logs and function telemetry
20. **Settings API**
21. **React: Home page** — with top-right Login/Signup nav, hero, stats, carousel
22. **React: Login** — with Google OAuth button + 2FA step
23. **React: Register** — with activation code field
24. **React: Layout** — updated sidebar with new pages
25. **React: Dashboard** — with referral requests count for admin
26. **React: Projects** — with member management + eligibility badges
27. **React: Project Detail** — with members section + eligibility dropdowns
28. **React: Tasks** — with 2FA code button per task
29. **React: Account Vault** — tabs: wallets, socials, 2FA, XP wallet
30. **React: Profile** — image upload, bio, socials, wallets
31. **React: Gas Tracker** — grid of 25 network cards
32. **React: AI Assistant** — chat interface
33. **React: Members** — with referral modal + admin vault access + referral requests
34. **React: Analysis** — with referral stats + eligibility overview
35. **React: Settings** — with Google link + 2FA shortcut
36. **React: Health** — with error log + function telemetry tables
37. **React: Developer** — with OAuth + referral status sections

---

*AYZEN WORKSPACE — Ultimate Replit Mega Prompt V4*
*Generated: 2026-06-17 | Admin: bibappix420@gmail.com | Stack: Node 20 + Python 3.12 + React + PostgreSQL*
*New in V4: Google OAuth, Activation Codes, Referral System, Account Vault, 2FA (TOTP + Email OTP), Gas Tracker (25 networks), AI Assistant, XP Transfer, Profile System, Project Member Eligibility, 250+ Function Telemetry, Error Logger, Session Fix (dual-account bug), Homepage with Login/Signup nav*
