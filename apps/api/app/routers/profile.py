"""User Profile — public and private profiles."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.profile")
router = APIRouter()


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


TIER_THRESHOLDS = [(20000, "Platinum"), (5000, "Gold"), (1000, "Silver"), (0, "Bronze")]

def _tier(xp: int) -> str:
    for threshold, name in TIER_THRESHOLDS:
        if xp >= threshold:
            return name
    return "Bronze"


class ProfileUpdate(BaseModel):
    bio: str | None = None
    avatar_url: str | None = None
    twitter_handle: str | None = None
    discord_handle: str | None = None
    telegram_handle: str | None = None
    github_handle: str | None = None
    username: str | None = None


def _row_to_profile(row, public: bool = False) -> dict:
    xp = row.get("global_xp") or 0
    return {
        "id": str(row["id"]),
        "username": row.get("username") or row.get("full_name") or row.get("email", "").split("@")[0],
        "email": None if public else row.get("email"),
        "full_name": row.get("full_name"),
        "role": row.get("role"),
        "xp": xp,
        "tier": _tier(xp),
        "streak": row.get("global_streak") or 0,
        "bio": row.get("bio"),
        "avatar_url": row.get("avatar_url"),
        "twitter_handle": row.get("twitter_handle"),
        "discord_handle": row.get("discord_handle"),
        "telegram_handle": row.get("telegram_handle"),
        "github_handle": row.get("github_handle"),
        "wallet_address": None if public else row.get("wallet_address"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "two_fa_enabled": row.get("two_fa_enabled", False),
    }


@router.get("/me")
async def get_my_profile(request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("""
                SELECT id, email, full_name, role, global_xp, global_streak, created_at,
                       bio, avatar_url, twitter_handle, discord_handle, telegram_handle,
                       github_handle, wallet_address, two_fa_enabled, username
                FROM users WHERE id = :uid
            """),
            {"uid": str(user.user_id)}
        )
        row = r.mappings().fetchone()
        if not row:
            raise HTTPException(404, "user_not_found")
        return _row_to_profile(dict(row), public=False)


@router.patch("/me")
async def update_my_profile(body: ProfileUpdate, request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        return {"updated": False}
    set_clause = ", ".join(f"{k} = :{k}" for k in fields)
    fields["uid"] = str(user.user_id)
    async with db() as session:
        await session.execute(
            text(f"UPDATE users SET {set_clause} WHERE id = :uid"),
            fields
        )
        await session.commit()
        return {"updated": True}


@router.get("/{username}")
async def get_public_profile(username: str, request: Request) -> dict:
    await _auth(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("""
                SELECT id, full_name, role, global_xp, global_streak, created_at,
                       bio, avatar_url, twitter_handle, discord_handle, telegram_handle,
                       github_handle, two_fa_enabled, username, email
                FROM users
                WHERE username = :uname OR full_name = :uname
                LIMIT 1
            """),
            {"uname": username}
        )
        row = r.mappings().fetchone()
        if not row:
            raise HTTPException(404, "user_not_found")
        return _row_to_profile(dict(row), public=True)
