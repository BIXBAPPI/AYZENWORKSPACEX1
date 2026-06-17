"""Telemetry — error logs, API call logs, function tracking."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.telemetry")
router = APIRouter()


async def _admin(request: Request):
    from apps.api.app.middleware.auth import verify_token, require_admin
    user = await verify_token(request)
    await require_admin(user)
    return user


class FrontendErrorLog(BaseModel):
    level: str = "error"
    function_name: str | None = None
    route: str | None = None
    error_type: str | None = None
    message: str | None = None
    stack_trace: str | None = None


@router.get("/errors")
async def get_errors(request: Request, limit: int = 100) -> list[dict]:
    await _admin(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("""
                SELECT el.id, el.timestamp, el.level, el.function_name, el.route,
                       el.error_type, el.message, el.stack_trace, u.email AS user_email
                FROM error_logs el
                LEFT JOIN users u ON u.id = el.user_id
                ORDER BY el.timestamp DESC
                LIMIT :lim
            """),
            {"lim": min(limit, 500)}
        )
        rows = r.mappings().fetchall()
        return [
            {
                "id": str(row["id"]),
                "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                "level": row["level"],
                "function_name": row["function_name"],
                "route": row["route"],
                "error_type": row["error_type"],
                "message": row["message"],
                "stack_trace": row["stack_trace"],
                "user_email": row["user_email"],
            }
            for row in rows
        ]


@router.post("/errors")
async def log_frontend_error(body: FrontendErrorLog, request: Request) -> dict:
    """Log errors from the frontend (no auth required)."""
    db = request.app.state.db
    async with db() as session:
        try:
            await session.execute(
                text("""
                    INSERT INTO error_logs (level, function_name, route, error_type, message, stack_trace)
                    VALUES (:level, :fn, :route, :et, :msg, :st)
                """),
                {
                    "level": body.level, "fn": body.function_name, "route": body.route,
                    "et": body.error_type, "msg": body.message, "st": body.stack_trace
                }
            )
            await session.commit()
        except Exception as e:
            logger.error("Failed to log error: %s", e)
    return {"logged": True}


@router.delete("/errors")
async def clear_errors(request: Request) -> dict:
    await _admin(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(text("DELETE FROM error_logs"))
        await session.commit()
        return {"cleared": r.rowcount}


@router.get("/functions")
async def get_function_telemetry(request: Request, search: str | None = None, page: int = 1) -> dict:
    await _admin(request)
    db = request.app.state.db
    async with db() as session:
        where = "WHERE function_name ILIKE :search" if search else ""
        params = {"search": f"%{search}%", "offset": (page - 1) * 25} if search else {"offset": (page - 1) * 25}
        r = await session.execute(
            text(f"""
                SELECT function_name, module, call_count, avg_time_ms, error_count, last_called, last_error,
                       CASE WHEN call_count > 0 THEN ROUND(error_count::NUMERIC / call_count * 100, 1) ELSE 0 END AS error_rate
                FROM function_telemetry
                {where}
                ORDER BY call_count DESC
                LIMIT 25 OFFSET :offset
            """),
            params
        )
        rows = r.mappings().fetchall()

        count_r = await session.execute(
            text(f"SELECT COUNT(*) FROM function_telemetry {where}"),
            {"search": f"%{search}%"} if search else {}
        )
        total = count_r.scalar() or 0

        return {
            "data": [dict(row) for row in rows],
            "total": total,
            "page": page,
            "pages": max(1, (total + 24) // 25),
        }


@router.get("/api-calls")
async def get_api_calls(request: Request, limit: int = 50) -> list[dict]:
    await _admin(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("""
                SELECT id, timestamp, method, path, status_code, response_time_ms, user_email, ip_address
                FROM api_call_logs
                ORDER BY timestamp DESC
                LIMIT :lim
            """),
            {"lim": min(limit, 200)}
        )
        rows = r.mappings().fetchall()
        return [
            {
                "id": str(row["id"]),
                "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                "method": row["method"],
                "path": row["path"],
                "status_code": row["status_code"],
                "response_time_ms": row["response_time_ms"],
                "user_email": row["user_email"],
                "ip_address": row["ip_address"],
            }
            for row in rows
        ]
