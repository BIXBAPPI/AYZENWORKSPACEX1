from __future__ import annotations
import logging
from uuid import UUID
from fastapi import APIRouter, Request
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.analytics")
router = APIRouter()

TIER_THRESHOLDS = [(10000, "Platinum"), (5000, "Gold"), (1000, "Silver"), (0, "Bronze")]

def _tier(xp: int) -> str:
    for t, name in TIER_THRESHOLDS:
        if xp >= t:
            return name
    return "Bronze"

async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


@router.get("/dashboard")
async def dashboard_summary(request: Request) -> dict:
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
        completion_rate = round((completed_tasks / max(total_tasks, 1)) * 100, 1) if total_tasks else 0

        r_me = await session.execute(
            text("SELECT COALESCE(global_xp, 0) AS xp, COALESCE(global_streak, 0) AS streak FROM users WHERE id = :uid"),
            {"uid": str(user.user_id)},
        )
        me_row = r_me.fetchone()
        my_xp = me_row.xp if me_row else 0
        my_streak = me_row.streak if me_row else 0

        r_rank = await session.execute(
            text("""
                SELECT rank FROM (
                    SELECT id, RANK() OVER (ORDER BY COALESCE(global_xp,0) DESC) AS rank
                    FROM users WHERE tenant_id = :tid
                ) sub WHERE id = :uid
            """),
            {"tid": str(user.tenant_id), "uid": str(user.user_id)},
        )
        rank_row = r_rank.fetchone()

        r4 = await session.execute(
            text("""
                SELECT u.id AS user_id, u.full_name, u.email,
                       COALESCE(u.global_xp, 0) AS xp,
                       COUNT(t.id) FILTER (WHERE t.status = 'completed') AS completed_count,
                       RANK() OVER (ORDER BY COALESCE(u.global_xp, 0) DESC) AS rank
                FROM users u
                LEFT JOIN tasks t ON t.assignee_id = u.id AND t.tenant_id = :tid
                WHERE u.tenant_id = :tid
                GROUP BY u.id, u.full_name, u.email, u.global_xp
                ORDER BY xp DESC LIMIT 5
            """),
            {"tid": str(user.tenant_id)},
        )
        top_members = [
            {"user_id": str(r.user_id), "full_name": r.full_name, "email": r.email,
             "xp": r.xp or 0, "tier": _tier(r.xp or 0), "completed_count": r.completed_count or 0, "rank": r.rank}
            for r in r4.fetchall()
        ]

        r5 = await session.execute(
            text("""
                SELECT tc.id, tc.task_id, t.title AS task_title,
                       tc.user_id, u.full_name AS user_name, tc.completed_at AS created_at
                FROM task_completions tc
                JOIN tasks t ON t.id = tc.task_id
                JOIN users u ON u.id = tc.user_id
                WHERE t.tenant_id = :tid
                ORDER BY tc.completed_at DESC LIMIT 10
            """),
            {"tid": str(user.tenant_id)},
        )
        recent_completions = [
            {"id": str(r.id), "task_id": str(r.task_id), "task_title": r.task_title,
             "user_id": str(r.user_id), "user_name": r.user_name,
             "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in r5.fetchall()
        ]

    return {
        "total_tasks": total_tasks, "completed_tasks": completed_tasks,
        "active_projects": row.active_projects or 0, "active_members": row.active_members or 0,
        "overdue_tasks": row.overdue_tasks or 0, "completion_rate": completion_rate,
        "my_xp": my_xp, "my_tier": _tier(my_xp), "my_streak": my_streak,
        "my_rank": rank_row.rank if rank_row else None,
        "top_members": top_members, "recent_completions": recent_completions,
    }


@router.get("/me")
async def my_analytics(request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        r_me = await session.execute(
            text("SELECT COALESCE(global_xp, 0) AS xp, COALESCE(global_streak, 0) AS streak FROM users WHERE id = :uid"),
            {"uid": str(user.user_id)},
        )
        me = r_me.fetchone()
        my_xp = me.xp if me else 0
        my_streak = me.streak if me else 0

        r_tasks = await session.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (WHERE assignee_id = :uid) AS total_assigned,
                    COUNT(*) FILTER (WHERE assignee_id = :uid AND status = 'completed') AS completed,
                    COUNT(*) FILTER (WHERE assignee_id = :uid AND deadline < NOW() AND status NOT IN ('completed','cancelled')) AS overdue,
                    COUNT(*) FILTER (WHERE assignee_id = :uid AND status = 'in_progress') AS in_progress,
                    COUNT(*) FILTER (WHERE assignee_id = :uid AND status = 'pending') AS pending
                FROM tasks WHERE tenant_id = :tid AND archived_at IS NULL
            """),
            {"uid": str(user.user_id), "tid": str(user.tenant_id)},
        )
        t = r_tasks.fetchone()

        r_xp = await session.execute(
            text("SELECT COALESCE(SUM(COALESCE(points_per_account,0)), 0) AS possible_xp FROM tasks WHERE tenant_id = :tid AND assignee_id = :uid AND archived_at IS NULL"),
            {"tid": str(user.tenant_id), "uid": str(user.user_id)},
        )
        xp_row = r_xp.fetchone()
        possible_xp = int(xp_row.possible_xp) if xp_row else 0
        roi = round((my_xp / max(possible_xp, 1)) * 100, 1) if possible_xp else 0

        r_rank = await session.execute(
            text("SELECT rank FROM (SELECT id, RANK() OVER (ORDER BY COALESCE(global_xp,0) DESC) AS rank FROM users WHERE tenant_id = :tid) sub WHERE id = :uid"),
            {"tid": str(user.tenant_id), "uid": str(user.user_id)},
        )
        rank_row = r_rank.fetchone()

        r_proj = await session.execute(
            text("""
                SELECT p.id, p.name,
                    COUNT(t.id) AS total_tasks,
                    COUNT(t.id) FILTER (WHERE t.status = 'completed') AS completed_tasks,
                    COALESCE(SUM(CASE WHEN t.status='completed' THEN COALESCE(t.points_per_account,0) ELSE 0 END), 0) AS xp_earned
                FROM projects p
                JOIN tasks t ON t.project_id = p.id AND t.assignee_id = :uid AND t.archived_at IS NULL
                WHERE p.tenant_id = :tid AND p.deleted_at IS NULL
                GROUP BY p.id, p.name ORDER BY completed_tasks DESC
            """),
            {"tid": str(user.tenant_id), "uid": str(user.user_id)},
        )
        projects = [
            {"id": str(r.id), "name": r.name, "total_tasks": r.total_tasks or 0,
             "completed_tasks": r.completed_tasks or 0,
             "completion_pct": round((r.completed_tasks or 0) / max(r.total_tasks or 1, 1) * 100, 1),
             "xp_earned": r.xp_earned or 0}
            for r in r_proj.fetchall()
        ]

        r_daily = await session.execute(
            text("""
                SELECT DATE(tc.completed_at) AS day, COUNT(*) AS count
                FROM task_completions tc JOIN tasks t ON t.id = tc.task_id
                WHERE tc.user_id = :uid AND t.tenant_id = :tid AND tc.completed_at >= NOW() - INTERVAL '60 days'
                GROUP BY day ORDER BY day ASC
            """),
            {"uid": str(user.user_id), "tid": str(user.tenant_id)},
        )
        daily_activity = [{"date": str(r.day), "count": r.count} for r in r_daily.fetchall()]

    return {
        "xp": my_xp, "tier": _tier(my_xp), "streak": my_streak,
        "rank": rank_row.rank if rank_row else None,
        "roi_pct": roi, "possible_xp": possible_xp,
        "total_assigned": t.total_assigned or 0, "completed": t.completed or 0,
        "overdue": t.overdue or 0, "in_progress": t.in_progress or 0, "pending": t.pending or 0,
        "projects": projects, "daily_activity": daily_activity,
    }


@router.get("/snapshots")
async def analytics_snapshots(request: Request, days: int = 30) -> list[dict]:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("""
                SELECT d::date AS snapshot_date,
                    COUNT(DISTINCT t.id) FILTER (WHERE t.status = 'completed') AS completed_tasks,
                    COUNT(DISTINCT t.id) AS total_tasks,
                    COUNT(DISTINCT t.assignee_id) AS active_members,
                    COUNT(DISTINCT t.id) FILTER (WHERE DATE(t.created_at) = d::date) AS new_tasks
                FROM generate_series((NOW()::date - (:days - 1) * INTERVAL '1 day'), NOW()::date, '1 day') AS g(d)
                LEFT JOIN tasks t ON t.tenant_id = :tid AND t.archived_at IS NULL
                GROUP BY d ORDER BY d ASC
            """),
            {"tid": str(user.tenant_id), "days": days},
        )
        return [
            {"id": str(row.snapshot_date), "snapshot_date": str(row.snapshot_date),
             "completed_tasks": row.completed_tasks or 0, "total_tasks": row.total_tasks or 0,
             "active_members": row.active_members or 0, "new_tasks": row.new_tasks or 0}
            for row in r.fetchall()
        ]


@router.get("/overview/{project_id}")
async def project_overview(project_id: UUID, request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            text("""
                SELECT COUNT(DISTINCT t.id) AS total_tasks, COUNT(DISTINCT pm.user_id) AS total_members,
                    COUNT(DISTINCT tc.id) AS total_completions, COALESCE(SUM(tc.points_earned), 0) AS total_points
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
