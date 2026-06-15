# ID: AX16      |  Local: A4Y3          |  Module: X05 (M04)
# Functions: A4Y3F1
# Processes: XN03
from __future__ import annotations

import logging
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import RedisError

logger = logging.getLogger("ayzen.telegram.idempotency")

IDEMPOTENCY_TTL = 60  # seconds


class IdempotencyGuard:
    """
    Deduplicates Telegram callback queries.
    callback_query.id is unique per click — stored in Redis for 60s.
    Also writes to bot_idempotency DB table as persistent record.
    pg_cron deletes rows older than 5 minutes.
    """

    def __init__(self, redis: aioredis.Redis | None, db_session_factory: Any = None) -> None:
        self._redis = redis
        self._db = db_session_factory

    def _key(self, callback_id: str) -> str:
        return f"ayzen:idempotent:{callback_id}"

    async def check_and_mark(self, callback_id: str, user_id: str | None = None) -> bool:
        """
        Returns True if the callback is new (not yet processed).
        Returns False if it's a duplicate (already processed).
        Marks it as processed atomically.
        """
        if not self._redis:
            # No Redis — fall back to DB check
            return await self._db_check_and_mark(callback_id, user_id)

        key = self._key(callback_id)
        try:
            # SET NX (only if not exists) with TTL
            result = await self._redis.set(key, "1", nx=True, ex=IDEMPOTENCY_TTL)
            if result is None:
                # Already exists — duplicate
                logger.debug("Duplicate callback_id=%s dropped", callback_id)
                return False

            # Also write to DB for audit trail (best effort)
            if self._db and user_id:
                try:
                    async with self._db() as session:
                        await session.execute(
                            """
                            INSERT INTO bot_idempotency (callback_id, user_id, processed_at)
                            VALUES (:cid, :uid, NOW())
                            ON CONFLICT (callback_id) DO NOTHING
                            """,
                            {"cid": callback_id, "uid": user_id},
                        )
                        await session.commit()
                except Exception as exc:
                    logger.debug("Idempotency DB write failed: %s", exc)

            return True
        except RedisError as exc:
            logger.warning("Idempotency Redis error: %s — falling back to DB", exc)
            return await self._db_check_and_mark(callback_id, user_id)

    async def _db_check_and_mark(self, callback_id: str, user_id: str | None) -> bool:
        if not self._db:
            return True  # No DB either — allow
        try:
            async with self._db() as session:
                result = await session.execute(
                    """
                    INSERT INTO bot_idempotency (callback_id, user_id, processed_at)
                    VALUES (:cid, :uid, NOW())
                    ON CONFLICT (callback_id) DO NOTHING
                    RETURNING callback_id
                    """,
                    {"cid": callback_id, "uid": user_id},
                )
                await session.commit()
                row = result.fetchone()
                return row is not None  # True if inserted (new), False if conflict (duplicate)
        except Exception as exc:
            logger.warning("Idempotency DB fallback error: %s", exc)
            return True  # Allow on error
