# ID: AX54      |  Local: A35Y1         |  Module: X37 (M36)
# Functions: A35Y1F1 A35Y1F2
# Processes: XN01 XN02
from __future__ import annotations

import logging

logger = logging.getLogger("ayzen.jobs.analytics")


async def run() -> None:
    """
    A35Y1F1: APScheduler cron job — runs daily at 02:00 UTC.
    Takes analytics snapshots per tenant/project for dashboard charts.
    """
    try:
        from apps.api.main import session_factory
    except ImportError:
        return

    if not session_factory:
        return

    try:
        async with session_factory() as session:
            # Snapshot: daily completion counts per project
            await session.execute(
                """
                INSERT INTO analytics_snapshots
                    (tenant_id, project_id, snapshot_date, completions, unique_users, total_points)
                SELECT
                    t.tenant_id,
                    t.project_id,
                    CURRENT_DATE - INTERVAL '1 day',
                    COUNT(tc.id),
                    COUNT(DISTINCT tc.user_id),
                    COALESCE(SUM(tc.points_earned), 0)
                FROM task_completions tc
                JOIN tasks t ON t.id = tc.task_id
                WHERE DATE(tc.completed_at) = CURRENT_DATE - INTERVAL '1 day'
                GROUP BY t.tenant_id, t.project_id
                ON CONFLICT (project_id, snapshot_date) DO UPDATE SET
                    completions = EXCLUDED.completions,
                    unique_users = EXCLUDED.unique_users,
                    total_points = EXCLUDED.total_points
                """,
            )
            await session.commit()
            logger.info("Analytics snapshot completed")
    except Exception as exc:
        logger.exception("Analytics job failed: %s", exc)
