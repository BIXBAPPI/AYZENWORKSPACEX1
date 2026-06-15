from __future__ import annotations

import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.broadcasts")

router = APIRouter()


class BroadcastInput(BaseModel):
    message: str
    target_role: str | None = None


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


async def _auth_admin(request: Request):
    from apps.api.app.middleware.auth import verify_token, require_admin
    user = await verify_token(request)
    await require_admin(user)
    return user


@router.get("/")
async def list_broadcasts(request: Request) -> list[dict]:
    """List broadcasts for tenant."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        result = await session.execute(
            text("""
                SELECT b.id, b.message, b.sent_count, b.failed_count,
                       b.sender_id AS created_by, b.created_at
                FROM bot_broadcasts b
                WHERE b.tenant_id = :tid
                ORDER BY b.created_at DESC
                LIMIT 50
            """),
            {"tid": str(user.tenant_id)},
        )
        return [
            {
                "id": str(r.id),
                "message": r.message,
                "sent_count": r.sent_count,
                "failed_count": r.failed_count,
                "created_by": str(r.created_by) if r.created_by else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.fetchall()
        ]


@router.post("/", status_code=201)
async def create_broadcast(body: BroadcastInput, request: Request) -> dict:
    """Queue a broadcast message. Sends via Telegram if bot is configured."""
    user = await _auth_admin(request)
    db = request.app.state.db

    broadcast_id = str(uuid.uuid4())

    async with db() as session:
        # Count eligible recipients
        conditions = ["u.tenant_id = :tid", "u.telegram_user_id IS NOT NULL"]
        params: dict = {"tid": str(user.tenant_id)}
        if body.target_role:
            conditions.append("u.role = :role")
            params["role"] = body.target_role

        where = " AND ".join(conditions)
        r = await session.execute(
            text(f"SELECT COUNT(*) AS cnt FROM users u WHERE {where}"),
            params,
        )
        target_count = r.scalar() or 0

        await session.execute(
            text("""
                INSERT INTO bot_broadcasts (id, tenant_id, sender_id, message, target_count, status)
                VALUES (:id, :tid, :sender_id, :message, :target_count, 'pending')
            """),
            {
                "id": broadcast_id,
                "tid": str(user.tenant_id),
                "sender_id": str(user.user_id),
                "message": body.message,
                "target_count": target_count,
            },
        )
        await session.commit()

    # Try to send via Telegram bot if configured
    sent_count = 0
    failed_count = 0
    try:
        from apps.api.app.integrations.telegram.client import get_telegram_client
        from apps.api.app.services.broadcast_service import BroadcastService
        client = get_telegram_client()
        svc = BroadcastService(db, client)

        # Get first project for tenant (backward compat with BroadcastService)
        async with db() as session:
            r = await session.execute(
                text("SELECT id FROM projects WHERE tenant_id = :tid AND deleted_at IS NULL LIMIT 1"),
                {"tid": str(user.tenant_id)},
            )
            proj = r.fetchone()

        if proj:
            sent_count = await svc.send_project_broadcast(
                project_id=proj.id,
                tenant_id=user.tenant_id,
                sender_id=user.user_id,
                message=body.message,
            )
    except Exception as exc:
        logger.warning("Telegram broadcast failed: %s", exc)

    # Update broadcast record
    async with db() as session:
        await session.execute(
            text("""
                UPDATE bot_broadcasts
                SET sent_count = :sent, failed_count = :failed, status = 'completed', completed_at = NOW()
                WHERE id = :id
            """),
            {"sent": sent_count, "failed": failed_count, "id": broadcast_id},
        )
        await session.commit()

    return {
        "id": broadcast_id,
        "message": body.message,
        "sent_count": sent_count,
        "failed_count": failed_count,
        "created_by": str(user.user_id),
        "created_at": None,
    }
