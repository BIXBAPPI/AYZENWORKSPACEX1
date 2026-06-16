from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.tasks")

router = APIRouter()


class CreateTaskRequest(BaseModel):
    title: str
    description: str | None = None
    project_id: str | None = None
    assignee_id: str | None = None
    priority: str = "normal"
    deadline: datetime | None = None


class UpdateTaskRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee_id: str | None = None
    deadline: datetime | None = None


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


def _task_row_to_dict(r) -> dict:
    return {
        "id": str(r.id),
        "project_id": str(r.project_id) if r.project_id else None,
        "title": r.title,
        "description": r.description if hasattr(r, "description") else None,
        "status": r.status,
        "priority": r.priority,
        "assignee_id": str(r.assignee_id) if r.assignee_id else None,
        "assignee_name": r.assignee_name if hasattr(r, "assignee_name") else None,
        "project_name": r.project_name if hasattr(r, "project_name") else None,
        "deadline": r.deadline.isoformat() if r.deadline else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


@router.get("/overdue")
async def list_overdue_tasks(request: Request) -> list[dict]:
    """List overdue tasks in tenant."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        result = await session.execute(
            text("""
                SELECT t.id, t.project_id, t.title, t.status, t.priority,
                       t.assignee_id, u.full_name AS assignee_name,
                       p.name AS project_name, t.deadline, t.created_at, t.updated_at
                FROM tasks t
                LEFT JOIN users u ON u.id = t.assignee_id
                LEFT JOIN projects p ON p.id = t.project_id
                WHERE t.tenant_id = :tid
                  AND t.archived_at IS NULL
                  AND t.deadline < NOW()
                  AND t.status NOT IN ('completed', 'cancelled')
                ORDER BY t.deadline ASC
            """),
            {"tid": str(user.tenant_id)},
        )
        rows = result.fetchall()
        return [_task_row_to_dict(r) for r in rows]


@router.get("/")
async def list_tasks(
    request: Request,
    project_id: str | None = None,
    assignee_id: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List tasks in tenant with optional filters."""
    user = await _auth(request)
    db = request.app.state.db

    conditions = ["t.tenant_id = :tid", "t.archived_at IS NULL"]
    params: dict = {"tid": str(user.tenant_id), "limit": limit, "offset": offset}

    if project_id:
        conditions.append("t.project_id = :pid")
        params["pid"] = project_id
    if assignee_id:
        conditions.append("t.assignee_id = :aid")
        params["aid"] = assignee_id
    if status:
        conditions.append("t.status = :status")
        params["status"] = status
    if priority:
        conditions.append("t.priority = :priority")
        params["priority"] = priority

    where_clause = " AND ".join(conditions)

    async with db() as session:
        result = await session.execute(
            text(f"""
                SELECT t.id, t.project_id, t.title, t.status, t.priority,
                       t.assignee_id, u.full_name AS assignee_name,
                       p.name AS project_name, t.deadline, t.created_at, t.updated_at
                FROM tasks t
                LEFT JOIN users u ON u.id = t.assignee_id
                LEFT JOIN projects p ON p.id = t.project_id
                WHERE {where_clause}
                ORDER BY t.created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        )
        return [_task_row_to_dict(r) for r in result.fetchall()]


@router.post("/", status_code=201)
async def create_task(body: CreateTaskRequest, request: Request) -> dict:
    """Create task."""
    user = await _auth(request)
    db = request.app.state.db

    # If no project_id provided, get or create a default project for this tenant
    project_id = body.project_id

    async with db() as session:
        if not project_id:
            # Get first available project
            r = await session.execute(
                text("SELECT id FROM projects WHERE tenant_id = :tid AND deleted_at IS NULL LIMIT 1"),
                {"tid": str(user.tenant_id)},
            )
            row = r.fetchone()
            if not row:
                # Create a default project
                import uuid as _uuid
                pid = str(_uuid.uuid4())
                await session.execute(
                    text("INSERT INTO projects (id, tenant_id, name, created_by) VALUES (:id, :tid, :name, :uid)"),
                    {"id": pid, "tid": str(user.tenant_id), "name": "General", "uid": str(user.user_id)},
                )
                project_id = pid
            else:
                project_id = str(row.id)

        result = await session.execute(
            text("""
                INSERT INTO tasks (project_id, tenant_id, title, task_type, assignee_id, priority,
                                   deadline, created_by, status)
                VALUES (:pid, :tid, :title, 'other', :assignee_id, :priority, :deadline, :uid, 'pending')
                RETURNING id, project_id, title, status, priority, assignee_id, deadline, created_at, updated_at
            """),
            {
                "pid": project_id,
                "tid": str(user.tenant_id),
                "title": body.title,
                "assignee_id": body.assignee_id or None,
                "priority": body.priority,
                "deadline": body.deadline,
                "uid": str(user.user_id),
            },
        )
        row = result.fetchone()
        await session.commit()

        return {
            "id": str(row.id),
            "project_id": str(row.project_id),
            "title": row.title,
            "description": None,
            "status": row.status,
            "priority": row.priority,
            "assignee_id": str(row.assignee_id) if row.assignee_id else None,
            "assignee_name": None,
            "project_name": None,
            "deadline": row.deadline.isoformat() if row.deadline else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


@router.get("/{task_id}")
async def get_task(task_id: UUID, request: Request) -> dict:
    """Get task detail."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        result = await session.execute(
            text("""
                SELECT t.id, t.project_id, t.title, t.status, t.priority,
                       t.assignee_id, u.full_name AS assignee_name,
                       p.name AS project_name, t.deadline, t.created_at, t.updated_at
                FROM tasks t
                LEFT JOIN users u ON u.id = t.assignee_id
                LEFT JOIN projects p ON p.id = t.project_id
                WHERE t.id = :tid AND t.tenant_id = :ten_id AND t.archived_at IS NULL
            """),
            {"tid": str(task_id), "ten_id": str(user.tenant_id)},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="task_not_found")
        return _task_row_to_dict(row)


@router.patch("/{task_id}")
async def update_task(task_id: UUID, body: UpdateTaskRequest, request: Request) -> dict:
    """Update task."""
    user = await _auth(request)
    db = request.app.state.db

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="no_updates")

    allowed = {"title", "description", "status", "priority", "assignee_id", "deadline"}
    set_parts = []
    params: dict = {"tid": str(task_id), "ten_id": str(user.tenant_id)}
    for k, v in updates.items():
        if k in allowed:
            set_parts.append(f"{k} = :{k}")
            params[k] = v

    if not set_parts:
        raise HTTPException(status_code=400, detail="no_valid_updates")

    async with db() as session:
        result = await session.execute(
            text(f"""
                UPDATE tasks SET {", ".join(set_parts)}, updated_at = NOW()
                WHERE id = :tid AND tenant_id = :ten_id AND archived_at IS NULL
                RETURNING id, project_id, title, status, priority, assignee_id, deadline, created_at, updated_at
            """),
            params,
        )
        row = result.fetchone()
        await session.commit()
        if not row:
            raise HTTPException(status_code=404, detail="task_not_found")
        return {
            "id": str(row.id),
            "project_id": str(row.project_id) if row.project_id else None,
            "title": row.title,
            "description": None,
            "status": row.status,
            "priority": row.priority,
            "assignee_id": str(row.assignee_id) if row.assignee_id else None,
            "assignee_name": None,
            "project_name": None,
            "deadline": row.deadline.isoformat() if row.deadline else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


@router.delete("/{task_id}", status_code=204, response_class=Response)
async def delete_task(task_id: UUID, request: Request) -> Response:
    """Archive/soft-delete task."""
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await session.execute(
            text("UPDATE tasks SET archived_at = NOW() WHERE id = :tid AND tenant_id = :ten_id"),
            {"tid": str(task_id), "ten_id": str(user.tenant_id)},
        )
        await session.commit()
    return Response(status_code=204)
