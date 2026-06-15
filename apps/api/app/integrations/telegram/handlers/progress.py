# ID: AX39      |  Local: A22Y1         |  Module: X23 (M22)
# Functions: A22Y1F1 A22Y1F2
# Processes: XN01 XN02
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.progress")


async def progress_handler(update: dict, ctx: dict) -> None:
    """A22Y1F1: Show user's progress summary for active project."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
    if not bot_ctx:
        await client.send_message(chat_id, t("error.not_linked", locale))
        return

    locale = bot_ctx.get("locale", "bn")
    user_id = bot_ctx.get("user_id")
    tenant_id = bot_ctx.get("tenant_id")
    project_id = bot_ctx.get("project_id")
    project_name = bot_ctx.get("project_name", "—")

    if not project_id:
        await client.send_message(chat_id, t("project.empty", locale))
        return

    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
        result = await session.execute(
            """
            SELECT
                COUNT(DISTINCT tc.id) as completed_tasks,
                COALESCE(SUM(tc.points_earned), 0) as total_points,
                COUNT(DISTINCT t.id) as total_tasks,
                COUNT(DISTINCT tc.id) FILTER (WHERE DATE(tc.completed_at) = CURRENT_DATE) as today_completed,
                COALESCE(SUM(tc.points_earned) FILTER (WHERE DATE(tc.completed_at) = CURRENT_DATE), 0) as today_points
            FROM tasks t
            LEFT JOIN task_completions tc ON tc.task_id = t.id AND tc.user_id = :uid
            WHERE t.project_id = :pid AND t.archived_at IS NULL
            """,
            {"uid": str(user_id), "pid": str(project_id)},
        )
        row = result.fetchone()

    if not row or row.total_tasks == 0:
        await client.send_message(chat_id, t("progress.header", locale, project_name=escape_md(project_name))
                                   + "\n\n" + t("progress.no_data", locale))
        return

    pct = int((row.completed_tasks / max(row.total_tasks, 1)) * 100)
    bar_filled = pct // 10
    progress_bar = "█" * bar_filled + "░" * (10 - bar_filled)

    text = (
        t("progress.header", locale, project_name=escape_md(project_name)) + "\n\n"
        + f"📊 `{progress_bar}` {pct}%\n\n"
        + t("progress.total_done", locale, count=row.completed_tasks) + "\n"
        + t("progress.points_today", locale, points=int(row.today_points)) + "\n"
        + f"💰 Total: {int(row.total_points)} points"
    )

    keyboard = InlineKeyboards.from_rows([
        [
            InlineKeyboards.button("🏆 Leaderboard", "menu:leaderboard"),
            InlineKeyboards.button(t("button.refresh", locale), "menu:progress"),
        ],
        [InlineKeyboards.button(t("button.menu", locale), "menu:main")],
    ])

    await client.send_message(chat_id, text, reply_markup=keyboard)
