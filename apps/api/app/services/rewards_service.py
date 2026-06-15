# ID: AX51      |  Local: A32Y2         |  Module: X34 (M33)
# Functions: A32Y2F1 A32Y2F2 A32Y2F3 A32Y2F4
# Processes: XN01 XN02 XN03 XN04
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger("ayzen.rewards")


POINT_MILESTONES = [100, 500, 1000, 5000, 10000]


class RewardsService:
    """Manages points and reward milestones."""

    def __init__(self, db_session_factory: Any, telegram_client: Any = None) -> None:
        self._db = db_session_factory
        self._client = telegram_client

    async def get_user_points(self, user_id: UUID, project_id: UUID, tenant_id: UUID) -> dict:
        """A32Y2F1: Get comprehensive points summary for user."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT
                    COALESCE(SUM(tc.points_earned), 0) as total_points,
                    COALESCE(SUM(tc.points_earned) FILTER (WHERE DATE(tc.completed_at) = CURRENT_DATE), 0) as today_points,
                    COALESCE(SUM(tc.points_earned) FILTER (WHERE tc.completed_at >= NOW() - INTERVAL '7 days'), 0) as week_points,
                    COUNT(tc.id) as total_completions,
                    RANK() OVER (ORDER BY SUM(tc.points_earned) DESC) as rank
                FROM task_completions tc
                JOIN tasks t ON t.id = tc.task_id
                WHERE tc.user_id = :uid AND t.project_id = :pid
                """,
                {"uid": str(user_id), "pid": str(project_id)},
            )
            row = result.fetchone()
            return dict(row._mapping) if row else {"total_points": 0, "today_points": 0}

    async def check_milestone(self, user_id: UUID, project_id: UUID, tenant_id: UUID, new_points: int) -> str | None:
        """A32Y2F2: Check if user just crossed a milestone. Returns milestone key or None."""
        points_data = await self.get_user_points(user_id, project_id, tenant_id)
        total = int(points_data.get("total_points", 0))
        prev_total = total - new_points

        for milestone in POINT_MILESTONES:
            if prev_total < milestone <= total:
                return f"milestone_{milestone}"
        return None

    async def send_milestone_notification(
        self, telegram_user_id: int, milestone: str, locale: str = "bn"
    ) -> None:
        """A32Y2F3: Send reward notification for milestone."""
        if not self._client:
            return
        from apps.api.app.services.i18n_service import t
        points = milestone.replace("milestone_", "")
        msg = t("notification.reward", locale,
                reward_name=f"🏆 {points} Points",
                reward_description=f"You reached {points} points!")
        try:
            await self._client.send_message(telegram_user_id, msg)
        except Exception as exc:
            logger.warning("Milestone notification failed: %s", exc)

    async def get_leaderboard(self, project_id: UUID, tenant_id: UUID, limit: int = 20) -> list[dict]:
        """A32Y2F4: Get project leaderboard with ranks."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT u.full_name, u.email,
                       COALESCE(SUM(tc.points_earned), 0) as total_points,
                       COUNT(tc.id) as completions,
                       RANK() OVER (ORDER BY SUM(tc.points_earned) DESC NULLS LAST) as rank
                FROM project_members pm
                JOIN users u ON u.id = pm.user_id
                LEFT JOIN task_completions tc ON tc.user_id = u.id
                JOIN tasks t ON t.id = tc.task_id AND t.project_id = :pid
                WHERE pm.project_id = :pid
                GROUP BY u.full_name, u.email
                ORDER BY total_points DESC
                LIMIT :limit
                """,
                {"pid": str(project_id), "limit": limit},
            )
            return [dict(r._mapping) for r in result.fetchall()]
