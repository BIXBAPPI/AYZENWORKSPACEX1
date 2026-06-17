"""AYZEN Auth — Firebase ID token → AYZEN JWT session exchange."""
from __future__ import annotations

import logging
import os
import uuid

import bcrypt
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.firebase_auth")
router = APIRouter()

_COOKIE_NAME = "ayzen-token"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def _get_firebase_app():
    """Initialize Firebase Admin SDK lazily."""
    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._DEFAULT_APP_NAME in firebase_admin._apps:
        return firebase_admin.get_app()

    project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
    private_key = os.environ.get("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n")
    client_email = os.environ.get("FIREBASE_CLIENT_EMAIL", "")

    if not all([project_id, private_key, client_email]):
        raise ValueError("Firebase not configured — set FIREBASE_PROJECT_ID, FIREBASE_PRIVATE_KEY, FIREBASE_CLIENT_EMAIL")

    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": project_id,
        "private_key": private_key,
        "client_email": client_email,
        "token_uri": "https://oauth2.googleapis.com/token",
    })
    return firebase_admin.initialize_app(cred)


class FirebaseLoginRequest(BaseModel):
    id_token: str
    activation_code: str | None = None  # required for first-time signups


@router.post("/firebase")
async def firebase_login(body: FirebaseLoginRequest, request: Request, response: Response) -> dict:
    """Exchange a Firebase ID token for an AYZEN JWT session cookie."""
    from apps.api.app.middleware.auth import create_access_token

    try:
        _get_firebase_app()
    except ValueError as e:
        raise HTTPException(503, f"AYZEN Auth not configured: {e}")
    except Exception as e:
        raise HTTPException(503, f"Firebase init failed: {e}")

    # Verify Firebase ID token
    try:
        from firebase_admin import auth as fb_auth
        decoded = fb_auth.verify_id_token(body.id_token)
    except Exception as e:
        raise HTTPException(401, f"invalid_firebase_token: {e}")

    firebase_uid = decoded.get("uid")
    email = decoded.get("email", "")
    name = decoded.get("name", "") or decoded.get("display_name", "") or email.split("@")[0]
    avatar_url = decoded.get("picture", "")
    provider = (decoded.get("firebase", {}).get("sign_in_provider") or "firebase")

    if not email:
        raise HTTPException(400, "firebase_token_missing_email")

    db = request.app.state.db
    async with db() as session:
        # Check if user already exists (by email)
        r = await session.execute(
            text("SELECT id, tenant_id, role, email_verified FROM users WHERE email = :email"),
            {"email": email}
        )
        existing = r.fetchone()

        if existing:
            # Existing user — just log them in
            user_id = str(existing.id)
            tenant_id = str(existing.tenant_id)
            role = existing.role

            # Update avatar if provided
            if avatar_url:
                await session.execute(
                    text("UPDATE users SET avatar_url = :url, email_verified = TRUE, updated_at = NOW() WHERE id = :id"),
                    {"url": avatar_url, "id": user_id}
                )
            await session.commit()

        else:
            # New user — check user count and activation code
            count_r = await session.execute(text("SELECT COUNT(*) FROM users"))
            user_count = count_r.scalar() or 0

            code_row = None
            if user_count > 0:
                if not body.activation_code:
                    raise HTTPException(400, "activation_code_required_for_new_user")
                code_r = await session.execute(
                    text("SELECT id, is_used, expires_at FROM activation_codes WHERE code = :code"),
                    {"code": body.activation_code.strip().upper()}
                )
                code_row = code_r.fetchone()
                if not code_row:
                    raise HTTPException(400, "invalid_activation_code")
                if code_row.is_used:
                    raise HTTPException(400, "activation_code_already_used")

            # Create new user + tenant
            user_id = str(uuid.uuid4())
            tenant_id = str(uuid.uuid4())
            tenant_slug = email.split("@")[0] + "-" + user_id[:8]
            role = "owner" if user_count == 0 else "member"

            await session.execute(
                text("INSERT INTO tenants (id, name, slug) VALUES (:tid, :n, :s)"),
                {"tid": tenant_id, "n": name or email, "s": tenant_slug}
            )
            await session.execute(
                text("""
                    INSERT INTO users (id, tenant_id, email, full_name, role, email_verified, avatar_url, activation_code_used, username)
                    VALUES (:uid, :tid, :email, :name, :role, TRUE, :avatar, :code, :uname)
                """),
                {
                    "uid": user_id, "tid": tenant_id, "email": email, "name": name,
                    "role": role, "avatar": avatar_url,
                    "code": body.activation_code, "uname": email.split("@")[0],
                }
            )
            await session.execute(
                text("INSERT INTO user_settings (user_id) VALUES (:uid) ON CONFLICT DO NOTHING"),
                {"uid": user_id}
            )

            if code_row:
                from datetime import datetime, timezone
                await session.execute(
                    text("UPDATE activation_codes SET is_used = TRUE, used_by = :uid, used_at = NOW() WHERE id = :cid"),
                    {"uid": user_id, "cid": code_row.id}
                )

            await session.commit()

    token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        email=email,
        role=role,
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
        "email": email,
        "role": role,
        "provider": provider,
        "new_user": not bool(existing),
    }
