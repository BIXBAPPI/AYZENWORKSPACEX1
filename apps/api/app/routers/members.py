from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.members")

router = APIRouter()


class InviteMemberRequest(BaseModel):
    project_id: UUID
    email: EmailStr
    role: str = "member"


class UpdateMemberRequest(BaseModel):
    role: str


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


@router.get("/")
async def list_members(request: Request) -> list[dict]:
    """List all members in tenant."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        result = await session.execute(
            text("""
                SELECT
                    u.id, u.email, u.full_name, u.role, u.telegram_user_id,
                    u.onboarding_completed, u.created_at,
                    COUNT(t.id) FILTER (WHERE t.assignee_id = u.id) AS tasks_assigned,
                    COUNT(t.id) FILTER (WHERE t.assignee_id = u.id AND t.status = 'completed') AS tasks_completed
                FROM users u
                LEFT JOIN tasks t ON t.tenant_id = u.tenant_id
                WHERE u.tenant_id = :tid
                GROUP BY u.id
                ORDER BY u.created_at DESC
            """),
            {"tid": str(user.tenant_id)},
        )
        rows = result.fetchall()
        return [
            {
                "id": str(r.id),
                "email": r.email,
                "full_name": r.full_name,
                "role": r.role,
                "telegram_user_id": r.telegram_user_id,
                "onboarding_completed": r.onboarding_completed,
                "tasks_assigned": r.tasks_assigned or 0,
                "tasks_completed": r.tasks_completed or 0,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


@router.get("/leaderboard")
async def get_leaderboard(request: Request, limit: int = 10) -> list[dict]:
    """Top members by completed task count in tenant."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        result = await session.execute(
            text("""
                SELECT
                    u.id AS user_id, u.full_name, u.email,
                    COUNT(t.id) FILTER (WHERE t.status = 'completed') AS completed_count,
                    RANK() OVER (ORDER BY COUNT(t.id) FILTER (WHERE t.status = 'completed') DESC) AS rank
                FROM users u
                LEFT JOIN tasks t ON t.assignee_id = u.id AND t.tenant_id = :tid
                WHERE u.tenant_id = :tid
                GROUP BY u.id, u.full_name, u.email
                ORDER BY completed_count DESC
                LIMIT :limit
            """),
            {"tid": str(user.tenant_id), "limit": limit},
        )
        return [
            {
                "user_id": str(r.user_id),
                "full_name": r.full_name,
                "email": r.email,
                "completed_count": r.completed_count or 0,
                "rank": r.rank,
            }
            for r in result.fetchall()
        ]


@router.get("/{user_id}")
async def get_member(user_id: UUID, request: Request) -> dict:
    """Get single member details."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        result = await session.execute(
            text("""
                SELECT
                    u.id, u.email, u.full_name, u.role, u.telegram_user_id,
                    u.onboarding_completed, u.created_at,
                    COUNT(t.id) FILTER (WHERE t.assignee_id = u.id) AS tasks_assigned,
                    COUNT(t.id) FILTER (WHERE t.assignee_id = u.id AND t.status = 'completed') AS tasks_completed
                FROM users u
                LEFT JOIN tasks t ON t.tenant_id = u.tenant_id
                WHERE u.id = :uid AND u.tenant_id = :tid
                GROUP BY u.id
            """),
            {"uid": str(user_id), "tid": str(user.tenant_id)},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="member_not_found")
        return {
            "id": str(row.id),
            "email": row.email,
            "full_name": row.full_name,
            "role": row.role,
            "telegram_user_id": row.telegram_user_id,
            "onboarding_completed": row.onboarding_completed,
            "tasks_assigned": row.tasks_assigned or 0,
            "tasks_completed": row.tasks_completed or 0,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }


@router.patch("/{user_id}")
async def update_member(user_id: UUID, body: UpdateMemberRequest, request: Request) -> dict:
    """Update member role (admin only)."""
    user = await _auth(request)
    from apps.api.app.middleware.auth import require_admin
    await require_admin(user)

    if body.role not in ("manager", "member"):
        raise HTTPException(status_code=400, detail="invalid_role")

    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("""
                UPDATE users SET role = :role, updated_at = NOW()
                WHERE id = :uid AND tenant_id = :tid
                RETURNING id, email, full_name, role
            """),
            {"role": body.role, "uid": str(user_id), "tid": str(user.tenant_id)},
        )
        row = result.fetchone()
        await session.commit()
        if not row:
            raise HTTPException(status_code=404, detail="member_not_found")
        return {"id": str(row.id), "email": row.email, "full_name": row.full_name, "role": row.role,
                "telegram_user_id": None, "onboarding_completed": False,
                "tasks_assigned": 0, "tasks_completed": 0, "created_at": None}


@router.post("/invite", status_code=201)
async def invite_member(body: InviteMemberRequest, request: Request) -> dict:
    """Invite user to project by email."""
    user = await _auth(request)
    from apps.api.app.middleware.auth import require_admin
    await require_admin(user)

    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("SELECT id FROM users WHERE email = :email AND tenant_id = :tid"),
            {"email": body.email, "tid": str(user.tenant_id)},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="user_not_found")

        await session.execute(
            text("""
                INSERT INTO project_members (project_id, user_id, role, assigned_by)
                VALUES (:pid, :uid, :role, :assigned_by)
                ON CONFLICT (project_id, user_id) DO UPDATE SET role = EXCLUDED.role
            """),
            {"pid": str(body.project_id), "uid": str(row.id), "role": body.role, "assigned_by": str(user.user_id)},
        )
        await session.commit()

    return {"status": "invited", "email": body.email, "role": body.role}
