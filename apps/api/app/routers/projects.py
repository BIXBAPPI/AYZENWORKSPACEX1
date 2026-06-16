# ID: AX75      |  Local: A52Y1         |  Module: X56 (M55)
# Functions: A52Y1F1 A52Y1F2 A52Y1F3 A52Y1F4 A52Y1F5
# Processes: XN01 XN02 XN03 XN04 XN05
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel

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
    """A52Y1F1: List all projects for current user's tenant."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{user.tenant_id}'")
        result = await session.execute(
            """
            SELECT p.id, p.name, p.description, p.created_at,
                   pm.role, pm.assigned_at,
                   COUNT(t.id) as task_count
            FROM projects p
            JOIN project_members pm ON pm.project_id = p.id AND pm.user_id = :uid
            LEFT JOIN tasks t ON t.project_id = p.id AND t.archived_at IS NULL
            WHERE p.deleted_at IS NULL
            GROUP BY p.id, p.name, p.description, p.created_at, pm.role, pm.assigned_at
            ORDER BY p.created_at DESC
            """,
            {"uid": str(user.user_id)},
        )
        return [dict(r._mapping) for r in result.fetchall()]


@router.post("/", status_code=201)
async def create_project(body: CreateProjectRequest, request: Request) -> dict:
    """A52Y1F2: Create new project (admin only)."""
    user = await _auth(request)
    from apps.api.app.middleware.auth import require_admin
    await require_admin(user)

    db = request.app.state.db
    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{user.tenant_id}'")
        result = await session.execute(
            """
            INSERT INTO projects (name, description, tenant_id, created_by)
            VALUES (:name, :desc, :tid, :uid)
            RETURNING id, name, description, created_at
            """,
            {"name": body.name, "desc": body.description, "tid": str(user.tenant_id), "uid": str(user.user_id)},
        )
        project = dict(result.fetchone()._mapping)

        # Auto-assign creator as owner
        await session.execute(
            """
            INSERT INTO project_members (project_id, user_id, role, assigned_by)
            VALUES (:pid, :uid, 'owner', :uid)
            """,
            {"pid": str(project["id"]), "uid": str(user.user_id)},
        )
        await session.commit()

    return project


@router.get("/{project_id}")
async def get_project(project_id: UUID, request: Request) -> dict:
    """A52Y1F3: Get project detail."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{user.tenant_id}'")
        result = await session.execute(
            """
            SELECT p.id, p.name, p.description, p.created_at, pm.role
            FROM projects p
            JOIN project_members pm ON pm.project_id = p.id AND pm.user_id = :uid
            WHERE p.id = :pid AND p.deleted_at IS NULL
            """,
            {"uid": str(user.user_id), "pid": str(project_id)},
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="project_not_found")
        return dict(row._mapping)


@router.patch("/{project_id}")
async def update_project(project_id: UUID, body: UpdateProjectRequest, request: Request) -> dict:
    """A52Y1F4: Update project (admin only)."""
    user = await _auth(request)
    from apps.api.app.middleware.auth import require_admin
    await require_admin(user)

    db = request.app.state.db
    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{user.tenant_id}'")
        updates = {}
        if body.name is not None:
            updates["name"] = body.name
        if body.description is not None:
            updates["description"] = body.description

        if not updates:
            raise HTTPException(status_code=400, detail="no_updates")

        set_clauses = ", ".join(f"{k} = :{k}" for k in updates)
        updates["pid"] = str(project_id)
        result = await session.execute(
            f"UPDATE projects SET {set_clauses}, updated_at = NOW() WHERE id = :pid RETURNING id, name, description",
            updates,
        )
        await session.commit()
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="project_not_found")
        return dict(row._mapping)


@router.delete("/{project_id}", status_code=204, response_class=Response)
async def delete_project(project_id: UUID, request: Request) -> Response:
    """A52Y1F5: Soft-delete project (owner only)."""
    user = await _auth(request)
    from apps.api.app.middleware.auth import require_admin
    await require_admin(user)

    db = request.app.state.db
    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{user.tenant_id}'")
        await session.execute(
            "UPDATE projects SET deleted_at = NOW() WHERE id = :pid AND tenant_id = :tid",
            {"pid": str(project_id), "tid": str(user.tenant_id)},
        )
        await session.commit()
    return Response(status_code=204)
