from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.notifications")

router = APIRouter()


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


@router.get("/")
async def list_notifications(request: Request, unread_only: bool = False) -> list[dict]:
    """List notifications for current user."""
    user = await _auth(request)
    db = request.app.state.db

    conditions = ["n.user_id = :uid"]
    params: dict = {"uid": str(user.user_id)}
    if unread_only:
        conditions.append("n.read = FALSE")
    where = " AND ".join(conditions)

    async with db() as session:
        result = await session.execute(
            text(f"""
                SELECT n.id, n.type, n.message, n.read, n.task_id, n.created_at
                FROM notifications n
                WHERE {where}
                ORDER BY n.created_at DESC
                LIMIT 100
            """),
            params,
        )
        return [
            {
                "id": str(r.id),
                "type": r.type,
                "message": r.message,
                "read": r.read,
                "task_id": str(r.task_id) if r.task_id else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.fetchall()
        ]


@router.patch("/{notification_id}/read")
async def mark_notification_read(notification_id: UUID, request: Request) -> dict:
    """Mark a notification as read."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        result = await session.execute(
            text("""
                UPDATE notifications
                SET read = TRUE
                WHERE id = :nid AND user_id = :uid
                RETURNING id, type, message, read, task_id, created_at
            """),
            {"nid": str(notification_id), "uid": str(user.user_id)},
        )
        row = result.fetchone()
        await session.commit()

        if not row:
            raise HTTPException(status_code=404, detail="notification_not_found")

        return {
            "id": str(row.id),
            "type": row.type,
            "message": row.message,
            "read": row.read,
            "task_id": str(row.task_id) if row.task_id else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }


@router.get("/settings")
async def get_notification_settings(request: Request) -> dict:
    """Get notification preferences."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        result = await session.execute(
            text("""
                SELECT notify_deadline, notify_assignment, notify_broadcast,
                       quiet_hours_start, quiet_hours_end
                FROM user_settings WHERE user_id = :uid
            """),
            {"uid": str(user.user_id)},
        )
        row = result.fetchone()
        if not row:
            return {"notify_deadline": True, "notify_assignment": True, "notify_broadcast": True}
        return dict(row._mapping)


@router.post("/send")
async def send_notification_to_user(request: Request) -> dict:
    """Send a Telegram notification to a user."""
    user = await _auth(request)
    return {"status": "not_configured"}
