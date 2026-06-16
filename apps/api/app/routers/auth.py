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

logger = logging.getLogger("ayzen.routers.auth")
router = APIRouter()
resend.api_key = os.environ.get("RESEND_API_KEY", "")

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str

class LinkCodeResponse(BaseModel):
    code: str
    expires_in: int

def generate_code() -> str:
    return str(random.randint(100000, 999999))

async def send_verification_email(email: str, code: str):
    try:
        resend.Emails.send({
            "from": "Ayzen <noreply@ayzen.tech>",
            "to": email,
            "subject": "Your Ayzen verification code",
            "html": f"""
            <div style="font-family:sans-serif;max-width:400px;margin:auto;padding:32px">
              <h2 style="color:#6C63FF">Ayzen Verification</h2>
              <p>Your verification code is:</p>
              <h1 style="letter-spacing:8px;color:#333;text-align:center">{code}</h1>
              <p style="color:#888;font-size:13px">Expires in 10 minutes. Do not share this code.</p>
            </div>
            """
        })
    except Exception as e:
        logger.error(f"Email send failed: {e}")

@router.post("/register")
async def register(body: RegisterRequest, request: Request):
    db = request.app.state.db
    async with db() as session:
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

        await session.execute(
            text("INSERT INTO tenants (id, name, slug) VALUES (:tid, :name, :slug)"),
            {"tid": tenant_id, "name": body.full_name or body.email, "slug": tenant_slug}
        )
        await session.execute(
            text("""
                INSERT INTO users (id, tenant_id, email, full_name, role, password_hash)
                VALUES (:uid, :tid, :email, :name, 'owner', :pwd)
            """),
            {"uid": user_id, "tid": tenant_id, "email": body.email,
             "name": body.full_name, "pwd": pwd_hash}
        )
        await session.execute(
            text("INSERT INTO user_settings (user_id) VALUES (:uid) ON CONFLICT DO NOTHING"),
            {"uid": user_id}
        )
        await session.execute(
            text("INSERT INTO user_bot_state (user_id, locale) VALUES (:uid, 'bn') ON CONFLICT DO NOTHING"),
            {"uid": user_id}
        )

        code = generate_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
        await session.execute(
            text("""
                INSERT INTO email_verifications (email, code, expires_at)
                VALUES (:email, :code, :expires_at)
            """),
            {"email": body.email, "code": code, "expires_at": expires_at}
        )

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

    return {"status": "verified", "email": body.email}

@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response):
    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("SELECT id, password_hash, role, tenant_id, email_verified FROM users WHERE email = :email"),
            {"email": body.email}
        )
        user = result.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="invalid_credentials")
        if not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
            raise HTTPException(status_code=401, detail="invalid_credentials")
        if not user.email_verified:
            raise HTTPException(status_code=403, detail="email_not_verified")

    return {"status": "logged_in", "email": body.email, "role": user.role}
