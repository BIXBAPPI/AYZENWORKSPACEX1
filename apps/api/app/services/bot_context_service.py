# ID: AX22      |  Local: A7Y1          |  Module: X08 (M07)
# Functions: A7Y1F1 A7Y1F2 A7Y1F3 A7Y1F4
# Processes: XN01 XN02 XN03 XN04
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis

logger = logging.getLogger("ayzen.bot_context")

_PROJECT_CACHE_TTL = 30
_CTX_CACHE_TTL = 60


class BotContextService:
    """Resolves tenant, project, role, and locale for a Telegram user."""

    def __init__(self, redis: aioredis.Redis | None, db_session_factory: Any) -> None:
        self._redis = redis
        self._db = db_session_factory

    # XN01  Context Resolution
    async def resolve(self, telegram_user_id: int) -> dict | None:
        """
        Look up user by telegram_id (M06); if None → None (not linked).
        Load BotState (M03); SET LOCAL tenant; load project + role; locale.
        Returns BotContext dict or None.
        """
        async with self._db() as session:
            result = await session.execute(
                """
                SELECT u.id as user_id, u.email, u.full_name, u.tenant_id, u.role,
                       ubs.active_project_id, ubs.locale
                FROM users u
                LEFT JOIN user_bot_state ubs ON ubs.user_id = u.id
                WHERE u.telegram_user_id = :tid
                """,
                {"tid": telegram_user_id},
            )
            row = result.fetchone()
            if not row:
                return None

            user_dict = dict(row._mapping)
            tenant_id = user_dict.get("tenant_id")
            project_id = user_dict.get("active_project_id")
            locale = user_dict.get("locale", "bn")

            # Set tenant isolation
            if tenant_id:
                await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")

            ctx: dict[str, Any] = {
                "user_id": user_dict["user_id"],
                "email": user_dict.get("email"),
                "full_name": user_dict.get("full_name"),
                "tenant_id": tenant_id,
                "role": user_dict.get("role"),
                "project_id": project_id,
                "locale": locale,
            }

            # Load project name if active project set
            if project_id:
                proj_result = await session.execute(
                    """
                    SELECT p.name, pm.role as project_role
                    FROM projects p
                    JOIN project_members pm ON pm.project_id = p.id AND pm.user_id = :uid
                    WHERE p.id = :pid AND p.deleted_at IS NULL
                    """,
                    {"pid": str(project_id), "uid": str(user_dict["user_id"])},
                )
                proj_row = proj_result.fetchone()
                if proj_row:
                    ctx["project_name"] = proj_row.name
                    ctx["project_role"] = proj_row.project_role
                else:
                    ctx["project_id"] = None  # not a member or project deleted

            return ctx

    # XN02  Set Active Project
    async def set_active_project(self, telegram_user_id: int, project_id: UUID) -> None:
        """
        Verify user is project_member; UPDATE user_bot_state active_project_id;
        update BotState Redis; audit log.
        """
        async with self._db() as session:
            # Verify membership
            result = await session.execute(
                """
                SELECT u.id as user_id
                FROM users u
                JOIN project_members pm ON pm.user_id = u.id AND pm.project_id = :pid
                WHERE u.telegram_user_id = :tid
                """,
                {"tid": telegram_user_id, "pid": str(project_id)},
            )
            row = result.fetchone()
            if not row:
                raise ValueError("User is not a member of this project")

            await session.execute(
                """
                UPDATE user_bot_state SET active_project_id = :pid
                WHERE user_id = :uid
                """,
                {"pid": str(project_id), "uid": str(row.user_id)},
            )
            await session.commit()

        # Update Redis state
        if self._redis:
            from apps.api.app.services.bot_state_service import BotStateService
            state_svc = BotStateService(self._redis, self._db)
            await state_svc.transition(telegram_user_id, "IDLE", project_id=project_id)

    # XN03  Get User Projects
    async def get_user_projects(self, user_id: UUID, tenant_id: UUID) -> list[dict]:
        """
        SELECT projects JOIN project_members WHERE member=user AND status=active
        ORDER BY assigned_at DESC LIMIT 50. Cache 30s.
        """
        import json
        cache_key = f"ayzen:projects:{user_id}"

        if self._redis:
            try:
                cached = await self._redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT p.id, p.name, p.description, pm.role, pm.assigned_at,
                       COUNT(t.id) as task_count
                FROM projects p
                JOIN project_members pm ON pm.project_id = p.id AND pm.user_id = :uid
                LEFT JOIN tasks t ON t.project_id = p.id AND t.archived_at IS NULL
                WHERE p.deleted_at IS NULL
                GROUP BY p.id, p.name, p.description, pm.role, pm.assigned_at
                ORDER BY pm.assigned_at DESC
                LIMIT 50
                """,
                {"uid": str(user_id)},
            )
            projects = [dict(r._mapping) for r in result.fetchall()]

        if self._redis:
            try:
                await self._redis.set(cache_key, json.dumps(projects, default=str), ex=_PROJECT_CACHE_TTL)
            except Exception:
                pass

        return projects

    # XN04  Auto-select First Project
    async def auto_select_first_project(self, user_id: UUID) -> UUID | None:
        """
        get_user_projects(); if exactly 1 → call set_active_project and return id.
        Else None (user must pick).
        """
        async with self._db() as session:
            result = await session.execute(
                "SELECT tenant_id FROM users WHERE id = :uid",
                {"uid": str(user_id)},
            )
            row = result.fetchone()
            if not row:
                return None
            tenant_id = row.tenant_id

        projects = await self.get_user_projects(user_id, tenant_id)
        if len(projects) == 1:
            pid = projects[0]["id"]
            async with self._db() as session:
                await session.execute(
                    "UPDATE user_bot_state SET active_project_id = :pid WHERE user_id = :uid",
                    {"pid": str(pid), "uid": str(user_id)},
                )
                await session.commit()
            return pid
        return None
