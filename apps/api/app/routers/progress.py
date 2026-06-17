from __future__ import annotations

import logging
import uuid
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.progress")

router = APIRouter()


class ProgressInput(BaseModel):
    task_id: str
    note: str | None = None
    percent_complete: int | None = None


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


@router.get("/")
async def list_progress_logs(
    request: Request,
    task_id: str | None = None,
    user_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """List progress/completion logs for tenant."""
    user = await _auth(request)
    db = request.app.state.db

    conditions = ["t.tenant_id = :tid"]
    params: dict = {"tid": str(user.tenant_id), "limit": limit}

    if task_id:
        conditions.append("tc.task_id = :task_id")
        params["task_id"] = task_id
    if user_id:
        conditions.append("tc.user_id = :user_id")
        params["user_id"] = user_id

    where = " AND ".join(conditions)

    async with db() as session:
        result = await session.execute(
            text(f"""
                SELECT tc.id, tc.task_id, t.title AS task_title,
                       tc.user_id, u.full_name AS user_name,
                       NULL AS note, NULL AS percent_complete,
                       tc.completed_at AS created_at
                FROM task_completions tc
                JOIN tasks t ON t.id = tc.task_id
                JOIN users u ON u.id = tc.user_id
                WHERE {where}
                ORDER BY tc.completed_at DESC
                LIMIT :limit
            """),
            params,
        )
        return [
            {
                "id": str(r.id),
                "task_id": str(r.task_id),
                "task_title": r.task_title,
                "user_id": str(r.user_id),
                "user_name": r.user_name,
                "note": r.note,
                "percent_complete": r.percent_complete,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in result.fetchall()
        ]


@router.post("/", status_code=201)
async def log_progress(body: ProgressInput, request: Request) -> dict:
    """Log task progress or mark as complete."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        # Check task exists in tenant
        r = await session.execute(
            text("SELECT id, project_id FROM tasks WHERE id = :tid AND tenant_id = :ten_id AND archived_at IS NULL"),
            {"tid": body.task_id, "ten_id": str(user.tenant_id)},
        )
        task_row = r.fetchone()
        if not task_row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="task_not_found")

        # Get or create account slot (required by DB constraint)
        slot_r = await session.execute(
            text("""
                SELECT id FROM account_slots
                WHERE user_id = :uid AND project_id = :pid AND slot_name = 'WEB'
            """),
            {"uid": str(user.user_id), "pid": str(task_row.project_id)},
        )
        slot_row = slot_r.fetchone()
        if not slot_row:
            slot_id = str(uuid.uuid4())
            await session.execute(
                text("""
                    INSERT INTO account_slots (id, user_id, project_id, slot_name)
                    VALUES (:id, :uid, :pid, 'WEB')
                """),
                {"id": slot_id, "uid": str(user.user_id), "pid": str(task_row.project_id)},
            )
        else:
            slot_id = str(slot_row.id)

        tc_id = str(uuid.uuid4())
        await session.execute(
            text("""
                INSERT INTO task_completions (id, task_id, user_id, account_slot_id, submitted_via, proof_url)
                VALUES (:id, :task_id, :user_id, :slot_id, 'web', :note)
                ON CONFLICT (task_id, account_slot_id) DO NOTHING
            """),
            {
                "id": tc_id,
                "task_id": body.task_id,
                "user_id": str(user.user_id),
                "slot_id": slot_id,
                "note": body.note or None,
            },
        )

        # If 100% complete, mark task as completed
        if body.percent_complete is not None and body.percent_complete >= 100:
            await session.execute(
                text("UPDATE tasks SET status = 'completed', updated_at = NOW() WHERE id = :tid"),
                {"tid": body.task_id},
            )

        await session.commit()

    return {
        "id": tc_id,
        "task_id": body.task_id,
        "task_title": None,
        "user_id": str(user.user_id),
        "user_name": None,
        "note": body.note,
        "percent_complete": body.percent_complete,
        "created_at": None,
    }


@router.get("/me")
async def my_progress(request: Request, project_id: UUID | None = None) -> dict:
    """Get current user's progress summary."""
    user = await _auth(request)
    db = request.app.state.db
    today = date.today()

    async with db() as session:
        where_extra = "AND t.project_id = :pid" if project_id else ""
        params: dict = {"uid": str(user.user_id), "today": today}
        if project_id:
            params["pid"] = str(project_id)

        result = await session.execute(
            text(f"""
                SELECT
                    COUNT(DISTINCT tc.id) AS total_completions,
                    COALESCE(SUM(tc.points_earned), 0) AS total_points,
                    COUNT(DISTINCT tc.id) FILTER (WHERE DATE(tc.completed_at) = :today) AS today_completions,
                    COUNT(DISTINCT t.id) AS total_tasks
                FROM tasks t
                JOIN project_members pm ON pm.project_id = t.project_id AND pm.user_id = :uid
                LEFT JOIN task_completions tc ON tc.task_id = t.id AND tc.user_id = :uid
                WHERE t.archived_at IS NULL {where_extra}
            """),
            params,
        )
        row = result.fetchone()

    return {
        "total_completions": row.total_completions if row else 0,
        "total_points": int(row.total_points) if row else 0,
        "today_completions": row.today_completions if row else 0,
        "total_tasks": row.total_tasks if row else 0,
        "completion_rate": round((row.total_completions / max(row.total_tasks, 1)) * 100, 1) if row else 0,
    }


# ── Account Slots ─────────────────────────────────────────────────────────────

class SlotCreate(BaseModel):
    project_id: str
    slot_name: str
    wallet_address: str | None = None
    twitter_username: str | None = None
    discord_username: str | None = None


class SlotUpdate(BaseModel):
    slot_name: str | None = None
    wallet_address: str | None = None
    twitter_username: str | None = None
    discord_username: str | None = None


@router.get("/slots")
async def list_slots(request: Request, project_id: str | None = None) -> list[dict]:
    """List the current user's account slots, optionally filtered by project."""
    user = await _auth(request)
    db = request.app.state.db
    params: dict = {"uid": str(user.user_id)}
    where_extra = ""
    if project_id:
        where_extra = "AND asl.project_id = :pid"
        params["pid"] = project_id

    async with db() as session:
        r = await session.execute(
            text(f"""
                SELECT asl.id, asl.project_id, asl.slot_name,
                       asl.wallet_address, asl.twitter_username, asl.discord_username,
                       asl.created_at, asl.updated_at,
                       p.name AS project_name,
                       COUNT(DISTINCT tc.id) AS completions
                FROM account_slots asl
                JOIN projects p ON p.id = asl.project_id
                LEFT JOIN task_completions tc ON tc.account_slot_id = asl.id
                WHERE asl.user_id = :uid {where_extra}
                GROUP BY asl.id, p.name
                ORDER BY p.name, asl.slot_name
            """),
            params,
        )
        rows = r.mappings().fetchall()
    return [
        {
            "id": str(row["id"]),
            "project_id": str(row["project_id"]),
            "project_name": row["project_name"],
            "slot_name": row["slot_name"],
            "wallet_address": row["wallet_address"],
            "twitter_username": row["twitter_username"],
            "discord_username": row["discord_username"],
            "completions": int(row["completions"] or 0),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]


@router.post("/slots", status_code=201)
async def create_slot(body: SlotCreate, request: Request) -> dict:
    """Create a new account slot for a project."""
    user = await _auth(request)
    db = request.app.state.db
    slot_id = str(uuid.uuid4())
    async with db() as session:
        # Verify project exists in tenant
        r = await session.execute(
            text("SELECT id FROM projects WHERE id = :pid AND tenant_id = :tid"),
            {"pid": body.project_id, "tid": str(user.tenant_id)},
        )
        if not r.fetchone():
            from fastapi import HTTPException
            raise HTTPException(404, "project_not_found")

        # Check slot_name is not duplicate for user+project
        r2 = await session.execute(
            text("SELECT id FROM account_slots WHERE user_id = :uid AND project_id = :pid AND slot_name = :name"),
            {"uid": str(user.user_id), "pid": body.project_id, "name": body.slot_name},
        )
        if r2.fetchone():
            from fastapi import HTTPException
            raise HTTPException(409, "slot_name_exists")

        await session.execute(
            text("""
                INSERT INTO account_slots (id, user_id, project_id, slot_name, wallet_address, twitter_username, discord_username)
                VALUES (:id, :uid, :pid, :name, :wallet, :twitter, :discord)
            """),
            {
                "id": slot_id,
                "uid": str(user.user_id),
                "pid": body.project_id,
                "name": body.slot_name,
                "wallet": body.wallet_address,
                "twitter": body.twitter_username,
                "discord": body.discord_username,
            },
        )
        await session.commit()
    return {"id": slot_id, "slot_name": body.slot_name, "project_id": body.project_id}


@router.patch("/slots/{slot_id}")
async def update_slot(slot_id: str, body: SlotUpdate, request: Request) -> dict:
    """Update an account slot."""
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("SELECT id FROM account_slots WHERE id = :sid AND user_id = :uid"),
            {"sid": slot_id, "uid": str(user.user_id)},
        )
        if not r.fetchone():
            from fastapi import HTTPException
            raise HTTPException(404, "slot_not_found")

        fields = {k: v for k, v in body.model_dump().items() if v is not None}
        if not fields:
            return {"updated": False}
        set_clause = ", ".join(f"{k} = :{k}" for k in fields)
        fields["sid"] = slot_id
        await session.execute(
            text(f"UPDATE account_slots SET {set_clause}, updated_at = NOW() WHERE id = :sid"),
            fields,
        )
        await session.commit()
    return {"updated": True}


@router.delete("/slots/{slot_id}", status_code=204)
async def delete_slot(slot_id: str, request: Request) -> None:
    """Delete an account slot (also cascades completions)."""
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("SELECT id FROM account_slots WHERE id = :sid AND user_id = :uid"),
            {"sid": slot_id, "uid": str(user.user_id)},
        )
        if not r.fetchone():
            from fastapi import HTTPException
            raise HTTPException(404, "slot_not_found")
        await session.execute(text("DELETE FROM account_slots WHERE id = :sid"), {"sid": slot_id})
        await session.commit()
