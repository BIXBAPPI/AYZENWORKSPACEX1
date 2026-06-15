# ID: AX40      |  Local: A23Y1         |  Module: X24 (M23)
# Functions: A23Y1F1 A23Y1F2
# Processes: XN01 XN02
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.services.rewards_service import RewardsService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.leaderboard")


async def leaderboard_handler(update: dict, ctx: dict) -> None:
    """A23Y1F1: Show project leaderboard."""
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
    project_name = bot_ctx.get("project_name", "—")
    user_id = bot_ctx["user_id"]

    rewards_svc = RewardsService(db)
    leaderboard = await rewards_svc.get_leaderboard(project_id, tenant_id, limit=10)

    if not leaderboard:
        await client.send_message(chat_id, t("progress.no_data", locale))
        return

    rank_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines = [f"🏆 *Leaderboard — {escape_md(project_name)}*\n"]

    for entry in leaderboard:
        rank = int(entry.get("rank", 0))
        icon = rank_emojis.get(rank, f"{rank}\\.")
        name = escape_md(entry.get("full_name") or entry.get("email") or "—")
        pts = int(entry.get("total_points", 0))
        done = entry.get("completions", 0)
        lines.append(f"{icon} {name} — {pts} pts \\({done}✅\\)")

    text = "\n".join(lines)

    keyboard = InlineKeyboards.from_rows([
        [
            InlineKeyboards.button("🔄 Refresh", "menu:leaderboard"),
            InlineKeyboards.button(t("button.menu", locale), "menu:main"),
        ]
    ])
    await client.send_message(chat_id, text, reply_markup=keyboard)
