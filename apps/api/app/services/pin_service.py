# ID: AX60      |  Local: A38Y2         |  Module: X43 (M42)
# Functions: A38Y2F1 A38Y2F2 A38Y2F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger("ayzen.pin")


class PinService:
    """Manages pinned tasks for quick access in bot."""

    def __init__(self, db_session_factory: Any, redis: Any | None = None) -> None:
        self._db = db_session_factory
        self._redis = redis

    _CACHE_TTL = 60
    _CACHE_PREFIX = "ayzen:pins:"

    def _cache_key(self, user_id: UUID, project_id: UUID) -> str:
        return f"{self._CACHE_PREFIX}{user_id}:{project_id}"

    async def _invalidate(self, user_id: UUID, project_id: UUID) -> None:
        if self._redis:
            try:
                await self._redis.delete(self._cache_key(user_id, project_id))
            except Exception:
                pass

    async def get_pinned(self, user_id: UUID, project_id: UUID, tenant_id: UUID) -> list[dict]:
        """A38Y2F1: Get user's pinned tasks for a project."""
        import json
        key = self._cache_key(user_id, project_id)
        if self._redis:
            try:
                cached = await self._redis.get(key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT t.id, t.title, t.task_type, t.points_per_account, tp.pinned_at
                FROM task_pins tp
                JOIN tasks t ON t.id = tp.task_id
                WHERE tp.user_id = :uid AND tp.project_id = :pid AND t.archived_at IS NULL
                ORDER BY tp.pinned_at DESC
                LIMIT 10
                """,
                {"uid": str(user_id), "pid": str(project_id)},
            )
            pins = [dict(r._mapping) for r in result.fetchall()]

        if self._redis and pins:
            try:
                await self._redis.set(key, json.dumps(pins, default=str), ex=self._CACHE_TTL)
            except Exception:
                pass
        return pins

    async def pin_task(self, user_id: UUID, task_id: UUID, project_id: UUID, tenant_id: UUID) -> None:
        """A38Y2F2: Pin a task for quick access."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            await session.execute(
                """
                INSERT INTO task_pins (user_id, task_id, project_id)
                VALUES (:uid, :tid, :pid)
                ON CONFLICT (user_id, task_id) DO NOTHING
                """,
                {"uid": str(user_id), "tid": str(task_id), "pid": str(project_id)},
            )
            await session.commit()
        await self._invalidate(user_id, project_id)

    async def unpin_task(self, user_id: UUID, task_id: UUID, project_id: UUID, tenant_id: UUID) -> None:
        """A38Y2F3: Unpin a task."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            await session.execute(
                "DELETE FROM task_pins WHERE user_id = :uid AND task_id = :tid",
                {"uid": str(user_id), "tid": str(task_id)},
            )
            await session.commit()
        await self._invalidate(user_id, project_id)
