# ID: AX47      |  Local: A29Y1         |  Module: X30 (M29)
# Functions: A29Y1F1 A29Y1F2
# Processes: XN01 XN02
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.admin.progress")


async def admin_progress_handler(update: dict, ctx: dict) -> None:
    """A29Y1F1: Show project-wide progress snapshot for admin."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    app = ctx.get("app")
    telegram_user_id = ctx["telegram_user_id"]

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    from apps.api.app.services.bot_context_service import BotContextService
    bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
    if not bot_ctx or not bot_ctx.get("project_id"):
        await client.send_message(chat_id, t("project.empty", locale))
        return

    tenant_id = bot_ctx["tenant_id"]
    project_id = bot_ctx["project_id"]
    project_name = bot_ctx.get("project_name", "—")

    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
        result = await session.execute(
            """
            SELECT
                COUNT(DISTINCT t.id) as total_tasks,
                COUNT(DISTINCT tc.id) as total_completions,
                COUNT(DISTINCT tc.user_id) as active_users,
                COALESCE(SUM(tc.points_earned), 0) as total_points,
                COUNT(DISTINCT tc.id) FILTER (WHERE DATE(tc.completed_at) = CURRENT_DATE) as today_done
            FROM tasks t
            LEFT JOIN task_completions tc ON tc.task_id = t.id
            WHERE t.project_id = :pid AND t.archived_at IS NULL
            """,
            {"pid": str(project_id)},
        )
        row = result.fetchone()

    if not row:
        await client.send_message(chat_id, "📈 No data yet.")
        return

    text = (
        f"📈 *Project Progress*\n"
        f"📌 {escape_md(project_name)}\n\n"
        f"📋 Total tasks: {row.total_tasks}\n"
        f"✅ Total completions: {row.total_completions}\n"
        f"👥 Active users: {row.active_users}\n"
        f"💰 Total points: {int(row.total_points)}\n"
        f"📅 Today's completions: {row.today_done}"
    )

    keyboard = InlineKeyboards.from_rows([
        [InlineKeyboards.button("◀ Admin Panel", "admin:panel")],
        [InlineKeyboards.button(t("button.menu", locale), "menu:main")],
    ])

    await client.send_message(chat_id, text, reply_markup=keyboard)
