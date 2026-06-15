# ID: AX15      |  Local: A4Y2          |  Module: X05 (M04)
# Functions: A4Y2F1
# Processes: XN02
from __future__ import annotations

import logging
import time
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import RedisError

logger = logging.getLogger("ayzen.telegram.rate_limit")

# Limits per action type
LIMITS: dict[str, tuple[int, int]] = {
    "update": (20, 60),        # 20 per 60s
    "wizard_input": (5, 60),   # 5 per 60s
    "broadcast": (1, 600),     # 1 per 600s (10 min)
}


class TelegramRateLimiter:
    """Sliding window rate limiter using Redis sorted sets."""

    def __init__(self, redis: aioredis.Redis | None) -> None:
        self._redis = redis

    def _key(self, telegram_user_id: int, action_type: str) -> str:
        return f"ayzen:rl:{action_type}:{telegram_user_id}"

    async def check(
        self,
        telegram_user_id: int,
        action_type: str = "update",
        is_admin: bool = False,
    ) -> bool:
        """
        Returns True if request is allowed, False if rate limited.
        Admin role is exempt from rate limits.
        """
        if is_admin and action_type != "broadcast":
            return True

        if not self._redis:
            return True  # Redis down → allow through

        limit, window = LIMITS.get(action_type, LIMITS["update"])
        key = self._key(telegram_user_id, action_type)
        now = time.time()
        window_start = now - window

        try:
            pipe = self._redis.pipeline()
            # Remove expired entries
            pipe.zremrangebyscore(key, "-inf", window_start)
            # Count remaining in window
            pipe.zcard(key)
            # Add current timestamp
            pipe.zadd(key, {str(now): now})
            # Set TTL
            pipe.expire(key, window + 5)
            results = await pipe.execute()

            count = results[1]  # count before adding current
            if count >= limit:
                logger.info("Rate limited uid=%d action=%s count=%d limit=%d", telegram_user_id, action_type, count, limit)
                return False
            return True
        except RedisError as exc:
            logger.warning("Rate limit Redis error: %s — allowing through", exc)
            return True

    async def get_remaining(self, telegram_user_id: int, action_type: str = "update") -> int:
        """Returns remaining allowed requests in current window."""
        if not self._redis:
            return 999
        limit, window = LIMITS.get(action_type, LIMITS["update"])
        key = self._key(telegram_user_id, action_type)
        now = time.time()
        window_start = now - window
        try:
            await self._redis.zremrangebyscore(key, "-inf", window_start)
            count = await self._redis.zcard(key)
            return max(0, limit - count)
        except RedisError:
            return limit
