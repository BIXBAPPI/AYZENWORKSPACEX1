-- ============================================================
-- AYZEN — Extended Schema Migration (010)
-- Run AFTER 009_ayzen_bot.sql
-- Supabase → SQL Editor → paste → Run
-- ============================================================
-- কী কী যোগ হচ্ছে:
--   ✅ users table এ নতুন columns (telegram username, wallet, IP, email info)
--   ✅ user_uid — per-user unique ID (readable, like AYZ-00042)
--   ✅ user_social_accounts — user নিজে add করবে (Twitter, Discord, GitHub, etc)
--   ✅ project_xp_config — per project XP settings (admin set করবে)
--   ✅ user_project_xp — per project XP + global XP
--   ✅ user_project_stats — join date, active days, spend, streak per project
--   ✅ project_activity_log — user কখন কী করলো (audit trail)
--   ✅ user_accounts — account management (email/pass/wallet/XP per account)
--   ✅ RLS policies সব নতুন table এ
-- ============================================================

BEGIN;

-- ══════════════════════════════════════════════════════════════
-- PART 1: users table এ নতুন columns যোগ
-- ══════════════════════════════════════════════════════════════

-- Unique readable UID (e.g. AYZ-00042)
ALTER TABLE users ADD COLUMN IF NOT EXISTS uid            TEXT UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_username TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS wallet_address    TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS ip_address        INET;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at      TIMESTAMPTZ;

-- Email account info
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_password_hash   TEXT;   -- hashed
ALTER TABLE users ADD COLUMN IF NOT EXISTS recovery_email        TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_created_at      TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_joined_at       TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Global XP & Rank (cross-project)
ALTER TABLE users ADD COLUMN IF NOT EXISTS global_xp        BIGINT  NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS global_rank       TEXT    NOT NULL DEFAULT 'Newcomer';
ALTER TABLE users ADD COLUMN IF NOT EXISTS global_streak     INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_active_date  DATE;

-- Play points (default project points, separate from XP)
ALTER TABLE users ADD COLUMN IF NOT EXISTS play_points       BIGINT  NOT NULL DEFAULT 0;

-- UID generator — auto assign AYZ-XXXXX on insert
CREATE SEQUENCE IF NOT EXISTS users_uid_seq START 1;

CREATE OR REPLACE FUNCTION assign_user_uid()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.uid IS NULL THEN
        NEW.uid := 'AYZ-' || LPAD(nextval('users_uid_seq')::TEXT, 5, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_assign_user_uid ON users;
CREATE TRIGGER trg_assign_user_uid
    BEFORE INSERT ON users
    FOR EACH ROW EXECUTE FUNCTION assign_user_uid();

-- Existing users যাদের uid নেই তাদের assign করো
DO $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN SELECT id FROM users WHERE uid IS NULL ORDER BY created_at LOOP
        UPDATE users
        SET uid = 'AYZ-' || LPAD(nextval('users_uid_seq')::TEXT, 5, '0')
        WHERE id = rec.id;
    END LOOP;
END$$;


-- ══════════════════════════════════════════════════════════════
-- PART 2: user_social_accounts — user নিজে add করবে
-- ══════════════════════════════════════════════════════════════
-- platform: twitter, discord, github, facebook, whatsapp,
--           instagram, youtube, tiktok, telegram, custom
-- Admin project create করার সময় কোন কোন social দরকার সেটা
-- project_social_fields এ define করবে (PART 3)

CREATE TABLE IF NOT EXISTS user_social_accounts (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform     TEXT        NOT NULL
                                 CHECK (platform IN (
                                     'twitter','discord','github','facebook',
                                     'whatsapp','instagram','youtube','tiktok',
                                     'telegram','custom'
                                 )),
    platform_username TEXT,
    platform_user_id  TEXT,
    profile_url       TEXT,
    custom_label      TEXT,        -- platform='custom' হলে label দেওয়া যাবে
    verified          BOOLEAN NOT NULL DEFAULT FALSE,
    added_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, platform, platform_username)
);

CREATE INDEX IF NOT EXISTS idx_social_user     ON user_social_accounts (user_id);
CREATE INDEX IF NOT EXISTS idx_social_platform ON user_social_accounts (platform);


-- ══════════════════════════════════════════════════════════════
-- PART 3: projects table এ নতুন columns
-- ══════════════════════════════════════════════════════════════

-- Project এর নিজস্ব XP config
ALTER TABLE projects ADD COLUMN IF NOT EXISTS base_xp_label    TEXT    DEFAULT 'XP';    -- e.g. "BKXP", "StarXP"
ALTER TABLE projects ADD COLUMN IF NOT EXISTS xp_enabled       BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS play_points_label TEXT    DEFAULT 'Points';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS required_socials  TEXT[]  DEFAULT '{}';   -- ['twitter','discord']
ALTER TABLE projects ADD COLUMN IF NOT EXISTS spend_currency    TEXT    DEFAULT 'BDT';


-- ══════════════════════════════════════════════════════════════
-- PART 4: project_xp_config — per project XP rules (admin sets)
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS project_xp_config (
    project_id          UUID    PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    xp_label            TEXT    NOT NULL DEFAULT 'XP',      -- "BKXP", "StarXP" etc
    initial_xp          INTEGER NOT NULL DEFAULT 0,         -- নতুন member পেলে
    task_complete_xp    INTEGER NOT NULL DEFAULT 10,        -- per task
    streak_bonus_xp     INTEGER NOT NULL DEFAULT 5,         -- per streak day
    referral_xp         INTEGER NOT NULL DEFAULT 20,        -- referral করলে
    max_daily_xp        INTEGER,                             -- NULL = unlimited
    xp_decay_enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    xp_decay_days       INTEGER NOT NULL DEFAULT 30,        -- N দিন inactive হলে decay
    xp_decay_percent    NUMERIC(5,2) NOT NULL DEFAULT 10.0, -- কত % কমবে
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ══════════════════════════════════════════════════════════════
-- PART 5: user_project_xp — per user per project XP + global
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_project_xp (
    user_id      UUID        NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    project_id   UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    xp           BIGINT      NOT NULL DEFAULT 0,
    rank         TEXT        NOT NULL DEFAULT 'Newcomer',
    streak       INTEGER     NOT NULL DEFAULT 0,
    last_xp_date DATE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_upxp_project ON user_project_xp (project_id, xp DESC);
CREATE INDEX IF NOT EXISTS idx_upxp_user    ON user_project_xp (user_id);

-- XP add করার function (project XP + global XP একসাথে update)
CREATE OR REPLACE FUNCTION add_xp(
    p_user_id    UUID,
    p_project_id UUID,
    p_amount     INTEGER,
    p_reason     TEXT DEFAULT 'task'
)
RETURNS VOID AS $$
DECLARE
    v_max_daily   INTEGER;
    v_earned_today BIGINT;
    v_actual       INTEGER;
    v_last_date    DATE;
    v_streak       INTEGER;
BEGIN
    -- max daily XP check
    SELECT xp_decay_enabled, max_daily_xp
    INTO v_max_daily
    FROM project_xp_config WHERE project_id = p_project_id;

    IF v_max_daily IS NOT NULL THEN
        SELECT COALESCE(SUM(xp_amount), 0) INTO v_earned_today
        FROM project_activity_log
        WHERE user_id = p_user_id
          AND project_id = p_project_id
          AND activity_type = 'xp_earn'
          AND DATE(created_at) = CURRENT_DATE;

        v_actual := LEAST(p_amount, v_max_daily - v_earned_today::INTEGER);
        IF v_actual <= 0 THEN RETURN; END IF;
    ELSE
        v_actual := p_amount;
    END IF;

    -- streak update
    SELECT last_xp_date, streak INTO v_last_date, v_streak
    FROM user_project_xp
    WHERE user_id = p_user_id AND project_id = p_project_id;

    IF v_last_date = CURRENT_DATE - 1 THEN
        v_streak := COALESCE(v_streak, 0) + 1;
    ELSIF v_last_date < CURRENT_DATE - 1 OR v_last_date IS NULL THEN
        v_streak := 1;
    END IF;

    -- upsert project XP
    INSERT INTO user_project_xp (user_id, project_id, xp, streak, last_xp_date, updated_at)
    VALUES (p_user_id, p_project_id, v_actual, v_streak, CURRENT_DATE, NOW())
    ON CONFLICT (user_id, project_id) DO UPDATE SET
        xp           = user_project_xp.xp + v_actual,
        streak       = v_streak,
        last_xp_date = CURRENT_DATE,
        updated_at   = NOW();

    -- global XP update
    UPDATE users SET
        global_xp        = global_xp + v_actual,
        global_streak    = v_streak,
        last_active_date = CURRENT_DATE,
        updated_at       = NOW()
    WHERE id = p_user_id;

    -- log it
    INSERT INTO project_activity_log
        (user_id, project_id, activity_type, xp_amount, note)
    VALUES
        (p_user_id, p_project_id, 'xp_earn', v_actual, p_reason);
END;
$$ LANGUAGE plpgsql;


-- ══════════════════════════════════════════════════════════════
-- PART 6: user_project_stats — project এ join date, spend, days
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_project_stats (
    user_id          UUID        NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    project_id       UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    joined_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    active_days      INTEGER     NOT NULL DEFAULT 0,   -- মোট কয়দিন active ছিলো
    last_active_at   TIMESTAMPTZ,
    tasks_completed  INTEGER     NOT NULL DEFAULT 0,
    total_spend      NUMERIC(12,2) NOT NULL DEFAULT 0, -- total টাকা/cost
    spend_currency   TEXT        NOT NULL DEFAULT 'BDT',
    play_points      BIGINT      NOT NULL DEFAULT 0,   -- project-specific points
    PRIMARY KEY (user_id, project_id)
);

CREATE INDEX IF NOT EXISTS idx_ups_project ON user_project_stats (project_id);
CREATE INDEX IF NOT EXISTS idx_ups_user    ON user_project_stats (user_id);


-- ══════════════════════════════════════════════════════════════
-- PART 7: project_activity_log — সব activity track
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS project_activity_log (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID        NOT NULL REFERENCES users(id)    ON DELETE CASCADE,
    project_id    UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    activity_type TEXT        NOT NULL
                                  CHECK (activity_type IN (
                                      'join','task_complete','xp_earn',
                                      'spend','streak_break','streak_continue',
                                      'rank_up','social_add','account_add','custom'
                                  )),
    task_id       UUID        REFERENCES tasks(id),
    xp_amount     INTEGER,
    spend_amount  NUMERIC(12,2),
    note          TEXT,
    meta          JSONB       DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pal_user       ON project_activity_log (user_id);
CREATE INDEX IF NOT EXISTS idx_pal_project    ON project_activity_log (project_id);
CREATE INDEX IF NOT EXISTS idx_pal_type       ON project_activity_log (activity_type);
CREATE INDEX IF NOT EXISTS idx_pal_created    ON project_activity_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pal_user_proj  ON project_activity_log (user_id, project_id, created_at DESC);


-- ══════════════════════════════════════════════════════════════
-- PART 8: user_accounts — account management
-- (email/pass/wallet/XP/rank per managed account)
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_accounts (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_user_id        UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id           UUID        REFERENCES projects(id) ON DELETE SET NULL,
    label                TEXT        NOT NULL DEFAULT 'Account 1',  -- display name

    -- Identity
    account_username     TEXT,
    telegram_username    TEXT,
    email                TEXT,
    email_password_hash  TEXT,
    recovery_email       TEXT,
    wallet_address       TEXT,

    -- XP / Rank for this account
    xp                   BIGINT  NOT NULL DEFAULT 0,
    rank                 TEXT    NOT NULL DEFAULT 'Newcomer',
    play_points          BIGINT  NOT NULL DEFAULT 0,

    -- Extra info
    notes                TEXT,
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ua_owner   ON user_accounts (owner_user_id);
CREATE INDEX IF NOT EXISTS idx_ua_project ON user_accounts (project_id);
CREATE INDEX IF NOT EXISTS idx_ua_email   ON user_accounts (email) WHERE email IS NOT NULL;


-- ══════════════════════════════════════════════════════════════
-- PART 9: project join করলে auto stats + xp row তৈরি হবে
-- ══════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION on_project_member_join()
RETURNS TRIGGER AS $$
DECLARE
    v_init_xp INTEGER;
BEGIN
    -- stats row
    INSERT INTO user_project_stats (user_id, project_id, joined_at)
    VALUES (NEW.user_id, NEW.project_id, NOW())
    ON CONFLICT DO NOTHING;

    -- xp row
    INSERT INTO user_project_xp (user_id, project_id)
    VALUES (NEW.user_id, NEW.project_id)
    ON CONFLICT DO NOTHING;

    -- initial XP if config আছে
    SELECT initial_xp INTO v_init_xp
    FROM project_xp_config WHERE project_id = NEW.project_id;

    IF v_init_xp IS NOT NULL AND v_init_xp > 0 THEN
        PERFORM add_xp(NEW.user_id, NEW.project_id, v_init_xp, 'join_bonus');
    END IF;

    -- activity log
    INSERT INTO project_activity_log (user_id, project_id, activity_type, note)
    VALUES (NEW.user_id, NEW.project_id, 'join', 'Joined project');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_project_member_join ON project_members;
CREATE TRIGGER trg_project_member_join
    AFTER INSERT ON project_members
    FOR EACH ROW EXECUTE FUNCTION on_project_member_join();


-- ══════════════════════════════════════════════════════════════
-- PART 10: task complete হলে auto XP + stats update
-- ══════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION on_task_completion()
RETURNS TRIGGER AS $$
DECLARE
    v_project_id UUID;
    v_xp_per_task INTEGER;
BEGIN
    SELECT project_id INTO v_project_id FROM tasks WHERE id = NEW.task_id;

    SELECT task_complete_xp INTO v_xp_per_task
    FROM project_xp_config WHERE project_id = v_project_id;

    -- task XP যোগ
    IF v_xp_per_task IS NOT NULL AND v_xp_per_task > 0 THEN
        PERFORM add_xp(NEW.user_id, v_project_id, v_xp_per_task, 'task_complete');
    END IF;

    -- stats update
    UPDATE user_project_stats SET
        tasks_completed = tasks_completed + 1,
        last_active_at  = NOW(),
        active_days     = active_days + CASE
            WHEN DATE(last_active_at) < CURRENT_DATE THEN 1 ELSE 0
        END
    WHERE user_id = NEW.user_id AND project_id = v_project_id;

    -- activity log
    INSERT INTO project_activity_log
        (user_id, project_id, activity_type, task_id, xp_amount, note)
    VALUES
        (NEW.user_id, v_project_id, 'task_complete', NEW.task_id,
         v_xp_per_task, 'Task completed');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_task_completion ON task_completions;
CREATE TRIGGER trg_task_completion
    AFTER INSERT ON task_completions
    FOR EACH ROW EXECUTE FUNCTION on_task_completion();


-- ══════════════════════════════════════════════════════════════
-- PART 11: RLS — নতুন সব table এ
-- ══════════════════════════════════════════════════════════════

ALTER TABLE user_social_accounts  ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_xp_config     ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_project_xp       ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_project_stats    ENABLE ROW LEVEL SECURITY;
ALTER TABLE project_activity_log  ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_accounts         ENABLE ROW LEVEL SECURITY;

-- service_role সব bypass করবে
CREATE POLICY rls_service_bypass ON user_social_accounts  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON project_xp_config     FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON user_project_xp       FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON user_project_stats    FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON project_activity_log  FOR ALL TO service_role USING (true) WITH CHECK (true);
CREATE POLICY rls_service_bypass ON user_accounts         FOR ALL TO service_role USING (true) WITH CHECK (true);

-- Tenant isolation
CREATE POLICY social_tenant   ON user_social_accounts  FOR ALL
    USING (user_id IN (SELECT id FROM users WHERE tenant_id = current_tenant_id()));

CREATE POLICY xpconfig_tenant ON project_xp_config     FOR ALL
    USING (project_id IN (SELECT id FROM projects WHERE tenant_id = current_tenant_id()));

CREATE POLICY upxp_tenant     ON user_project_xp       FOR ALL
    USING (user_id IN (SELECT id FROM users WHERE tenant_id = current_tenant_id()));

CREATE POLICY ups_tenant      ON user_project_stats    FOR ALL
    USING (user_id IN (SELECT id FROM users WHERE tenant_id = current_tenant_id()));

CREATE POLICY pal_tenant      ON project_activity_log  FOR ALL
    USING (user_id IN (SELECT id FROM users WHERE tenant_id = current_tenant_id()));

CREATE POLICY ua_tenant       ON user_accounts         FOR ALL
    USING (owner_user_id IN (SELECT id FROM users WHERE tenant_id = current_tenant_id()));


-- ══════════════════════════════════════════════════════════════
-- PART 12: Useful views
-- ══════════════════════════════════════════════════════════════

-- User full profile view
CREATE OR REPLACE VIEW v_user_profile AS
SELECT
    u.id,
    u.uid,
    u.email,
    u.full_name,
    u.telegram_user_id,
    u.telegram_username,
    u.wallet_address,
    u.ip_address,
    u.global_xp,
    u.global_rank,
    u.global_streak,
    u.play_points,
    u.last_active_date,
    u.email_joined_at,
    u.onboarding_completed,
    u.role,
    u.tenant_id,
    (
        SELECT json_agg(json_build_object(
            'platform', sa.platform,
            'username', sa.platform_username,
            'profile_url', sa.profile_url,
            'verified', sa.verified
        ))
        FROM user_social_accounts sa WHERE sa.user_id = u.id
    ) AS social_accounts
FROM users u;

-- Per project leaderboard view
CREATE OR REPLACE VIEW v_project_leaderboard AS
SELECT
    upx.project_id,
    upx.user_id,
    u.uid,
    u.full_name,
    u.telegram_username,
    upx.xp,
    upx.rank,
    upx.streak,
    ups.tasks_completed,
    ups.active_days,
    ups.joined_at,
    ups.total_spend,
    RANK() OVER (PARTITION BY upx.project_id ORDER BY upx.xp DESC) AS leaderboard_position
FROM user_project_xp upx
JOIN users u ON u.id = upx.user_id
LEFT JOIN user_project_stats ups ON ups.user_id = upx.user_id AND ups.project_id = upx.project_id;

-- User project summary (একজন user এর সব project এর summary)
CREATE OR REPLACE VIEW v_user_project_summary AS
SELECT
    ups.user_id,
    ups.project_id,
    p.name AS project_name,
    p.base_xp_label,
    ups.joined_at,
    ups.active_days,
    ups.tasks_completed,
    ups.total_spend,
    ups.spend_currency,
    ups.play_points,
    upx.xp,
    upx.rank,
    upx.streak,
    upx.last_xp_date
FROM user_project_stats ups
JOIN projects p ON p.id = ups.project_id
LEFT JOIN user_project_xp upx ON upx.user_id = ups.user_id AND upx.project_id = ups.project_id;


-- ══════════════════════════════════════════════════════════════
-- VERIFY — এই queries run করো confirm করতে:
-- ══════════════════════════════════════════════════════════════
-- SELECT column_name FROM information_schema.columns WHERE table_name = 'users' ORDER BY column_name;
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
-- SELECT * FROM v_user_profile LIMIT 5;
-- SELECT * FROM v_project_leaderboard LIMIT 10;

COMMIT;
