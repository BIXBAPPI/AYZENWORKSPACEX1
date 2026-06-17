from __future__ import annotations

import logging
import uuid
import random
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import resend
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text

from apps.api.app.middleware.auth import create_access_token, verify_token

logger = logging.getLogger("ayzen.routers.auth")
router = APIRouter()
resend.api_key = os.environ.get("RESEND_API_KEY", "")

_COOKIE_NAME = "ayzen-token"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TwoFARequest(BaseModel):
    email: EmailStr
    code: str
    method: str = "totp"  # "totp" | "email"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    activation_code: str | None = None
    username: str | None = None


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


def generate_code() -> str:
    return str(random.randint(100000, 999999))


async def send_verification_email(email: str, code: str):
    try:
        resend.Emails.send({
            "from": "Ayzen <noreply@ayzen.tech>",
            "to": email,
            "subject": "Your Ayzen verification code",
            "html": f"""
            <div style="font-family:sans-serif;max-width:400px;margin:auto;padding:32px;background:#0a0a0f;color:#f1f5f9;border-radius:12px">
              <h2 style="color:#7c3aed">AYZEN Verification</h2>
              <p>Your verification code is:</p>
              <h1 style="letter-spacing:12px;color:#06b6d4;text-align:center">{code}</h1>
              <p style="color:#94a3b8;font-size:13px">Expires in 10 minutes. Do not share this code.</p>
            </div>
            """
        })
    except Exception as e:
        logger.error(f"Email send failed: {e}")


@router.post("/register")
async def register(body: RegisterRequest, request: Request):
    db = request.app.state.db
    async with db() as session:
        # Check if this is the very first user (no users in DB) — allow without code
        user_count_r = await session.execute(text("SELECT COUNT(*) FROM users"))
        user_count = user_count_r.scalar() or 0

        # Validate activation code if provided or required
        code_row = None
        if user_count > 0:
            if not body.activation_code:
                raise HTTPException(status_code=400, detail="activation_code_required")
            code_r = await session.execute(
                text("""
                    SELECT id, is_used, expires_at
                    FROM activation_codes
                    WHERE code = :code
                """),
                {"code": body.activation_code.strip().upper()}
            )
            code_row = code_r.fetchone()
            if not code_row:
                raise HTTPException(status_code=400, detail="invalid_activation_code")
            if code_row.is_used:
                raise HTTPException(status_code=400, detail="activation_code_already_used")
            if code_row.expires_at and datetime.now(timezone.utc) > code_row.expires_at.replace(tzinfo=timezone.utc):
                raise HTTPException(status_code=400, detail="activation_code_expired")

        existing = await session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": body.email}
        )
        if existing.fetchone():
            raise HTTPException(status_code=400, detail="email_already_registered")

        pwd_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
        user_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        tenant_slug = body.email.split("@")[0] + "-" + str(user_id)[:8]

        # First user gets owner role; others get member
        role = "owner" if user_count == 0 else "member"

        await session.execute(
            text("INSERT INTO tenants (id, name, slug) VALUES (:tid, :name, :slug)"),
            {"tid": tenant_id, "name": body.full_name or body.email, "slug": tenant_slug}
        )
        await session.execute(
            text("""
                INSERT INTO users (id, tenant_id, email, full_name, role, password_hash, username, activation_code_used)
                VALUES (:uid, :tid, :email, :name, :role, :pwd, :uname, :code)
            """),
            {
                "uid": user_id, "tid": tenant_id, "email": body.email,
                "name": body.full_name, "role": role, "pwd": pwd_hash,
                "uname": body.username or body.email.split("@")[0],
                "code": body.activation_code,
            }
        )
        await session.execute(
            text("INSERT INTO user_settings (user_id) VALUES (:uid) ON CONFLICT DO NOTHING"),
            {"uid": user_id}
        )
        try:
            await session.execute(
                text("INSERT INTO user_bot_state (user_id, locale) VALUES (:uid, 'bn') ON CONFLICT DO NOTHING"),
                {"uid": user_id}
            )
        except Exception:
            pass

        # Mark activation code as used
        if code_row:
            await session.execute(
                text("""
                    UPDATE activation_codes
                    SET is_used = TRUE, used_by = :uid, used_at = NOW()
                    WHERE id = :cid
                """),
                {"uid": user_id, "cid": code_row.id}
            )

        # Send email verification
        code = generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        try:
            await session.execute(
                text("""
                    INSERT INTO email_verifications (email, code, expires_at)
                    VALUES (:email, :code, :expires_at)
                    ON CONFLICT DO NOTHING
                """),
                {"email": body.email, "code": code, "expires_at": expires_at}
            )
        except Exception:
            pass

        await session.commit()

    await send_verification_email(body.email, code)
    return {"status": "verification_sent", "email": body.email}


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, request: Request):
    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("""
                SELECT id, expires_at, used FROM email_verifications
                WHERE email = :email AND code = :code
                ORDER BY created_at DESC LIMIT 1
            """),
            {"email": body.email, "code": body.code}
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=400, detail="invalid_code")
        if row.used:
            raise HTTPException(status_code=400, detail="code_already_used")
        if datetime.now(timezone.utc) > row.expires_at:
            raise HTTPException(status_code=400, detail="code_expired")

        await session.execute(
            text("UPDATE email_verifications SET used = TRUE WHERE id = :id"),
            {"id": row.id}
        )
        await session.execute(
            text("UPDATE users SET email_verified = TRUE WHERE email = :email"),
            {"email": body.email}
        )
        await session.commit()

    return {"status": "verified", "email": body.email}


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response):
    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("""
                SELECT id, password_hash, role, tenant_id, email_verified, full_name, two_fa_enabled
                FROM users WHERE email = :email
            """),
            {"email": body.email}
        )
        user = result.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    if not user.password_hash:
        raise HTTPException(status_code=401, detail="invalid_credentials")
    if not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail="invalid_credentials")

    # Skip email verification check for first owner or if not verified (graceful)
    # Only enforce if email_verified column exists and is explicitly False
    email_verified = getattr(user, "email_verified", True)
    if email_verified is False:
        raise HTTPException(status_code=403, detail="email_not_verified")

    # Check 2FA
    if user.two_fa_enabled:
        return {"requires_2fa": True, "email": body.email}

    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=body.email,
        role=user.role,
    )

    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=_COOKIE_MAX_AGE,
        path="/",
    )

    return {
        "status": "logged_in",
        "email": body.email,
        "role": user.role,
        "full_name": user.full_name,
    }


@router.post("/verify-2fa")
async def verify_2fa(body: TwoFARequest, request: Request, response: Response):
    """Second factor verification after password check."""
    import pyotp, hashlib
    db = request.app.state.db
    async with db() as session:
        user_r = await session.execute(
            text("SELECT id, role, tenant_id, full_name FROM users WHERE email = :email"),
            {"email": body.email}
        )
        user = user_r.fetchone()
        if not user:
            raise HTTPException(401, "invalid_credentials")

        vault_r = await session.execute(
            text("SELECT totp_secret, totp_enabled, email_code_hash, email_code_expires FROM account_vault WHERE user_id = :uid"),
            {"uid": str(user.id)}
        )
        vault = vault_r.fetchone()
        if not vault:
            raise HTTPException(400, "2fa_not_setup")

        if body.method == "totp":
            if not vault.totp_enabled or not vault.totp_secret:
                raise HTTPException(400, "totp_not_enabled")
            totp = pyotp.TOTP(vault.totp_secret)
            if not totp.verify(body.code, valid_window=1):
                raise HTTPException(400, "invalid_totp_code")
        elif body.method == "email":
            code_hash = hashlib.sha256(body.code.encode()).hexdigest()
            if vault.email_code_hash != code_hash:
                raise HTTPException(400, "invalid_email_code")
            if vault.email_code_expires and datetime.now(timezone.utc) > vault.email_code_expires.replace(tzinfo=timezone.utc):
                raise HTTPException(400, "email_code_expired")
            await session.execute(
                text("UPDATE account_vault SET email_code_hash = NULL WHERE user_id = :uid"),
                {"uid": str(user.id)}
            )
            await session.commit()
        else:
            raise HTTPException(400, "invalid_method")

    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=body.email,
        role=user.role,
    )
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=_COOKIE_MAX_AGE,
        path="/",
    )
    return {"status": "logged_in", "email": body.email, "role": user.role}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key=_COOKIE_NAME,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    return {"status": "logged_out"}


@router.get("/me")
async def get_me(request: Request):
    user = await verify_token(request)
    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("""
                SELECT id, tenant_id, email, full_name, role, onboarding_completed, created_at,
                       global_xp, global_streak, two_fa_enabled, username
                FROM users WHERE id = :uid
            """),
            {"uid": str(user.user_id)}
        )
        row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="user_not_found")

    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "email": row.email,
        "full_name": row.full_name,
        "username": row.username,
        "role": row.role,
        "onboarding_completed": row.onboarding_completed,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "global_xp": row.global_xp,
        "global_streak": row.global_streak,
        "two_fa_enabled": row.two_fa_enabled,
    }
