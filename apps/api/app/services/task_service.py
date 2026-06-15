# ID: AX52      |  Local: A33Y1         |  Module: X35 (M34)
# Functions: A33Y1F1 A33Y1F2 A33Y1F3 A33Y1F4
# Processes: XN01 XN02 XN03 XN04
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger("ayzen.task_service")


class TaskService:
    """Business logic for task management."""

    def __init__(self, db_session_factory: Any) -> None:
        self._db = db_session_factory

    async def get_pending_tasks(self, user_id: UUID, project_id: UUID, tenant_id: UUID) -> list[dict]:
        """A33Y1F1: Get tasks not yet completed by user in project."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT t.id, t.title, t.task_type, t.target_url, t.points_per_account,
                       t.deadline, t.max_slots_per_user,
                       COUNT(DISTINCT asl.id) as user_slot_count,
                       COUNT(DISTINCT tc.id) as done_slot_count
                FROM tasks t
                LEFT JOIN account_slots asl ON asl.user_id = :uid AND asl.project_id = :pid
                LEFT JOIN task_completions tc ON tc.task_id = t.id AND tc.user_id = :uid
                WHERE t.project_id = :pid
                  AND t.archived_at IS NULL
                  AND (t.deadline IS NULL OR t.deadline > NOW())
                GROUP BY t.id, t.title, t.task_type, t.target_url, t.points_per_account, t.deadline, t.max_slots_per_user
                HAVING COUNT(DISTINCT asl.id) > COUNT(DISTINCT tc.id)
                ORDER BY t.created_at DESC
                """,
                {"uid": str(user_id), "pid": str(project_id)},
            )
            return [dict(r._mapping) for r in result.fetchall()]

    async def get_task_stats(self, task_id: UUID, tenant_id: UUID) -> dict:
        """A33Y1F2: Get completion statistics for a task."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT
                    COUNT(tc.id) as total_completions,
                    COUNT(DISTINCT tc.user_id) as unique_users,
                    COALESCE(SUM(tc.points_earned), 0) as total_points,
                    MIN(tc.completed_at) as first_completion,
                    MAX(tc.completed_at) as last_completion
                FROM task_completions tc
                WHERE tc.task_id = :tid
                """,
                {"tid": str(task_id)},
            )
            row = result.fetchone()
            return dict(row._mapping) if row else {}

    async def archive_task(self, task_id: UUID, tenant_id: UUID) -> bool:
        """A33Y1F3: Soft-archive a task."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                "UPDATE tasks SET archived_at = NOW() WHERE id = :tid AND archived_at IS NULL RETURNING id",
                {"tid": str(task_id)},
            )
            await session.commit()
            return result.rowcount > 0

    async def get_overdue_tasks(self, tenant_id: UUID) -> list[dict]:
        """A33Y1F4: Get all tasks past deadline that are not archived."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT t.id, t.title, t.deadline, t.project_id, p.name as project_name
                FROM tasks t JOIN projects p ON p.id = t.project_id
                WHERE t.deadline < NOW() AND t.archived_at IS NULL
                ORDER BY t.deadline DESC
                """,
            )
            return [dict(r._mapping) for r in result.fetchall()]
