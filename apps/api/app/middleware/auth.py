from __future__ import annotations

import logging
import os
import time
from typing import Any
from uuid import UUID

import jwt
from fastapi import HTTPException, Request, status

logger = logging.getLogger("ayzen.auth")

_JWT_SECRET = os.environ.get("SESSION_SECRET", "changeme-set-session-secret")
_JWT_ALGORITHM = "HS256"


class AuthUser:
    __slots__ = ("user_id", "tenant_id", "email", "role")

    def __init__(self, user_id: str, tenant_id: str, email: str, role: str) -> None:
        self.user_id = UUID(user_id)
        self.tenant_id = UUID(tenant_id)
        self.email = email
        self.role = role


async def verify_token(request: Request) -> AuthUser:
    """Validate JWT from HttpOnly cookie or Authorization header (self-hosted, SESSION_SECRET)."""
    token: str | None = request.cookies.get("ayzen-token")

    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")

    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        email = payload.get("email", "")
        role = payload.get("role", "member")

        if not user_id or not tenant_id:
            raise ValueError("Missing sub or tenant_id")

        return AuthUser(user_id=str(user_id), tenant_id=str(tenant_id), email=email, role=role)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token_invalid")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Auth error: %s", exc)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="auth_error")


async def require_admin(user: AuthUser) -> AuthUser:
    if user.role not in ("owner", "manager"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    return user


async def optional_auth(request: Request) -> AuthUser | None:
    try:
        return await verify_token(request)
    except HTTPException:
        return None


async def set_tenant_context(session: Any, tenant_id: UUID) -> None:
    await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")


def create_access_token(user_id: str, tenant_id: str, email: str, role: str, expires_in: int = 86400) -> str:
    """Create a signed JWT. expires_in in seconds (default 24h)."""
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "email": email,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + expires_in,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)
