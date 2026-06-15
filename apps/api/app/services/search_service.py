# ID: AX59      |  Local: A37Y4         |  Module: X42 (M41)
# Functions: A37Y4F1 A37Y4F2 A37Y4F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger("ayzen.search")


class SearchService:
    """Full-text search across tasks and members."""

    def __init__(self, db_session_factory: Any) -> None:
        self._db = db_session_factory

    async def search_tasks(
        self, query: str, project_id: UUID, tenant_id: UUID, limit: int = 20
    ) -> list[dict]:
        """A37Y4F1: Search tasks by title or type within a project."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT id, title, task_type, points_per_account, deadline
                FROM tasks
                WHERE project_id = :pid
                  AND archived_at IS NULL
                  AND (
                    title ILIKE :q
                    OR task_type ILIKE :q
                  )
                ORDER BY created_at DESC
                LIMIT :limit
                """,
                {"pid": str(project_id), "q": f"%{query}%", "limit": limit},
            )
            return [dict(r._mapping) for r in result.fetchall()]

    async def search_members(
        self, query: str, project_id: UUID, tenant_id: UUID, limit: int = 20
    ) -> list[dict]:
        """A37Y4F2: Search project members by name or email."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT u.id, u.full_name, u.email, pm.role
                FROM project_members pm
                JOIN users u ON u.id = pm.user_id
                WHERE pm.project_id = :pid
                  AND (u.full_name ILIKE :q OR u.email ILIKE :q)
                ORDER BY u.full_name
                LIMIT :limit
                """,
                {"pid": str(project_id), "q": f"%{query}%", "limit": limit},
            )
            return [dict(r._mapping) for r in result.fetchall()]

    async def search_all(self, query: str, project_id: UUID, tenant_id: UUID) -> dict:
        """A37Y4F3: Combined search across tasks and members."""
        import asyncio
        tasks, members = await asyncio.gather(
            self.search_tasks(query, project_id, tenant_id),
            self.search_members(query, project_id, tenant_id),
        )
        return {"tasks": tasks, "members": members, "total": len(tasks) + len(members)}
