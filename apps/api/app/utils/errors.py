# ID: AX91      |  Local: A68Y1         |  Module: X72 (M71)
# Functions: A68Y1F1 A68Y1F2 A68Y1F3 A68Y1F4
# Processes: XN01 XN02 XN03 XN04
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("ayzen.errors")


class AyzenError(Exception):
    """Base AYZEN application error."""
    status_code: int = 500
    detail: str = "internal_error"
    log_level: int = logging.ERROR

    def __init__(self, detail: str | None = None, **kwargs: Any) -> None:
        super().__init__(detail or self.detail)
        if detail:
            self.detail = detail
        for k, v in kwargs.items():
            setattr(self, k, v)


class NotFoundError(AyzenError):
    """A68Y1F1: Resource not found."""
    status_code = 404
    detail = "not_found"
    log_level = logging.DEBUG


class UnauthorizedError(AyzenError):
    """A68Y1F2: Authentication required."""
    status_code = 401
    detail = "unauthorized"
    log_level = logging.WARNING


class ForbiddenError(AyzenError):
    """A68Y1F3: Permission denied."""
    status_code = 403
    detail = "forbidden"
    log_level = logging.WARNING


class ConflictError(AyzenError):
    """A68Y1F4: Duplicate submission or conflict."""
    status_code = 409
    detail = "conflict"
    log_level = logging.DEBUG


class ValidationError(AyzenError):
    """Input validation failed."""
    status_code = 422
    detail = "validation_error"
    log_level = logging.DEBUG


class RateLimitError(AyzenError):
    """Rate limit exceeded."""
    status_code = 429
    detail = "rate_limited"
    log_level = logging.DEBUG


# FastAPI exception handlers

async def ayzen_error_handler(request: Request, exc: AyzenError) -> JSONResponse:
    """Convert AyzenError subclasses to JSON responses."""
    logger.log(exc.log_level, "AyzenError %s on %s: %s", type(exc).__name__, request.url, exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "type": type(exc).__name__},
    )


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Log and format HTTPExceptions."""
    if exc.status_code >= 500:
        logger.error("HTTP %d on %s: %s", exc.status_code, request.url, exc.detail)
    else:
        logger.debug("HTTP %d on %s: %s", exc.status_code, request.url, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


def register_error_handlers(app: Any) -> None:
    """Register all error handlers on FastAPI app."""
    app.add_exception_handler(AyzenError, ayzen_error_handler)
    app.add_exception_handler(HTTPException, http_error_handler)
