# ID: AX25      |  Local: A9Y2          |  Module: X09 (M08)
# Functions: A9Y2F1 A9Y2F2 A9Y2F3 A9Y2F4
# Processes: XN01 XN02 XN03
from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import RedisError

logger = logging.getLogger("ayzen.user_settings")

_SETTINGS_CACHE_TTL = 60
_SETTINGS_CACHE_PREFIX = "ayzen:settings:tg:"


class UserSettingsService:
    """Manages per-user settings stored in user_settings table."""

    def __init__(self, redis: aioredis.Redis | None, db_session_factory: Any) -> None:
        self._redis = redis
        self._db = db_session_factory

    def _cache_key(self, telegram_user_id: int) -> str:
        return f"{_SETTINGS_CACHE_PREFIX}{telegram_user_id}"

    async def _invalidate(self, telegram_user_id: int) -> None:
        if self._redis:
            try:
                await self._redis.delete(self._cache_key(telegram_user_id))
            except RedisError:
                pass

    # XN01  Get or Create Settings
    async def get_or_create(self, telegram_user_id: int) -> dict:
        """Load user settings with Redis cache, or create defaults if missing."""
        if self._redis:
            try:
                cached = await self._redis.get(self._cache_key(telegram_user_id))
                if cached:
                    return json.loads(cached)
            except RedisError:
                pass

        async with self._db() as session:
            result = await session.execute(
                """
                SELECT u.id as user_id,
                       COALESCE(us.locale, 'bn') as locale,
                       COALESCE(us.notify_deadline, true) as notify_deadline,
                       COALESCE(us.notify_assignment, true) as notify_assignment,
                       COALESCE(us.notify_broadcast, true) as notify_broadcast,
                       us.quiet_hours_start, us.quiet_hours_end
                FROM users u
                LEFT JOIN user_settings us ON us.user_id = u.id
                WHERE u.telegram_user_id = :tid
                """,
                {"tid": telegram_user_id},
            )
            row = result.fetchone()
            if not row:
                return {"locale": "bn", "notify_deadline": True, "notify_assignment": True, "notify_broadcast": True}

            user_id = row.user_id
            settings = {
                "user_id": str(user_id),
                "locale": row.locale,
                "notify_deadline": row.notify_deadline,
                "notify_assignment": row.notify_assignment,
                "notify_broadcast": row.notify_broadcast,
                "quiet_hours_start": str(row.quiet_hours_start) if row.quiet_hours_start else None,
                "quiet_hours_end": str(row.quiet_hours_end) if row.quiet_hours_end else None,
            }

            # Ensure row exists (UPSERT defaults)
            await session.execute(
                """
                INSERT INTO user_settings (user_id) VALUES (:uid)
                ON CONFLICT (user_id) DO NOTHING
                """,
                {"uid": str(user_id)},
            )
            await session.commit()

        if self._redis:
            try:
                await self._redis.set(self._cache_key(telegram_user_id), json.dumps(settings), ex=_SETTINGS_CACHE_TTL)
            except RedisError:
                pass

        return settings

    # XN02  Update Locale
    async def update_locale(self, telegram_user_id: int, locale: str) -> None:
        if locale not in ("bn", "en"):
            raise ValueError(f"Invalid locale: {locale}")

        async with self._db() as session:
            await session.execute(
                """
                UPDATE user_settings us SET locale = :locale, updated_at = NOW()
                FROM users u
                WHERE us.user_id = u.id AND u.telegram_user_id = :tid
                """,
                {"locale": locale, "tid": telegram_user_id},
            )
            # Also update user_bot_state
            await session.execute(
                "UPDATE user_bot_state SET locale = :locale WHERE telegram_user_id = :tid",
                {"locale": locale, "tid": telegram_user_id},
            )
            await session.commit()

        await self._invalidate(telegram_user_id)

    # XN03  Toggle Notification
    async def toggle_notification(self, telegram_user_id: int, notify_type: str) -> bool:
        """Toggle a notification setting. Returns new state (True = enabled)."""
        valid_types = {"deadline": "notify_deadline", "assignment": "notify_assignment", "broadcast": "notify_broadcast"}
        col = valid_types.get(notify_type)
        if not col:
            raise ValueError(f"Invalid notify type: {notify_type}")

        async with self._db() as session:
            result = await session.execute(
                f"""
                UPDATE user_settings us SET {col} = NOT {col}, updated_at = NOW()
                FROM users u
                WHERE us.user_id = u.id AND u.telegram_user_id = :tid
                RETURNING us.{col}
                """,
                {"tid": telegram_user_id},
            )
            row = result.fetchone()
            await session.commit()

        await self._invalidate(telegram_user_id)
        return row[0] if row else True

    # XN04  Get User Locale (lightweight)
    async def get_locale(self, telegram_user_id: int) -> str:
        """Fast locale lookup — Redis cached."""
        settings = await self.get_or_create(telegram_user_id)
        return settings.get("locale", "bn")
