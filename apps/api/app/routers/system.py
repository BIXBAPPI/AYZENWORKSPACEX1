from __future__ import annotations
import logging, os, platform, sys, time
from fastapi import APIRouter, Request
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.system")
router = APIRouter()
_START_TIME = time.time()

SENSITIVE_KEYS = {"DATABASE_URL","SESSION_SECRET","TELEGRAM_BOT_TOKEN","TELEGRAM_WEBHOOK_SECRET","INTERNAL_WEBHOOK_TOKEN","RESEND_API_KEY","REDIS_URL"}
DISPLAY_KEYS = ["DATABASE_URL","SESSION_SECRET","TELEGRAM_BOT_TOKEN","TELEGRAM_WEBHOOK_SECRET","INTERNAL_WEBHOOK_TOKEN","CORS_ORIGINS","NODE_ENV","PYTHON_ENV","REDIS_URL","BOT_USERNAME","REPLIT_DOMAINS","REPLIT_DEV_DOMAIN"]


async def _auth_admin(request: Request):
    from apps.api.app.middleware.auth import verify_token, require_admin
    user = await verify_token(request)
    await require_admin(user)
    return user


@router.get("/developer")
async def developer_info(request: Request) -> dict:
    await _auth_admin(request)
    env_vars = [
        {"key": k, "value": "***" if k in SENSITIVE_KEYS and os.environ.get(k) else (os.environ.get(k) or "(not set)"),
         "is_set": bool(os.environ.get(k)), "sensitive": k in SENSITIVE_KEYS}
        for k in DISPLAY_KEYS
    ]
    db = request.app.state.db
    table_counts, db_connected = [], False
    try:
        async with db() as session:
            db_connected = True
            for tbl in ["users","tenants","projects","tasks","task_completions","project_members","notifications","broadcasts"]:
                try:
                    r = await session.execute(text(f"SELECT COUNT(*) AS cnt FROM {tbl}"))
                    row = r.fetchone()
                    table_counts.append({"table": tbl, "rows": row.cnt if row else 0})
                except Exception:
                    table_counts.append({"table": tbl, "rows": -1})
    except Exception as e:
        logger.warning("DB count error: %s", e)
    return {
        "env_vars": env_vars,
        "python": {"version": sys.version, "venv_path": "/home/runner/workspace/.venv"},
        "db": {"connected": db_connected, "table_counts": table_counts},
        "telegram": {
            "bot_token_set": bool(os.environ.get("TELEGRAM_BOT_TOKEN")),
            "bot_username": os.environ.get("BOT_USERNAME", "(not set)"),
            "webhook_secret_set": bool(os.environ.get("TELEGRAM_WEBHOOK_SECRET")),
        },
    }


@router.get("/health/telemetry")
async def health_telemetry(request: Request) -> dict:
    await _auth_admin(request)
    uptime_seconds = int(time.time() - _START_TIME)
    mem = {}
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        mem = {"rss_mb": round(usage.ru_maxrss / 1024, 1)}
    except Exception:
        pass
    db = request.app.state.db
    db_status, db_latency_ms, table_counts = False, -1, []
    try:
        async with db() as session:
            t0 = time.monotonic()
            await session.execute(text("SELECT 1"))
            db_latency_ms = round((time.monotonic() - t0) * 1000, 2)
            db_status = True
            for tbl in ["users","tenants","projects","tasks","task_completions","project_members","notifications","broadcasts"]:
                try:
                    r = await session.execute(text(f"SELECT COUNT(*) AS cnt FROM {tbl}"))
                    row = r.fetchone()
                    table_counts.append({"table": tbl, "rows": row.cnt if row else 0})
                except Exception:
                    table_counts.append({"table": tbl, "rows": -1})
    except Exception as e:
        logger.warning("Telemetry DB error: %s", e)
    routes = []
    try:
        from apps.api.main import app as fastapi_app
        for route in fastapi_app.routes:
            if hasattr(route, "methods") and hasattr(route, "path"):
                for method in route.methods:
                    routes.append({"method": method, "path": route.path, "name": getattr(route, "name", "")})
    except Exception:
        pass
    return {
        "server": {"uptime_seconds": uptime_seconds, "python_version": sys.version, "platform": platform.system(), "arch": platform.machine(), "node_env": os.environ.get("NODE_ENV", "development")},
        "memory": mem,
        "db": {"connected": db_status, "latency_ms": db_latency_ms, "table_counts": table_counts},
        "ports": {"node_api": 8080, "python_api": 8000},
        "routes": routes,
    }
