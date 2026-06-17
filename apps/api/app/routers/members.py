from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.members")
router = APIRouter()

TIER_THRESHOLDS = [(10000, "Platinum"), (5000, "Gold"), (1000, "Silver"), (0, "Bronze")]

def _tier(xp: int) -> str:
    for threshold, name in TIER_THRESHOLDS:
        if xp >= threshold:
            return name
    return "Bronze"


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
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("""
                SELECT u.id, u.email, u.full_name, u.role, u.telegram_user_id,
                    u.onboarding_completed, u.created_at,
                    COALESCE(u.global_xp, 0) AS xp,
                    COALESCE(u.global_streak, 0) AS streak,
                    COUNT(t.id) FILTER (WHERE t.assignee_id = u.id) AS tasks_assigned,
                    COUNT(t.id) FILTER (WHERE t.assignee_id = u.id AND t.status = 'completed') AS tasks_completed
                FROM users u
                LEFT JOIN tasks t ON t.tenant_id = u.tenant_id
                WHERE u.tenant_id = :tid
                GROUP BY u.id
                ORDER BY u.global_xp DESC NULLS LAST, u.created_at DESC
            """),
            {"tid": str(user.tenant_id)},
        )
        return [
            {
                "id": str(r.id), "email": r.email, "full_name": r.full_name, "role": r.role,
                "telegram_user_id": r.telegram_user_id, "onboarding_completed": r.onboarding_completed,
                "tasks_assigned": r.tasks_assigned or 0, "tasks_completed": r.tasks_completed or 0,
                "xp": r.xp or 0, "tier": _tier(r.xp or 0), "streak": r.streak or 0,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.fetchall()
        ]


@router.get("/leaderboard")
async def get_leaderboard(request: Request, limit: int = 20) -> list[dict]:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("""
                SELECT u.id AS user_id, u.full_name, u.email,
                    COALESCE(u.global_xp, 0) AS xp,
                    COALESCE(u.global_streak, 0) AS streak,
                    COUNT(t.id) FILTER (WHERE t.assignee_id = u.id AND t.status = 'completed') AS completed_count,
                    RANK() OVER (ORDER BY COALESCE(u.global_xp, 0) DESC) AS rank
                FROM users u
                LEFT JOIN tasks t ON t.assignee_id = u.id AND t.tenant_id = :tid
                WHERE u.tenant_id = :tid
                GROUP BY u.id, u.full_name, u.email, u.global_xp, u.global_streak
                ORDER BY xp DESC
                LIMIT :limit
            """),
            {"tid": str(user.tenant_id), "limit": limit},
        )
        return [
            {
                "user_id": str(r.user_id), "full_name": r.full_name, "email": r.email,
                "xp": r.xp or 0, "tier": _tier(r.xp or 0), "streak": r.streak or 0,
                "completed_count": r.completed_count or 0, "rank": r.rank,
            }
            for r in result.fetchall()
        ]


@router.get("/{user_id}")
async def get_member(user_id: UUID, request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("""
                SELECT u.id, u.email, u.full_name, u.role, u.telegram_user_id,
                    u.onboarding_completed, u.created_at,
                    COALESCE(u.global_xp, 0) AS xp,
                    COALESCE(u.global_streak, 0) AS streak,
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
            "id": str(row.id), "email": row.email, "full_name": row.full_name, "role": row.role,
            "telegram_user_id": row.telegram_user_id, "onboarding_completed": row.onboarding_completed,
            "tasks_assigned": row.tasks_assigned or 0, "tasks_completed": row.tasks_completed or 0,
            "xp": row.xp or 0, "tier": _tier(row.xp or 0), "streak": row.streak or 0,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }


@router.patch("/{user_id}")
async def update_member(user_id: UUID, body: UpdateMemberRequest, request: Request) -> dict:
    user = await _auth(request)
    from apps.api.app.middleware.auth import require_admin
    await require_admin(user)
    if body.role not in ("manager", "member", "owner"):
        raise HTTPException(status_code=400, detail="invalid_role")
    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("""
                UPDATE users SET role = :role, updated_at = NOW()
                WHERE id = :uid AND tenant_id = :tid
                RETURNING id, email, full_name, role, COALESCE(global_xp, 0) AS xp
            """),
            {"role": body.role, "uid": str(user_id), "tid": str(user.tenant_id)},
        )
        row = result.fetchone()
        await session.commit()
        if not row:
            raise HTTPException(status_code=404, detail="member_not_found")
        return {
            "id": str(row.id), "email": row.email, "full_name": row.full_name, "role": row.role,
            "xp": row.xp or 0, "tier": _tier(row.xp or 0),
            "telegram_user_id": None, "onboarding_completed": False,
            "tasks_assigned": 0, "tasks_completed": 0, "streak": 0, "created_at": None,
        }


@router.delete("/{user_id}", status_code=204)
async def delete_member(user_id: UUID, request: Request):
    user = await _auth(request)
    from apps.api.app.middleware.auth import require_admin
    await require_admin(user)
    db = request.app.state.db
    async with db() as session:
        await session.execute(
            text("DELETE FROM users WHERE id = :uid AND tenant_id = :tid"),
            {"uid": str(user_id), "tid": str(user.tenant_id)},
        )
        await session.commit()


@router.post("/invite", status_code=201)
async def invite_member(body: InviteMemberRequest, request: Request) -> dict:
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
