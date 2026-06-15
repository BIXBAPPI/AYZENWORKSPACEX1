# ID: AX62      |  Local: A39Y1         |  Module: X43 (M42)
# Functions: A39Y1F1 A39Y1F2 A39Y1F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("ayzen.rate_limiter")

_RATE_LIMIT_PATHS = {
    "/api/v1/auth/login": (5, 300),       # 5 per 5 min
    "/api/v1/auth/register": (3, 3600),   # 3 per hour
    "/api/v1/broadcasts/": (2, 600),      # 2 per 10 min
}


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    A39Y1F1: HTTP-level rate limiter using Redis sliding window.
    Applied to auth and broadcast endpoints by path.
    Falls back to allowing through if Redis unavailable.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        redis = getattr(request.app.state, "redis", None)

        for route_prefix, (limit, window) in _RATE_LIMIT_PATHS.items():
            if path.startswith(route_prefix):
                if redis:
                    ip = request.client.host if request.client else "unknown"
                    key = f"ayzen:http_rl:{path}:{ip}"
                    now = time.time()
                    window_start = now - window

                    try:
                        pipe = redis.pipeline()
                        pipe.zremrangebyscore(key, "-inf", window_start)
                        pipe.zcard(key)
                        pipe.zadd(key, {str(now): now})
                        pipe.expire(key, window + 5)
                        results = await pipe.execute()
                        count = results[1]

                        if count >= limit:
                            retry_after = int(window - (now - window_start))
                            return Response(
                                content='{"detail":"rate_limited"}',
                                status_code=429,
                                headers={
                                    "Content-Type": "application/json",
                                    "Retry-After": str(retry_after),
                                },
                            )
                    except Exception as exc:
                        logger.warning("Rate limiter Redis error: %s", exc)
                break

        return await call_next(request)
