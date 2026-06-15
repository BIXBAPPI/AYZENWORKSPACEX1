# ID: AX31      |  Local: A14Y1         |  Module: X15 (M14)
# Functions: A14Y1F1 A14Y1F2 A14Y1F3
# Processes: XN01 XN02
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.profile")


async def profile_handler(update: dict, ctx: dict) -> None:
    """A14Y1F1: /profile — show user profile summary."""
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

    user_data = ctx.get("user_data", {})
    name = bot_ctx.get("full_name") or user_data.get("first_name", "—")
    email = bot_ctx.get("email", "—")
    role = bot_ctx.get("role", "member")
    project_name = bot_ctx.get("project_name", "—")

    text = (
        f"👤 *Profile*\n\n"
        f"📛 Name: {escape_md(name)}\n"
        f"📧 Email: {escape_md(email)}\n"
        f"🎭 Role: {escape_md(role)}\n"
        f"📌 Active Project: {escape_md(project_name or '—')}\n"
        f"🆔 Telegram ID: `{telegram_user_id}`"
    )

    keyboard = InlineKeyboards.from_rows([
        [InlineKeyboards.button("🔄 Refresh", f"profile_refresh:{telegram_user_id}")],
        [InlineKeyboards.button(t("button.menu", locale), "menu:main")],
    ])

    await client.send_message(chat_id, text, reply_markup=keyboard)


async def profile_refresh_callback(update: dict, ctx: dict) -> None:
    """A14Y1F2: Refresh profile callback."""
    callback_query = ctx.get("callback_query", {})
    await ctx["client"].answer_callback_query(callback_query.get("id", ""))
    await profile_handler(update, ctx)
