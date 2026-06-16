from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.projects")

router = APIRouter()


class CreateProjectRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


@router.get("/")
async def list_projects(request: Request) -> list[dict]:
    """List all projects for current user's tenant."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        result = await session.execute(
            text("""
            SELECT p.id, p.name, p.description, p.created_at,
                   pm.role, pm.assigned_at,
                   COUNT(t.id) AS task_count
            FROM projects p
            JOIN project_members pm ON pm.project_id = p.id AND pm.user_id = :uid
            LEFT JOIN tasks t ON t.project_id = p.id AND t.archived_at IS NULL
            WHERE p.deleted_at IS NULL AND p.tenant_id = :tid
            GROUP BY p.id, p.name, p.description, p.created_at, pm.role, pm.assigned_at
            ORDER BY p.created_at DESC
            """),
            {"uid": str(user.user_id), "tid": str(user.tenant_id)},
        )
        rows = result.fetchall()
        return [
            {
                "id": str(r.id),
                "name": r.name,
                "description": r.description,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "role": r.role,
                "task_count": r.task_count or 0,
            }
            for r in rows
        ]


@router.post("/", status_code=201)
async def create_project(body: CreateProjectRequest, request: Request) -> dict:
    """Create new project (admin only)."""
    user = await _auth(request)
    from apps.api.app.middleware.auth import require_admin
    await require_admin(user)

    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("""
            INSERT INTO projects (name, description, tenant_id, created_by)
            VALUES (:name, :desc, :tid, :uid)
            RETURNING id, name, description, created_at
            """),
            {"name": body.name, "desc": body.description, "tid": str(user.tenant_id), "uid": str(user.user_id)},
        )
        project = result.fetchone()
        proj_id = str(project.id)

        await session.execute(
            text("""
            INSERT INTO project_members (project_id, user_id, role, assigned_by)
            VALUES (:pid, :uid, 'owner', :uid)
            ON CONFLICT (project_id, user_id) DO NOTHING
            """),
            {"pid": proj_id, "uid": str(user.user_id)},
        )
        await session.commit()

    return {
        "id": proj_id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "role": "owner",
        "task_count": 0,
    }


@router.get("/{project_id}")
async def get_project(project_id: UUID, request: Request) -> dict:
    """Get project detail."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        result = await session.execute(
            text("""
            SELECT p.id, p.name, p.description, p.created_at, pm.role,
                   COUNT(t.id) AS task_count
            FROM projects p
            JOIN project_members pm ON pm.project_id = p.id AND pm.user_id = :uid
            LEFT JOIN tasks t ON t.project_id = p.id AND t.archived_at IS NULL
            WHERE p.id = :pid AND p.deleted_at IS NULL AND p.tenant_id = :tid
            GROUP BY p.id, p.name, p.description, p.created_at, pm.role
            """),
            {"uid": str(user.user_id), "pid": str(project_id), "tid": str(user.tenant_id)},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="project_not_found")
        return {
            "id": str(row.id),
            "name": row.name,
            "description": row.description,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "role": row.role,
            "task_count": row.task_count or 0,
        }


@router.patch("/{project_id}")
async def update_project(project_id: UUID, body: UpdateProjectRequest, request: Request) -> dict:
    """Update project (admin only)."""
    user = await _auth(request)
    from apps.api.app.middleware.auth import require_admin
    await require_admin(user)

    db = request.app.state.db
    updates: dict = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.description is not None:
        updates["description"] = body.description

    if not updates:
        raise HTTPException(status_code=400, detail="no_updates")

    set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
    updates["pid"] = str(project_id)
    updates["tid"] = str(user.tenant_id)

    async with db() as session:
        result = await session.execute(
            text(f"UPDATE projects SET {set_clauses}, updated_at = NOW() WHERE id = :pid AND tenant_id = :tid RETURNING id, name, description"),
            updates,
        )
        await session.commit()
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="project_not_found")
        return {"id": str(row.id), "name": row.name, "description": row.description}


@router.delete("/{project_id}", status_code=204, response_class=Response)
async def delete_project(project_id: UUID, request: Request) -> Response:
    """Soft-delete project (owner only)."""
    user = await _auth(request)
    from apps.api.app.middleware.auth import require_admin
    await require_admin(user)

    db = request.app.state.db
    async with db() as session:
        await session.execute(
            text("UPDATE projects SET deleted_at = NOW() WHERE id = :pid AND tenant_id = :tid"),
            {"pid": str(project_id), "tid": str(user.tenant_id)},
        )
        await session.commit()
    return Response(status_code=204)
