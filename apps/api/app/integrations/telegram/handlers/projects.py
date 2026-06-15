# ID: AX32      |  Local: A15Y1         |  Module: X16 (M15)
# Functions: A15Y1F1 A15Y1F2 A15Y1F3 A15Y1F4
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.integrations.telegram.keyboards.builders import KeyboardBuilders
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.projects")


async def projects_handler(update: dict, ctx: dict) -> None:
    """A15Y1F1: Show user's project list with pagination."""
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

    projects = await BotContextService(redis, db).get_user_projects(user_id, tenant_id)

    if not projects:
        await client.send_message(chat_id, t("project.empty", locale))
        return

    state_svc = BotStateService(redis, db)
    await state_svc.transition(telegram_user_id, "PROJECT_SELECT")

    keyboard = KeyboardBuilders.project_list(projects, page=0, locale=locale)
    text = t("project.switcher_header", locale)

    await client.send_message(chat_id, text, reply_markup=keyboard)


async def project_page_callback(update: dict, ctx: dict) -> None:
    """A15Y1F2: Handle proj_page:{n} pagination."""
    callback_query = ctx.get("callback_query", {})
    callback_data = ctx.get("callback_data", "")
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")

    await client.answer_callback_query(callback_query.get("id", ""))

    try:
        page = int(callback_data.split(":")[1])
    except (IndexError, ValueError):
        page = 0

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
    if not bot_ctx:
        return

    projects = await BotContextService(redis, db).get_user_projects(bot_ctx["user_id"], bot_ctx["tenant_id"])
    keyboard = KeyboardBuilders.project_list(projects, page=page, locale=locale)

    msg_id = callback_query.get("message", {}).get("message_id")
    if msg_id:
        await client.edit_message_reply_markup(chat_id, msg_id, keyboard)


async def project_select_callback(update: dict, ctx: dict) -> None:
    """A15Y1F3: Handle project:{uuid} — select project."""
    callback_query = ctx.get("callback_query", {})
    callback_data = ctx.get("callback_data", "")
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")

    await client.answer_callback_query(callback_query.get("id", ""))

    project_id = callback_data.replace("project:", "")

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    try:
        from uuid import UUID
        await BotContextService(redis, db).set_active_project(telegram_user_id, UUID(project_id))
        bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
        project_name = bot_ctx.get("project_name", project_id) if bot_ctx else project_id
        await client.send_message(
            chat_id,
            t("project.active_set", locale, project_name=escape_md(project_name))
        )
    except ValueError as exc:
        await client.send_message(chat_id, t("project.not_member", locale))


async def project_detail_callback(update: dict, ctx: dict) -> None:
    """A15Y1F4: Show project detail."""
    callback_query = ctx.get("callback_query", {})
    await ctx["client"].answer_callback_query(callback_query.get("id", ""))
    await projects_handler(update, ctx)
