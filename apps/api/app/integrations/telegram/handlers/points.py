# ID: AX41      |  Local: A24Y1         |  Module: X25 (M24)
# Functions: A24Y1F1 A24Y1F2
# Processes: XN01 XN02
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.services.rewards_service import RewardsService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.points")


async def points_handler(update: dict, ctx: dict) -> None:
    """A24Y1F1: Show user's points summary and rank."""
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

    project_id = bot_ctx.get("project_id")
    if not project_id:
        await client.send_message(chat_id, t("project.empty", locale))
        return

    tenant_id = bot_ctx["tenant_id"]
    user_id = bot_ctx["user_id"]

    rewards_svc = RewardsService(db)
    points_data = await rewards_svc.get_user_points(user_id, project_id, tenant_id)

    total = int(points_data.get("total_points", 0))
    today = int(points_data.get("today_points", 0))
    week = int(points_data.get("week_points", 0))
    completions = int(points_data.get("total_completions", 0))
    rank = int(points_data.get("rank", 0))

    text = (
        f"💰 *Your Points*\n\n"
        f"🔢 Total: *{total}* pts\n"
        f"📅 Today: {today} pts\n"
        f"📅 This week: {week} pts\n"
        f"✅ Total completions: {completions}\n"
        f"🏆 Project rank: \\#{rank}"
    )

    keyboard = InlineKeyboards.from_rows([
        [
            InlineKeyboards.button("🏆 Leaderboard", "menu:leaderboard"),
            InlineKeyboards.button(t("button.menu", locale), "menu:main"),
        ]
    ])
    await client.send_message(chat_id, text, reply_markup=keyboard)
