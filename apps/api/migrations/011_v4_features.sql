-- ============================================================
-- AYZEN V4 Features Migration (011)
-- Run AFTER 010_ayzen_extended.sql
-- ============================================================

BEGIN;

-- ── New columns on users ───────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS username           TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret        TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS two_fa_enabled     BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS bio                TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS twitter_handle     TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS discord_handle     TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_handle    TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS github_handle      TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS xp_transferable    BIGINT  NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS activation_code_used TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url         TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified     BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash      TEXT;

-- ── activation_codes ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activation_codes (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    code        TEXT        UNIQUE NOT NULL,
    created_by  UUID        REFERENCES users(id) ON DELETE SET NULL,
    used_by     UUID        REFERENCES users(id) ON DELETE SET NULL,
    is_used     BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    used_at     TIMESTAMPTZ,
    expires_at  TIMESTAMPTZ
);

-- ── referral_requests ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS referral_requests (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id         UUID        REFERENCES users(id) ON DELETE CASCADE,
    referred_email      TEXT        NOT NULL,
    referred_username   TEXT,
    status              TEXT        NOT NULL DEFAULT 'pending'
                                        CHECK (status IN ('pending','approved','rejected')),
    admin_note          TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at         TIMESTAMPTZ,
    reviewed_by         UUID        REFERENCES users(id) ON DELETE SET NULL,
    activation_code_id  UUID        REFERENCES activation_codes(id) ON DELETE SET NULL
);

-- ── account_vault ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS account_vault (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,
    evm_address         TEXT,
    solana_address      TEXT,
    cosmos_address      TEXT,
    sui_address         TEXT,
    aptos_address       TEXT,
    btc_address         TEXT,
    twitter             TEXT,
    discord             TEXT,
    telegram            TEXT,
    github              TEXT,
    totp_secret         TEXT,
    totp_enabled        BOOLEAN     NOT NULL DEFAULT FALSE,
    email_code_hash     TEXT,
    email_code_expires  TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── xp_transfers ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS xp_transfers (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user_id UUID       REFERENCES users(id) ON DELETE SET NULL,
    to_user_id  UUID        REFERENCES users(id) ON DELETE SET NULL,
    amount      INTEGER     NOT NULL,
    note        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── error_logs ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS error_logs (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level           TEXT        NOT NULL DEFAULT 'error',
    function_name   TEXT,
    route           TEXT,
    error_type      TEXT,
    message         TEXT,
    stack_trace     TEXT,
    user_id         UUID        REFERENCES users(id) ON DELETE SET NULL,
    request_data    TEXT
);

-- ── api_call_logs ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_call_logs (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    method          TEXT,
    path            TEXT,
    status_code     INTEGER,
    response_time_ms FLOAT,
    user_id         UUID        REFERENCES users(id) ON DELETE SET NULL,
    user_email      TEXT,
    ip_address      TEXT
);

-- ── function_telemetry ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS function_telemetry (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    function_name   TEXT        NOT NULL UNIQUE,
    module          TEXT,
    call_count      INTEGER     NOT NULL DEFAULT 0,
    total_time_ms   FLOAT       NOT NULL DEFAULT 0,
    avg_time_ms     FLOAT       NOT NULL DEFAULT 0,
    error_count     INTEGER     NOT NULL DEFAULT 0,
    last_called     TIMESTAMPTZ,
    last_error      TEXT
);

COMMIT;
