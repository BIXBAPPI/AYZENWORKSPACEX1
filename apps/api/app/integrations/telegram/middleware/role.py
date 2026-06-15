# ID: AX23      |  Local: A8Y1          |  Module: X09 (M08)
# Functions: A8Y1F1 A8Y1F2 A8Y1F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger("ayzen.telegram.role")

_ROLE_CACHE_TTL = 60
_ROLE_CACHE_PREFIX = "ayzen:role:"


class RoleMiddleware:
    """
    Server-side role verification for admin actions.
    Cache for 60s only — re-verify on every admin call.
    """

    def __init__(self, redis: aioredis.Redis | None, db_session_factory: Any) -> None:
        self._redis = redis
        self._db = db_session_factory

    async def get_project_role(self, user_id: str, project_id: str) -> str | None:
        """
        A8Y1F1: Get user's role in a project. Cached 60s.
        Returns 'owner', 'manager', 'member', or None (not a member).
        """
        cache_key = f"{_ROLE_CACHE_PREFIX}{user_id}:{project_id}"

        if self._redis:
            try:
                cached = await self._redis.get(cache_key)
                if cached:
                    return cached if cached != "NONE" else None
            except Exception:
                pass

        async with self._db() as session:
            result = await session.execute(
                "SELECT role FROM project_members WHERE user_id = :uid AND project_id = :pid",
                {"uid": user_id, "pid": project_id},
            )
            row = result.fetchone()
            role = row.role if row else None

        if self._redis:
            try:
                await self._redis.set(cache_key, role or "NONE", ex=_ROLE_CACHE_TTL)
            except Exception:
                pass

        return role

    async def is_admin(self, user_id: str, project_id: str | None = None, tenant_role: str | None = None) -> bool:
        """
        A8Y1F2: True if user is owner or manager.
        Checks project role if project_id given; falls back to tenant role.
        """
        if tenant_role in ("owner", "manager"):
            return True

        if project_id:
            role = await self.get_project_role(user_id, project_id)
            return role in ("owner", "manager")

        return False

    async def require_admin(self, ctx: dict) -> bool:
        """
        A8Y1F3: Verify admin role from bot context. Sends error message if not admin.
        Returns True if admin, False if not.
        """
        bot_ctx = ctx.get("bot_ctx") or {}
        user_id = str(bot_ctx.get("user_id", ""))
        project_id = str(bot_ctx.get("project_id", ""))
        tenant_role = bot_ctx.get("role")

        is_admin = await self.is_admin(user_id, project_id, tenant_role)
        if not is_admin:
            chat_id = ctx.get("chat_id")
            client = ctx.get("client")
            locale = ctx.get("locale", "bn")
            if chat_id and client:
                from apps.api.app.services.i18n_service import t
                await client.send_message(chat_id, t("admin.no_permission", locale))
        return is_admin

    async def invalidate_role_cache(self, user_id: str, project_id: str) -> None:
        """Invalidate cached role (call after role changes)."""
        if self._redis:
            try:
                await self._redis.delete(f"{_ROLE_CACHE_PREFIX}{user_id}:{project_id}")
            except Exception:
                pass
