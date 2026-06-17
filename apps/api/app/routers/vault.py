"""Account Vault — wallets, socials, TOTP, email OTP."""
from __future__ import annotations

import hashlib
import logging
import os
import random
import string
import time
from datetime import datetime, timedelta, timezone

import pyotp
import resend
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.vault")
router = APIRouter()
resend.api_key = os.environ.get("RESEND_API_KEY", "")


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _gen_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


class VaultUpdate(BaseModel):
    evm_address: str | None = None
    solana_address: str | None = None
    cosmos_address: str | None = None
    sui_address: str | None = None
    aptos_address: str | None = None
    btc_address: str | None = None
    twitter: str | None = None
    discord: str | None = None
    telegram: str | None = None
    github: str | None = None


class TotpVerifyRequest(BaseModel):
    code: str


class EmailOtpVerifyRequest(BaseModel):
    code: str


async def _ensure_vault(session, user_id: str) -> dict:
    """Get or create vault row for a user."""
    r = await session.execute(
        text("SELECT * FROM account_vault WHERE user_id = :uid"),
        {"uid": user_id}
    )
    row = r.mappings().fetchone()
    if not row:
        await session.execute(
            text("INSERT INTO account_vault (user_id) VALUES (:uid) ON CONFLICT DO NOTHING"),
            {"uid": user_id}
        )
        await session.commit()
        r = await session.execute(
            text("SELECT * FROM account_vault WHERE user_id = :uid"),
            {"uid": user_id}
        )
        row = r.mappings().fetchone()
    return dict(row)


@router.get("/")
async def get_vault(request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        vault = await _ensure_vault(session, str(user.user_id))
        vault.pop("totp_secret", None)
        vault.pop("email_code_hash", None)
        vault["id"] = str(vault["id"])
        vault["user_id"] = str(vault["user_id"])
        return vault


@router.patch("/")
async def update_vault(body: VaultUpdate, request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_vault(session, str(user.user_id))
        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        if not fields:
            return {"updated": False}
        set_clause = ", ".join(f"{k} = :{k}" for k in fields)
        fields["uid"] = str(user.user_id)
        fields["now"] = datetime.now(timezone.utc)
        await session.execute(
            text(f"UPDATE account_vault SET {set_clause}, updated_at = :now WHERE user_id = :uid"),
            fields
        )
        await session.commit()
        return {"updated": True}


# ── TOTP ─────────────────────────────────────────────────────────────────────

@router.post("/totp/enable")
async def totp_enable(request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        vault = await _ensure_vault(session, str(user.user_id))
        if vault.get("totp_enabled"):
            raise HTTPException(400, "totp_already_enabled")
        secret = pyotp.random_base32()
        await session.execute(
            text("UPDATE account_vault SET totp_secret = :s WHERE user_id = :uid"),
            {"s": secret, "uid": str(user.user_id)}
        )
        await session.commit()
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(name=user.email, issuer_name="AYZEN")
        return {"secret": secret, "uri": uri}


@router.post("/totp/verify")
async def totp_verify(body: TotpVerifyRequest, request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        vault = await _ensure_vault(session, str(user.user_id))
        secret = vault.get("totp_secret")
        if not secret:
            raise HTTPException(400, "totp_not_setup")
        totp = pyotp.TOTP(secret)
        if not totp.verify(body.code, valid_window=1):
            raise HTTPException(400, "invalid_totp_code")
        await session.execute(
            text("UPDATE account_vault SET totp_enabled = TRUE WHERE user_id = :uid"),
            {"uid": str(user.user_id)}
        )
        await session.execute(
            text("UPDATE users SET two_fa_enabled = TRUE WHERE id = :uid"),
            {"uid": str(user.user_id)}
        )
        await session.commit()
        return {"enabled": True}


@router.post("/totp/disable")
async def totp_disable(body: TotpVerifyRequest, request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        vault = await _ensure_vault(session, str(user.user_id))
        secret = vault.get("totp_secret")
        if not secret or not vault.get("totp_enabled"):
            raise HTTPException(400, "totp_not_enabled")
        totp = pyotp.TOTP(secret)
        if not totp.verify(body.code, valid_window=1):
            raise HTTPException(400, "invalid_totp_code")
        await session.execute(
            text("UPDATE account_vault SET totp_enabled = FALSE, totp_secret = NULL WHERE user_id = :uid"),
            {"uid": str(user.user_id)}
        )
        await session.execute(
            text("UPDATE users SET two_fa_enabled = FALSE WHERE id = :uid"),
            {"uid": str(user.user_id)}
        )
        await session.commit()
        return {"disabled": True}


@router.get("/totp/generate")
async def totp_generate(request: Request) -> dict:
    """Return the current TOTP code for the logged-in user (live display)."""
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        vault = await _ensure_vault(session, str(user.user_id))
        secret = vault.get("totp_secret")
        if not secret or not vault.get("totp_enabled"):
            raise HTTPException(400, "totp_not_enabled")
        totp = pyotp.TOTP(secret)
        remaining = 30 - (int(time.time()) % 30)
        return {"code": totp.now(), "remaining_seconds": remaining}


# ── Email OTP ─────────────────────────────────────────────────────────────────

@router.post("/email-otp/send")
async def email_otp_send(request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_vault(session, str(user.user_id))
        code = _gen_otp()
        code_hash = _hash_code(code)
        expires = datetime.now(timezone.utc) + timedelta(minutes=10)
        await session.execute(
            text("""
                UPDATE account_vault
                SET email_code_hash = :h, email_code_expires = :exp
                WHERE user_id = :uid
            """),
            {"h": code_hash, "exp": expires, "uid": str(user.user_id)}
        )
        await session.commit()
        try:
            resend.Emails.send({
                "from": "AYZEN <noreply@ayzen.tech>",
                "to": user.email,
                "subject": "Your AYZEN verification code",
                "html": f"""
                <div style="font-family:sans-serif;max-width:400px;margin:auto;padding:32px;background:#0a0a0f;color:#f1f5f9;border-radius:12px">
                  <h2 style="color:#7c3aed">AYZEN Verification</h2>
                  <p>Your one-time code is:</p>
                  <h1 style="letter-spacing:12px;color:#06b6d4;text-align:center;font-size:36px">{code}</h1>
                  <p style="color:#94a3b8;font-size:13px">Expires in 10 minutes. Do not share this code.</p>
                </div>
                """
            })
        except Exception as e:
            logger.error("Email OTP send failed: %s", e)
        return {"sent": True}


@router.post("/email-otp/verify")
async def email_otp_verify(body: EmailOtpVerifyRequest, request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        vault = await _ensure_vault(session, str(user.user_id))
        code_hash = _hash_code(body.code)
        expires = vault.get("email_code_expires")
        if not vault.get("email_code_hash") or vault["email_code_hash"] != code_hash:
            raise HTTPException(400, "invalid_code")
        if expires and datetime.now(timezone.utc) > expires.replace(tzinfo=timezone.utc):
            raise HTTPException(400, "code_expired")
        await session.execute(
            text("UPDATE account_vault SET email_code_hash = NULL, email_code_expires = NULL WHERE user_id = :uid"),
            {"uid": str(user.user_id)}
        )
        await session.commit()
        return {"valid": True}


# ── Admin vault access ────────────────────────────────────────────────────────

@router.get("/admin/{user_id}")
async def admin_get_vault(user_id: str, request: Request) -> dict:
    from apps.api.app.middleware.auth import require_admin
    user = await _auth(request)
    await require_admin(user)
    db = request.app.state.db
    async with db() as session:
        vault = await _ensure_vault(session, user_id)
        vault.pop("totp_secret", None)
        vault.pop("email_code_hash", None)
        vault["id"] = str(vault["id"])
        vault["user_id"] = str(vault["user_id"])
        return vault
