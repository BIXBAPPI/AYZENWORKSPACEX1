# ID: AX38      |  Local: A21Y1         |  Module: X22 (M21)
# Functions: A21Y1F1 A21Y1F2
# Processes: XN01 XN02
from __future__ import annotations

import logging
from datetime import date

from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.status")


async def status_handler(update: dict, ctx: dict) -> None:
    """A21Y1F1: /status — show today's summary (works in stateless mode too)."""
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

    today = date.today()

    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")

        # Today's completions
        result = await session.execute(
            """
            SELECT COUNT(*) as done_count, COALESCE(SUM(points_earned), 0) as total_points
            FROM task_completions
            WHERE user_id = :uid
              AND DATE(completed_at) = :today
            """,
            {"uid": str(user_id), "today": today},
        )
        row = result.fetchone()
        done_count = row.done_count if row else 0
        total_points = int(row.total_points) if row else 0

        # Streak
        streak_result = await session.execute(
            """
            WITH daily AS (
                SELECT DISTINCT DATE(completed_at) as completion_date
                FROM task_completions WHERE user_id = :uid
                ORDER BY completion_date DESC
            )
            SELECT COUNT(*) FROM (
                SELECT completion_date,
                       ROW_NUMBER() OVER (ORDER BY completion_date DESC) as rn
                FROM daily
                WHERE completion_date <= CURRENT_DATE
            ) sub
            WHERE completion_date = CURRENT_DATE - INTERVAL '1 day' * (rn - 1)
            """,
            {"uid": str(user_id)},
        )
        streak_row = streak_result.fetchone()
        streak = int(streak_row[0]) if streak_row else 0

    text = t("status.today_header", locale) + "\n\n" + t(
        "status.summary_template", locale,
        date=escape_md(today.strftime("%Y-%m-%d")),
        done=done_count,
        points=total_points,
        streak=streak,
        project_name=escape_md(project_name),
    )

    if streak > 0:
        text += "\n\n" + t("status.streak", locale, streak=streak)

    keyboard = InlineKeyboards.from_rows([
        [
            InlineKeyboards.button("📊 Progress", "menu:progress"),
            InlineKeyboards.button(t("button.menu", locale), "menu:main"),
        ]
    ])

    await client.send_message(chat_id, text, reply_markup=keyboard)
