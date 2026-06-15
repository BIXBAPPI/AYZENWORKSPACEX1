# ID: AX20      |  Local: A6Y1          |  Module: X07 (M06)
# Functions: A6Y1F1 A6Y1F2 A6Y1F3 A6Y1F4
# Processes: XN01 XN02 XN03 XN04
from __future__ import annotations

import logging
import secrets
import string
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis
from redis.exceptions import RedisError

logger = logging.getLogger("ayzen.bot_user")

_LINK_CODE_TTL = 600  # 10 minutes
_LINK_KEY_PREFIX = "ayzen:link:"
_USER_TG_CACHE_PREFIX = "ayzen:user:tg:"
_USER_TG_CACHE_TTL = 60


class BotUserService:
    """Handles Telegram account linking/unlinking to AYZEN web accounts."""

    def __init__(self, redis: aioredis.Redis | None, db_session_factory: Any) -> None:
        self._redis = redis
        self._db = db_session_factory

    # XN01  Link Code Generation
    async def generate_link_code(self, user_id: UUID) -> str:
        """
        Generate 8-char alphanumeric token.
        Redis SET ayzen:link:{token} = user_id TTL=600s. Single-use.
        """
        alphabet = string.ascii_letters + string.digits
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        key = f"{_LINK_KEY_PREFIX}{code}"

        if self._redis:
            await self._redis.set(key, str(user_id), ex=_LINK_CODE_TTL)
        else:
            # Fallback: store in DB (link_codes table or user pending_link_code column)
            async with self._db() as session:
                await session.execute(
                    "UPDATE users SET pending_link_code = :code, pending_link_expires = NOW() + INTERVAL '10 minutes' WHERE id = :uid",
                    {"code": code, "uid": str(user_id)},
                )
                await session.commit()

        logger.info("Link code generated for user_id=%s", user_id)
        return code

    # XN02  Link Validation & DB Bind
    async def validate_and_link(
        self,
        telegram_user_id: int,
        telegram_username: str | None,
        code: str,
    ) -> dict | None:
        """
        Validates code, links Telegram account to web user.
        Returns user dict on success, None if invalid/expired.
        """
        key = f"{_LINK_KEY_PREFIX}{code}"
        user_id_str: str | None = None

        if self._redis:
            try:
                user_id_str = await self._redis.get(key)
                if user_id_str:
                    await self._redis.delete(key)  # single-use
            except RedisError as exc:
                logger.warning("Redis error on link code lookup: %s", exc)

        if not user_id_str:
            # Try DB fallback
            async with self._db() as session:
                result = await session.execute(
                    """
                    SELECT id FROM users
                    WHERE pending_link_code = :code
                      AND pending_link_expires > NOW()
                    """,
                    {"code": code},
                )
                row = result.fetchone()
                if row:
                    user_id_str = str(row.id)
                    await session.execute(
                        "UPDATE users SET pending_link_code = NULL, pending_link_expires = NULL WHERE id = :uid",
                        {"uid": user_id_str},
                    )
                    await session.commit()

        if not user_id_str:
            return None

        # Link telegram_id to user
        async with self._db() as session:
            await session.execute(
                """
                UPDATE users SET
                    telegram_user_id = :tuid,
                    telegram_username = :tusername,
                    updated_at = NOW()
                WHERE id = :uid
                """,
                {"tuid": telegram_user_id, "tusername": telegram_username, "uid": user_id_str},
            )
            await session.commit()

            result = await session.execute(
                "SELECT id, email, full_name, tenant_id, role FROM users WHERE id = :uid",
                {"uid": user_id_str},
            )
            user = result.fetchone()

        # Invalidate user cache
        if self._redis:
            try:
                await self._redis.delete(f"{_USER_TG_CACHE_PREFIX}{telegram_user_id}")
            except RedisError:
                pass

        logger.info("Linked telegram_user_id=%d to user_id=%s", telegram_user_id, user_id_str)
        return dict(user._mapping) if user else None

    # XN03  User Lookup by Telegram ID
    async def get_user_by_telegram_id(self, telegram_user_id: int) -> dict | None:
        """
        SELECT user WHERE telegram_id=?
        Cache ayzen:user:tg:{tid} TTL=60s.
        """
        cache_key = f"{_USER_TG_CACHE_PREFIX}{telegram_user_id}"

        if self._redis:
            try:
                import json
                cached = await self._redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except RedisError:
                pass

        async with self._db() as session:
            result = await session.execute(
                """
                SELECT u.id, u.email, u.full_name, u.tenant_id, u.role,
                       u.telegram_user_id, u.telegram_username
                FROM users u
                WHERE u.telegram_user_id = :tid
                """,
                {"tid": telegram_user_id},
            )
            row = result.fetchone()
            if not row:
                return None
            user = dict(row._mapping)

        if self._redis:
            try:
                import json
                await self._redis.set(cache_key, json.dumps(user, default=str), ex=_USER_TG_CACHE_TTL)
            except RedisError:
                pass

        return user

    # XN04  Unlink Flow
    async def unlink(self, user_id: UUID) -> None:
        """
        Clear telegram_user_id from user. Delete bot state. Audit log.
        """
        # Get telegram_user_id first (for state cleanup)
        async with self._db() as session:
            result = await session.execute(
                "SELECT telegram_user_id FROM users WHERE id = :uid",
                {"uid": str(user_id)},
            )
            row = result.fetchone()
            tuid = row.telegram_user_id if row else None

            await session.execute(
                """
                UPDATE users SET
                    telegram_user_id = NULL,
                    telegram_username = NULL,
                    updated_at = NOW()
                WHERE id = :uid
                """,
                {"uid": str(user_id)},
            )
            await session.commit()

        if tuid and self._redis:
            try:
                from apps.api.app.services.bot_state_service import BotStateService
                state_svc = BotStateService(self._redis, self._db)
                await state_svc.clear(tuid)
                await self._redis.delete(f"{_USER_TG_CACHE_PREFIX}{tuid}")
            except Exception as exc:
                logger.warning("Error clearing bot state on unlink: %s", exc)

        logger.info("Unlinked user_id=%s (telegram_user_id=%s)", user_id, tuid)
