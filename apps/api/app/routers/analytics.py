from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Request
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.analytics")

router = APIRouter()


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


@router.get("/dashboard")
async def dashboard_summary(request: Request) -> dict:
    """Tenant-level dashboard summary for the web dashboard."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        r = await session.execute(
            text("""
                SELECT
                    COUNT(DISTINCT t.id) FILTER (WHERE t.archived_at IS NULL) AS total_tasks,
                    COUNT(DISTINCT t.id) FILTER (WHERE t.archived_at IS NULL AND t.status = 'completed') AS completed_tasks,
                    COUNT(DISTINCT p.id) FILTER (WHERE p.deleted_at IS NULL) AS active_projects,
                    COUNT(DISTINCT u2.id) AS active_members,
                    COUNT(DISTINCT t.id) FILTER (
                        WHERE t.archived_at IS NULL AND t.deadline < NOW() AND t.status NOT IN ('completed','cancelled')
                    ) AS overdue_tasks
                FROM tenants tn
                LEFT JOIN projects p ON p.tenant_id = tn.id
                LEFT JOIN tasks t ON t.tenant_id = tn.id
                LEFT JOIN users u2 ON u2.tenant_id = tn.id
                WHERE tn.id = :tid
            """),
            {"tid": str(user.tenant_id)},
        )
        row = r.fetchone()
        total_tasks = row.total_tasks or 0
        completed_tasks = row.completed_tasks or 0
        active_projects = row.active_projects or 0
        active_members = row.active_members or 0
        overdue_tasks = row.overdue_tasks or 0
        completion_rate = round((completed_tasks / max(total_tasks, 1)) * 100, 1) if total_tasks else 0

        r4 = await session.execute(
            text("""
                SELECT u.id AS user_id, u.full_name, u.email,
                       COUNT(t.id) FILTER (WHERE t.status = 'completed') AS completed_count,
                       RANK() OVER (ORDER BY COUNT(t.id) FILTER (WHERE t.status = 'completed') DESC) AS rank
                FROM users u
                LEFT JOIN tasks t ON t.assignee_id = u.id AND t.tenant_id = :tid
                WHERE u.tenant_id = :tid
                GROUP BY u.id, u.full_name, u.email
                ORDER BY completed_count DESC
                LIMIT 5
            """),
            {"tid": str(user.tenant_id)},
        )
        top_members = [
            {
                "user_id": str(r.user_id),
                "full_name": r.full_name,
                "email": r.email,
                "completed_count": r.completed_count,
                "rank": r.rank,
            }
            for r in r4.fetchall()
        ]

        r5 = await session.execute(
            text("""
                SELECT tc.id, tc.task_id, t.title AS task_title,
                       tc.user_id, u.full_name AS user_name,
                       NULL AS note, NULL AS percent_complete,
                       tc.completed_at AS created_at
                FROM task_completions tc
                JOIN tasks t ON t.id = tc.task_id
                JOIN users u ON u.id = tc.user_id
                WHERE t.tenant_id = :tid
                ORDER BY tc.completed_at DESC
                LIMIT 10
            """),
            {"tid": str(user.tenant_id)},
        )
        recent_completions = [
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
            for r in r5.fetchall()
        ]

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "active_projects": active_projects,
        "active_members": active_members,
        "overdue_tasks": overdue_tasks,
        "completion_rate": completion_rate,
        "top_members": top_members,
        "recent_completions": recent_completions,
    }


@router.get("/snapshots")
async def analytics_snapshots(request: Request, days: int = 30) -> list[dict]:
    """Daily analytics snapshots for charts."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        r = await session.execute(
            text("""
                SELECT
                    d::date AS snapshot_date,
                    COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'completed') AS completed_tasks,
                    COUNT(DISTINCT t.id) AS total_tasks,
                    COUNT(DISTINCT t.assignee_id) AS active_members,
                    COUNT(DISTINCT t.id) FILTER (WHERE DATE(t.created_at) = d::date) AS new_tasks
                FROM generate_series(
                    (NOW()::date - (:days - 1) * INTERVAL '1 day'),
                    NOW()::date,
                    '1 day'
                ) AS g(d)
                LEFT JOIN tasks t ON t.tenant_id = :tid AND t.archived_at IS NULL
                GROUP BY d
                ORDER BY d ASC
            """),
            {"tid": str(user.tenant_id), "days": days},
        )
        return [
            {
                "id": str(row.snapshot_date),
                "snapshot_date": str(row.snapshot_date),
                "completed_tasks": row.completed_tasks or 0,
                "total_tasks": row.total_tasks or 0,
                "active_members": row.active_members or 0,
                "new_tasks": row.new_tasks or 0,
            }
            for row in r.fetchall()
        ]


@router.get("/overview/{project_id}")
async def project_overview(project_id: UUID, request: Request) -> dict:
    """Full project analytics overview."""
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("""
                SELECT
                    COUNT(DISTINCT t.id) AS total_tasks,
                    COUNT(DISTINCT pm.user_id) AS total_members,
                    COUNT(DISTINCT tc.id) AS total_completions,
                    COALESCE(SUM(tc.points_earned), 0) AS total_points
                FROM projects p
                LEFT JOIN tasks t ON t.project_id = p.id AND t.archived_at IS NULL
                LEFT JOIN project_members pm ON pm.project_id = p.id
                LEFT JOIN task_completions tc ON tc.task_id = t.id
                WHERE p.id = :pid AND p.tenant_id = :tid
            """),
            {"pid": str(project_id), "tid": str(user.tenant_id)},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else {}
