-- ID: AX09      |  Local: A1Y1          |  Module: X02 (M01)
-- ============================================================
-- AYZEN — Full Schema Migration
-- Run once on a fresh database:
--   psql $DATABASE_URL -f migrations/009_ayzen_bot.sql
-- ============================================================

BEGIN;

-- ─── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── Helper function ─────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID AS $$
    SELECT NULLIF(current_setting('app.current_tenant', TRUE), '')::UUID;
$$ LANGUAGE sql STABLE;

-- ─── tenants ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tenants (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT        NOT NULL,
    slug       TEXT        UNIQUE NOT NULL,
    plan       TEXT        NOT NULL DEFAULT 'free'
                               CHECK (plan IN ('free','pro','enterprise')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── users ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email                TEXT        UNIQUE NOT NULL,
    full_name            TEXT,
    role                 TEXT        NOT NULL DEFAULT 'member'
                                         CHECK (role IN ('owner','manager','member')),
    telegram_user_id     BIGINT      UNIQUE,
    onboarding_completed BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_tenant      ON users (tenant_id);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users (telegram_user_id)
    WHERE telegram_user_id IS NOT NULL;

-- ─── projects ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name        TEXT        NOT NULL,
    description TEXT,
    created_by  UUID        REFERENCES users(id),
    deleted_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_tenant ON projects (tenant_id)
    WHERE deleted_at IS NULL;

-- ─── project_members ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS project_members (
    project_id  UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id     UUID        NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    role        TEXT        NOT NULL DEFAULT 'member'
                                CHECK (role IN ('owner','manager','member')),
    assigned_by UUID        REFERENCES users(id),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (project_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_pm_user    ON project_members (user_id);
CREATE INDEX IF NOT EXISTS idx_pm_project ON project_members (project_id);
CREATE INDEX IF NOT EXISTS idx_pm_assigned_at ON project_members (project_id, assigned_at DESC);

-- ─── tasks ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id         UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tenant_id          UUID        NOT NULL REFERENCES tenants(id)  ON DELETE CASCADE,
    title              TEXT        NOT NULL,
    task_type          TEXT        NOT NULL DEFAULT 'other'
                                       CHECK (task_type IN ('twitter','discord','onchain','form','other')),
    target_url         TEXT,
    points_per_account INTEGER     NOT NULL DEFAULT 0,
    max_slots_per_user INTEGER     NOT NULL DEFAULT 5,  -- 0 = unlimited
    deadline           TIMESTAMPTZ,
    notify_sent        BOOLEAN     NOT NULL DEFAULT FALSE,
    created_by         UUID        REFERENCES users(id),
    archived_at        TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_project   ON tasks (project_id) WHERE archived_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_tenant    ON tasks (tenant_id)  WHERE archived_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_deadline  ON tasks (deadline)
    WHERE archived_at IS NULL AND deadline IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_title_trgm ON tasks USING gin (title gin_trgm_ops);

-- ─── account_slots ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS account_slots (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID        NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    project_id       UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    slot_name        TEXT        NOT NULL DEFAULT 'M1',
    twitter_username TEXT,
    discord_username TEXT,
    wallet_address   TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, project_id, slot_name)
);

CREATE INDEX IF NOT EXISTS idx_slots_user    ON account_slots (user_id);
CREATE INDEX IF NOT EXISTS idx_slots_project ON account_slots (project_id);

-- ─── task_completions ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS task_completions (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id         UUID        NOT NULL REFERENCES tasks(id)         ON DELETE CASCADE,
    user_id         UUID        NOT NULL REFERENCES users(id)         ON DELETE CASCADE,
    account_slot_id UUID        NOT NULL REFERENCES account_slots(id) ON DELETE CASCADE,
    submitted_via   TEXT        NOT NULL DEFAULT 'bot'
                                    CHECK (submitted_via IN ('bot','web','api')),
    points_earned   INTEGER     NOT NULL DEFAULT 0,
    proof_url       TEXT,
    completed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (task_id, account_slot_id)   -- one completion per slot per task
);

CREATE INDEX IF NOT EXISTS idx_tc_task      ON task_completions (task_id);
CREATE INDEX IF NOT EXISTS idx_tc_user      ON task_completions (user_id);
CREATE INDEX IF NOT EXISTS idx_tc_slot      ON task_completions (account_slot_id);
CREATE INDEX IF NOT EXISTS idx_tc_completed ON task_completions (completed_at DESC);

-- ─── user_settings ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_settings (
    user_id           UUID    PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    locale            TEXT    NOT NULL DEFAULT 'bn'
                                  CHECK (locale IN ('bn','en')),
    notify_deadline   BOOLEAN NOT NULL DEFAULT TRUE,
    notify_assignment BOOLEAN NOT NULL DEFAULT TRUE,
    notify_broadcast  BOOLEAN NOT NULL DEFAULT TRUE,
    quiet_hours_start TIME,
    quiet_hours_end   TIME,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─── user_bot_state ──────────────────────────────────────────────────────────
-- Mirrors Redis bot state; used as fallback on Redis miss
CREATE TABLE IF NOT EXISTS user_bot_state (
    user_id           UUID    PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    telegram_user_id  BIGINT  UNIQUE,
    state             TEXT    NOT NULL DEFAULT 'IDLE',
    active_project_id UUID    REFERENCES projects(id),
    locale            TEXT    NOT NULL DEFAULT 'bn',
    wizard_step       INTEGER NOT NULL DEFAULT 0,
    wizard_data       JSONB   NOT NULL DEFAULT '{}',
    last_seen_at      TIMESTAMPTZ,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ubs_telegram ON user_bot_state (telegram_user_id)
    WHERE telegram_user_id IS NOT NULL;

-- ─── bot_link_codes ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bot_link_codes (
    code       TEXT        PRIMARY KEY,
    user_id    UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '10 minutes',
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_link_codes_user    ON bot_link_codes (user_id);
CREATE INDEX IF NOT EXISTS idx_link_codes_expires ON bot_link_codes (expires_at);

-- ─── bot_idempotency ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bot_idempotency (
    callback_id  TEXT        PRIMARY KEY,
    user_id      UUID        REFERENCES users(id) ON DELETE CASCADE,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_idempotency_time ON bot_idempotency (processed_at);

-- ─── bot_wizard_drafts ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bot_wizard_drafts (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    wizard_type TEXT        NOT NULL
                                CHECK (wizard_type IN ('new_task','new_slot','broadcast')),
    draft_json  JSONB       NOT NULL DEFAULT '{}',
    expires_at  TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '2 hours',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_drafts_user_type ON bot_wizard_drafts (user_id, wizard_type);
CREATE        INDEX IF NOT EXISTS idx_drafts_expires   ON bot_wizard_drafts (expires_at);

-- ─── bot_broadcasts ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bot_broadcasts (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID        NOT NULL REFERENCES tenants(id)  ON DELETE CASCADE,
    sender_id    UUID        REFERENCES users(id)    ON DELETE SET NULL,
    project_id   UUID        REFERENCES projects(id) ON DELETE SET NULL,
    message      TEXT        NOT NULL,
    target_count INTEGER     NOT NULL DEFAULT 0,
    sent_count   INTEGER     NOT NULL DEFAULT 0,
    failed_count INTEGER     NOT NULL DEFAULT 0,
    status       TEXT        NOT NULL DEFAULT 'pending'
                                 CHECK (status IN ('pending','sending','completed','failed','cancelled')),
    completed_at TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_broadcasts_tenant ON bot_broadcasts (tenant_id, created_at DESC);

-- ─── bot_audit_log ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bot_audit_log (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID        NOT NULL,
    user_id          UUID        REFERENCES users(id) ON DELETE SET NULL,
    action           TEXT        NOT NULL,
    entity           TEXT,
    entity_id        UUID,
    meta             JSONB       NOT NULL DEFAULT '{}',
    telegram_msg_id  BIGINT,
    telegram_chat_id BIGINT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_tenant ON bot_audit_log (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user   ON bot_audit_log (user_id);

-- ─── analytics_snapshots ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS analytics_snapshots (
    project_id    UUID    NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    snapshot_date DATE    NOT NULL,
    completions   INTEGER NOT NULL DEFAULT 0,
    unique_users  INTEGER NOT NULL DEFAULT 0,
    total_points  BIGINT  NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (project_id, snapshot_date)
);

-- ─── task_pins ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS task_pins (
    user_id    UUID        NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    task_id    UUID        NOT NULL REFERENCES tasks(id)    ON DELETE CASCADE,
    project_id UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    pinned_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, task_id)
);

-- ─── referrals ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS referrals (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id      UUID        NOT NULL REFERENCES users(id),
    referred_user_id UUID        NOT NULL REFERENCES users(id),
    project_id       UUID        REFERENCES projects(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (referrer_id, referred_user_id)
);

-- ─── Row-Level Security ──────────────────────────────────────────────────────

ALTER TABLE users               ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects            ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_members     ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks               ENABLE ROW LEVEL SECURITY;
ALTER TABLE account_slots       ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_completions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings       ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_bot_state      ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_broadcasts      ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_audit_log       ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_pins           ENABLE ROW LEVEL SECURITY;
ALTER TABLE referrals           ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_wizard_drafts   ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_idempotency     ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_link_codes      ENABLE ROW LEVEL SECURITY;

-- service_role bypasses RLS for all internal operations
CREATE POLICY rls_service_bypass ON users               FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON projects            FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON project_members     FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON tasks               FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON account_slots       FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON task_completions    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON user_settings       FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON user_bot_state      FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON bot_broadcasts      FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON bot_audit_log       FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON analytics_snapshots FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON task_pins           FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON referrals           FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON bot_wizard_drafts   FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON bot_idempotency     FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON bot_link_codes      FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Tenant isolation via app.current_tenant session variable
-- Applied by FastAPI before every query: SET LOCAL app.current_tenant = '...'

CREATE POLICY users_tenant       ON users               FOR ALL USING (tenant_id            = current_tenant_id());
CREATE POLICY projects_tenant    ON projects            FOR ALL USING (tenant_id            = current_tenant_id());
CREATE POLICY pm_tenant          ON project_members     FOR ALL USING (project_id IN (SELECT id FROM projects WHERE tenant_id = current_tenant_id()));
CREATE POLICY tasks_tenant       ON tasks               FOR ALL USING (tenant_id            = current_tenant_id());
CREATE POLICY slots_tenant       ON account_slots       FOR ALL USING (user_id   IN (SELECT id FROM users    WHERE tenant_id = current_tenant_id()));
CREATE POLICY tc_tenant          ON task_completions    FOR ALL USING (user_id   IN (SELECT id FROM users    WHERE tenant_id = current_tenant_id()));
CREATE POLICY us_tenant          ON user_settings       FOR ALL USING (user_id   IN (SELECT id FROM users    WHERE tenant_id = current_tenant_id()));
CREATE POLICY ubs_tenant         ON user_bot_state      FOR ALL USING (user_id   IN (SELECT id FROM users    WHERE tenant_id = current_tenant_id()));
CREATE POLICY broadcasts_tenant  ON bot_broadcasts      FOR ALL USING (tenant_id            = current_tenant_id());
CREATE POLICY audit_tenant       ON bot_audit_log       FOR ALL USING (tenant_id            = current_tenant_id());
CREATE POLICY analytics_tenant   ON analytics_snapshots FOR ALL USING (project_id IN (SELECT id FROM projects WHERE tenant_id = current_tenant_id()));
CREATE POLICY pins_tenant        ON task_pins           FOR ALL USING (user_id   IN (SELECT id FROM users    WHERE tenant_id = current_tenant_id()));
CREATE POLICY referrals_tenant   ON referrals           FOR ALL USING (referrer_id IN (SELECT id FROM users  WHERE tenant_id = current_tenant_id()));
CREATE POLICY drafts_tenant      ON bot_wizard_drafts   FOR ALL USING (user_id   IN (SELECT id FROM users    WHERE tenant_id = current_tenant_id()));
CREATE POLICY idempotency_user   ON bot_idempotency     FOR ALL USING (user_id   IN (SELECT id FROM users    WHERE tenant_id = current_tenant_id()));
CREATE POLICY link_codes_tenant  ON bot_link_codes      FOR ALL USING (user_id   IN (SELECT id FROM users    WHERE tenant_id = current_tenant_id()));

-- ─── pg_cron jobs ─────────────────────────────────────────────────────────────
-- Enable pg_cron first: Supabase Dashboard → Database → Extensions → pg_cron
-- Then uncomment the blocks below.

-- -- Purge expired idempotency keys every 5 minutes
-- SELECT cron.schedule(
--     'clean-bot-idempotency', '*/5 * * * *',
--     $$DELETE FROM bot_idempotency
--       WHERE processed_at < NOW() - INTERVAL '10 minutes'$$
-- );

-- -- Purge expired link codes every 30 minutes
-- SELECT cron.schedule(
--     'clean-link-codes', '*/30 * * * *',
--     $$DELETE FROM bot_link_codes
--       WHERE expires_at < NOW() AND used_at IS NULL$$
-- );

-- -- Purge expired wizard drafts every hour
-- SELECT cron.schedule(
--     'clean-wizard-drafts', '0 * * * *',
--     $$DELETE FROM bot_wizard_drafts
--       WHERE expires_at < NOW()$$
-- );

-- -- Daily analytics snapshots at 02:00 UTC
-- SELECT cron.schedule(
--     'analytics-snapshot', '0 2 * * *',
--     $$
--     INSERT INTO analytics_snapshots
--         (project_id, snapshot_date, completions, unique_users, total_points)
--     SELECT t.project_id,
--            CURRENT_DATE - 1,
--            COUNT(tc.id),
--            COUNT(DISTINCT tc.user_id),
--            COALESCE(SUM(tc.points_earned), 0)
--     FROM task_completions tc
--     JOIN tasks t ON t.id = tc.task_id
--     WHERE DATE(tc.completed_at) = CURRENT_DATE - 1
--     GROUP BY t.project_id
--     ON CONFLICT (project_id, snapshot_date) DO UPDATE SET
--         completions  = EXCLUDED.completions,
--         unique_users = EXCLUDED.unique_users,
--         total_points = EXCLUDED.total_points
--     $$
-- );

-- -- Prune audit log older than 90 days every Sunday 03:30 UTC
-- SELECT cron.schedule(
--     'prune-audit-log', '30 3 * * 0',
--     $$DELETE FROM bot_audit_log
--       WHERE created_at < NOW() - INTERVAL '90 days'$$
-- );

-- ─── Seed: default tenant for local dev (remove for production) ───────────────
-- INSERT INTO tenants (id, name, slug) VALUES
--     ('00000000-0000-0000-0000-000000000001', 'Dev Tenant', 'dev')
-- ON CONFLICT DO NOTHING;

COMMIT;
