from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as aioredis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("ayzen")

engine = None
session_factory: async_sessionmaker | None = None
redis_client = None
scheduler: AsyncIOScheduler | None = None


def _fix_db_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global engine, session_factory, redis_client, scheduler

    # FIX #3: Provide clearer error if DATABASE_URL is missing
    db_url_raw = os.environ.get("DATABASE_URL")
    if not db_url_raw:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Add it to .replit [userenv.shared] or your server environment. "
            "Get it from Supabase → Project Settings → Database → Connection string (URI)."
        )

    database_url = _fix_db_url(db_url_raw)
    engine = create_async_engine(database_url, pool_size=10, max_overflow=20, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    app.state.db = session_factory
    logger.info("Database connected")

    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        app.state.redis = redis_client
        logger.info("Redis connected")
    except Exception as exc:
        logger.warning("Redis unavailable — stateless mode: %s", exc)
        app.state.redis = None

    scheduler = AsyncIOScheduler()
    _register_jobs(scheduler)
    scheduler.start()
    logger.info("Scheduler started")

    # Auto-register Telegram webhook
    import httpx
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    replit_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
    if bot_token and replit_domain:
        webhook_url = f"https://{replit_domain}/api/v1/bot/webhook"
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/setWebhook",
                    json={"url": webhook_url, "secret_token": os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")}
                )
                logger.info(f"Telegram webhook set: {r.json()}")
        except Exception as e:
            logger.warning(f"Webhook setup failed: {e}")

    yield

    scheduler.shutdown(wait=False)
    if redis_client:
        await redis_client.aclose()
    if engine:
        await engine.dispose()
    logger.info("AYZEN shutdown complete")


def _register_jobs(scheduler: AsyncIOScheduler) -> None:
    from apps.api.app.jobs.deadline_reminder import run as deadline_run
    from apps.api.app.jobs.daily_digest import run as digest_run
    from apps.api.app.jobs.analytics_job import run as analytics_run
    from apps.api.app.jobs.stale_user_job import run as stale_run
    from apps.api.app.jobs.quiet_queue_job import run as quiet_run

    scheduler.add_job(deadline_run, "interval", minutes=15, id="deadline_reminder")
    scheduler.add_job(digest_run, "cron", hour=8, minute=0, id="daily_digest")
    scheduler.add_job(analytics_run, "cron", hour=2, minute=0, id="analytics_snapshot")
    scheduler.add_job(stale_run, "cron", hour=3, minute=0, id="stale_user")
    scheduler.add_job(quiet_run, "interval", minutes=5, id="quiet_queue_flush")


def create_app() -> FastAPI:
    # FIX #5: Build CORS origins list including ayzen.tech
    cors_origins: list[str] = []
    for val in [
        os.environ.get("CORS_ORIGINS", ""),
        os.environ.get("REPLIT_DOMAINS", ""),
        os.environ.get("REPLIT_DEV_DOMAIN", ""),
    ]:
        for part in val.split(","):
            part = part.strip()
            if part:
                cors_origins.append(f"https://{part}" if not part.startswith("http") else part)
                if not part.startswith("http"):
                    cors_origins.append(f"http://{part}")

    # FIX #5: Always include production domain and localhost variants
    cors_origins += [
        "https://ayzen.tech",
        "https://www.ayzen.tech",
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:80",
        "http://localhost",
    ]
    cors_origins = list(set(filter(None, cors_origins)))

    app = FastAPI(
        title="AYZEN API",
        version="5.0.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        # FIX #5: Updated regex to also match ayzen.tech subdomains
        allow_origin_regex=r"https://.*\.(replit\.dev|replit\.app|repl\.co|ayzen\.tech)",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "X-Internal-Webhook-Token"],
    )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s", request.url)
        return JSONResponse(status_code=500, content={"detail": "internal_error"})

    from apps.api.app.integrations.telegram.webhook import router as telegram_router
    from apps.api.app.routers.auth import router as auth_router
    from apps.api.app.routers.projects import router as projects_router
    from apps.api.app.routers.tasks import router as tasks_router
    from apps.api.app.routers.members import router as members_router
    from apps.api.app.routers.progress import router as progress_router
    from apps.api.app.routers.analytics import router as analytics_router
    from apps.api.app.routers.broadcasts import router as broadcasts_router
    from apps.api.app.routers.exports import router as exports_router
    from apps.api.app.routers.settings import router as settings_router
    from apps.api.app.routers.notifications import router as notifications_router
    from apps.api.app.routers.tma_auth import router as tma_router

    app.include_router(telegram_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(projects_router, prefix="/api/v1/projects", tags=["projects"])
    app.include_router(tasks_router, prefix="/api/v1/tasks", tags=["tasks"])
    app.include_router(members_router, prefix="/api/v1/members", tags=["members"])
    app.include_router(progress_router, prefix="/api/v1/progress", tags=["progress"])
    app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])
    app.include_router(broadcasts_router, prefix="/api/v1/broadcasts", tags=["broadcasts"])
    app.include_router(exports_router, prefix="/api/v1/exports", tags=["exports"])
    app.include_router(settings_router, prefix="/api/v1/settings", tags=["settings"])
    app.include_router(notifications_router, prefix="/api/v1/notifications", tags=["notifications"])
    app.include_router(tma_router, prefix="/api/v1/tma", tags=["tma"])

    @app.get("/api/v1/health", tags=["health"])
    async def health_check() -> dict:
        return {"status": "ok", "version": "5.0.0"}

    # FIX #7: Also register /healthz alias to match OpenAPI spec and generated client
    @app.get("/api/v1/healthz", tags=["health"])
    async def health_check_alias() -> dict:
        return {"status": "ok", "version": "5.0.0"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=port, reload=False)