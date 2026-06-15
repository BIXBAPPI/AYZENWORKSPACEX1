from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.settings")

router = APIRouter()


class UserSettingsUpdate(BaseModel):
    language: str | None = None
    quiet_start: str | None = None
    quiet_end: str | None = None
    notify_deadline: bool | None = None
    notify_assignments: bool | None = None


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


@router.get("/")
async def get_settings(request: Request) -> dict:
    """Get user settings."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        result = await session.execute(
            text("""
                SELECT locale, notify_deadline, notify_assignment,
                       quiet_hours_start, quiet_hours_end
                FROM user_settings
                WHERE user_id = :uid
            """),
            {"uid": str(user.user_id)},
        )
        row = result.fetchone()
        if not row:
            return {
                "user_id": str(user.user_id),
                "language": "en",
                "notify_deadline": True,
                "notify_assignments": True,
                "quiet_start": None,
                "quiet_end": None,
            }
        return {
            "user_id": str(user.user_id),
            "language": row.locale or "en",
            "notify_deadline": row.notify_deadline,
            "notify_assignments": row.notify_assignment,
            "quiet_start": str(row.quiet_hours_start) if row.quiet_hours_start else None,
            "quiet_end": str(row.quiet_hours_end) if row.quiet_hours_end else None,
        }


@router.patch("/")
async def update_settings(body: UserSettingsUpdate, request: Request) -> dict:
    """Update user settings."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        # Upsert settings row
        await session.execute(
            text("""
                INSERT INTO user_settings (user_id) VALUES (:uid)
                ON CONFLICT (user_id) DO NOTHING
            """),
            {"uid": str(user.user_id)},
        )

        updates: dict = {}
        if body.language is not None:
            updates["locale"] = body.language
        if body.quiet_start is not None:
            updates["quiet_hours_start"] = body.quiet_start
        if body.quiet_end is not None:
            updates["quiet_hours_end"] = body.quiet_end
        if body.notify_deadline is not None:
            updates["notify_deadline"] = body.notify_deadline
        if body.notify_assignments is not None:
            updates["notify_assignment"] = body.notify_assignments

        if updates:
            set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
            updates["uid"] = str(user.user_id)
            await session.execute(
                text(f"UPDATE user_settings SET {set_clauses}, updated_at = NOW() WHERE user_id = :uid"),
                updates,
            )

        await session.commit()

    return {
        "user_id": str(user.user_id),
        "language": body.language or "en",
        "notify_deadline": body.notify_deadline if body.notify_deadline is not None else True,
        "notify_assignments": body.notify_assignments if body.notify_assignments is not None else True,
        "quiet_start": body.quiet_start,
        "quiet_end": body.quiet_end,
    }


@router.delete("/bot-link")
async def unlink_bot(request: Request) -> dict:
    """Unlink Telegram bot account."""
    user = await _auth(request)
    db = request.app.state.db
    redis = request.app.state.redis

    from apps.api.app.services.bot_user_service import BotUserService
    svc = BotUserService(redis, db)
    await svc.unlink(user.user_id)
    return {"status": "unlinked"}
