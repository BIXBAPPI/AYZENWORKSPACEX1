from __future__ import annotations

import logging
import uuid

import bcrypt
from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.auth")

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LinkCodeResponse(BaseModel):
    code: str
    expires_in: int


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, request: Request) -> dict:
    """Register new user with local bcrypt auth. Creates user + default tenant."""
    db = request.app.state.db
    async with db() as session:
        existing = await session.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": body.email},
        )
        if existing.fetchone():
            raise HTTPException(status_code=400, detail="email_already_registered")

        user_id = str(uuid.uuid4())
        tenant_id = str(uuid.uuid4())
        tenant_slug = f"{body.email.split('@')[0].lower().replace('.', '-')[:40]}-{user_id[:8]}"
        pwd_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

        await session.execute(
            text("INSERT INTO tenants (id, name, slug) VALUES (:tid, :name, :slug)"),
            {"tid": tenant_id, "name": body.full_name or body.email, "slug": tenant_slug},
        )
        await session.execute(
            text("""
                INSERT INTO users (id, tenant_id, email, full_name, role, password_hash)
                VALUES (:uid, :tid, :email, :name, 'owner', :pwd)
            """),
            {"uid": user_id, "tid": tenant_id, "email": body.email, "name": body.full_name, "pwd": pwd_hash},
        )
        await session.commit()

    return {"status": "registered", "email": body.email}


@router.post("/login")
async def login(body: LoginRequest, response: Response, request: Request) -> dict:
    """Login with email+password, set HttpOnly cookie."""
    from apps.api.app.middleware.auth import create_access_token

    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("SELECT id, tenant_id, role, password_hash FROM users WHERE email = :email"),
            {"email": body.email},
        )
        row = result.fetchone()

    if not row or not row.password_hash:
        raise HTTPException(status_code=401, detail="invalid_credentials")

    if not bcrypt.checkpw(body.password.encode(), row.password_hash.encode()):
        raise HTTPException(status_code=401, detail="invalid_credentials")

    token = create_access_token(
        user_id=str(row.id),
        tenant_id=str(row.tenant_id),
        email=body.email,
        role=row.role,
    )
    response.set_cookie(
        "ayzen-token", token,
        httponly=True, secure=True, samesite="none", max_age=86400, path="/",
    )
    return {"status": "logged_in", "role": row.role}


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie("ayzen-token", path="/")
    return {"status": "logged_out"}


@router.get("/me")
async def me(request: Request) -> dict:
    from apps.api.app.middleware.auth import verify_token
    user = await verify_token(request)
    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("SELECT full_name, onboarding_completed FROM users WHERE id = :uid"),
            {"uid": str(user.user_id)},
        )
        row = result.fetchone()
    return {
        "user_id": str(user.user_id),
        "email": user.email,
        "role": user.role,
        "tenant_id": str(user.tenant_id),
        "full_name": row.full_name if row else None,
        "onboarding_completed": row.onboarding_completed if row else False,
    }


@router.post("/bot-link-code", response_model=LinkCodeResponse)
async def generate_link_code(request: Request) -> LinkCodeResponse:
    from apps.api.app.middleware.auth import verify_token
    from apps.api.app.services.bot_user_service import BotUserService

    user = await verify_token(request)
    redis = request.app.state.redis
    db = request.app.state.db
    svc = BotUserService(redis, db)
    code = await svc.generate_link_code(user.user_id)
    return LinkCodeResponse(code=code, expires_in=600)
