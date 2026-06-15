# ID: AX56      |  Local: A37Y1         |  Module: X39 (M38)
# Functions: A37Y1F1 A37Y1F2 A37Y1F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("ayzen.health")


class HealthService:
    """System health checks for all dependencies."""

    def __init__(self, redis: Any | None, db_session_factory: Any) -> None:
        self._redis = redis
        self._db = db_session_factory

    async def check_database(self) -> dict:
        """A37Y1F1: Ping the database."""
        try:
            async with self._db() as session:
                result = await session.execute("SELECT 1 as ok")
                row = result.fetchone()
                return {"status": "ok", "latency_ms": 0} if row else {"status": "error"}
        except Exception as exc:
            logger.error("DB health check failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    async def check_redis(self) -> dict:
        """A37Y1F2: Ping Redis."""
        if not self._redis:
            return {"status": "disabled"}
        try:
            import time
            start = time.perf_counter()
            await self._redis.ping()
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {"status": "ok", "latency_ms": latency}
        except Exception as exc:
            logger.warning("Redis health check failed: %s", exc)
            return {"status": "error", "error": str(exc)}

    async def check_telegram(self) -> dict:
        """A37Y1F3: Test Telegram API connectivity via getMe."""
        try:
            from apps.api.app.integrations.telegram.client import get_telegram_client
            client = get_telegram_client()
            resp = await client._request("getMe", {})
            if resp.get("ok"):
                return {"status": "ok", "bot": resp.get("result", {}).get("username")}
            return {"status": "error"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    async def full_check(self) -> dict:
        """Run all health checks in parallel and aggregate."""
        import asyncio
        db_result, redis_result, tg_result = await asyncio.gather(
            self.check_database(),
            self.check_redis(),
            self.check_telegram(),
        )
        all_ok = all(r.get("status") in ("ok", "disabled") for r in [db_result, redis_result, tg_result])
        return {
            "status": "ok" if all_ok else "degraded",
            "checks": {
                "database": db_result,
                "redis": redis_result,
                "telegram": tg_result,
            },
        }
