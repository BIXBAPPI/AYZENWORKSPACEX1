# ID: AX21      |  Local: A6Y2          |  Module: X07 (M06)
# Functions: A6Y2F1 A6Y2F2
# Processes: XN01 XN02
from __future__ import annotations

import logging
from typing import Any

from apps.api.app.services.bot_user_service import BotUserService
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.integrations.telegram.keyboards.reply import ReplyKeyboards

logger = logging.getLogger("ayzen.handlers.start")


async def start_handler(update: dict, ctx: dict) -> None:
    """Handle /start command — welcome or link prompt."""
    telegram_user_id = ctx["telegram_user_id"]
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    app = ctx.get("app")
    locale = ctx.get("locale", "bn")

    # Get user info from Telegram
    user_data = ctx.get("user_data", {})
    first_name = user_data.get("first_name", "")

    # Check if user is linked
    db = app.state.db if app else None
    redis = app.state.redis if app else None

    user_svc = BotUserService(redis, db)
    user = await user_svc.get_user_by_telegram_id(telegram_user_id)

    if not user:
        # Not linked — show registration prompt
        msg = t("welcome.not_linked", locale, name=escape_md(first_name))
        await client.send_message(chat_id, msg)
        return

    # User is linked — show welcome back + set active state
    ctx_svc = BotContextService(redis, db)
    bot_ctx = await ctx_svc.resolve(telegram_user_id)

    if not bot_ctx:
        msg = t("welcome.not_linked", locale, name=escape_md(first_name))
        await client.send_message(chat_id, msg)
        return

    state_svc = BotStateService(redis, db)
    locale = bot_ctx.get("locale", "bn")
    project_name = bot_ctx.get("project_name") or "—"

    await state_svc.transition(telegram_user_id, "IDLE", locale=locale)

    is_admin = bot_ctx.get("role") in ("owner", "manager")
    keyboard = ReplyKeyboards.main_menu(locale, is_admin)

    msg = t("welcome.returning", locale,
            name=escape_md(first_name),
            project_name=escape_md(project_name))
    await client.send_message(chat_id, msg, reply_markup=keyboard)


async def link_handler(update: dict, ctx: dict) -> None:
    """Handle /link {code} command — link Telegram to web account."""
    telegram_user_id = ctx["telegram_user_id"]
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    args = ctx.get("args", [])
    app = ctx.get("app")

    if not args:
        await client.send_message(chat_id, t("welcome.link_invalid", locale))
        return

    code = args[0].strip()
    user_data = ctx.get("user_data", {})
    telegram_username = user_data.get("username")

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    user_svc = BotUserService(redis, db)
    user = await user_svc.validate_and_link(telegram_user_id, telegram_username, code)

    if not user:
        await client.send_message(chat_id, t("welcome.link_invalid", locale))
        return

    # Auto-select first project
    ctx_svc = BotContextService(redis, db)
    await ctx_svc.auto_select_first_project(user["id"])

    is_admin = user.get("role") in ("owner", "manager")
    keyboard = ReplyKeyboards.main_menu(locale, is_admin)

    await client.send_message(chat_id, t("welcome.link_success", locale), reply_markup=keyboard)
