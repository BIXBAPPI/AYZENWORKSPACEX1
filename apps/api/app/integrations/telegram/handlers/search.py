# ID: AX43      |  Local: A23Y1         |  Module: X23 (M18)
# Functions: A23Y1F1 A23Y1F2 A23Y1F3
# Processes: XN01 XN03
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.services.search_service import SearchService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards
from apps.api.app.integrations.telegram.keyboards.reply import ReplyKeyboards

logger = logging.getLogger("ayzen.handlers.search")


async def search_prompt_handler(update: dict, ctx: dict) -> None:
    """A23Y1F1: Prompt user to enter a search keyword."""
    chat_id = ctx["chat_id"]
    client  = ctx["client"]
    locale  = ctx.get("locale", "bn")
    app     = ctx.get("app")
    db      = app.state.db if app else None
    redis   = app.state.redis if app else None
    tg_uid  = ctx["telegram_user_id"]

    bot_ctx = await BotContextService(redis, db).resolve(tg_uid)
    if not bot_ctx:
        await client.send_message(chat_id, t("error.not_linked", locale))
        return

    locale = bot_ctx.get("locale", "bn")

    # Transition to SEARCH_WAIT state
    await BotStateService(redis, db).transition(tg_uid, "SEARCH_WAIT", locale=locale)

    kb = ReplyKeyboards.cancel_only(locale)
    await client.send_message(
        chat_id,
        t("search.header", locale),
        reply_markup=kb,
    )


async def search_execute_handler(update: dict, ctx: dict) -> None:
    """A23Y1F2: Execute search — called when user sends a keyword while in SEARCH_WAIT state."""
    chat_id = ctx["chat_id"]
    client  = ctx["client"]
    locale  = ctx.get("locale", "bn")
    app     = ctx.get("app")
    db      = app.state.db if app else None
    redis   = app.state.redis if app else None
    tg_uid  = ctx["telegram_user_id"]
    query   = ctx.get("text", "").strip()

    bot_ctx = await BotContextService(redis, db).resolve(tg_uid)
    if not bot_ctx:
        await client.send_message(chat_id, t("error.not_linked", locale))
        return

    locale     = bot_ctx.get("locale", "bn")
    project_id = bot_ctx.get("active_project_id", "")
    tenant_id  = bot_ctx.get("tenant_id", "")

    # Return to IDLE regardless
    await BotStateService(redis, db).transition(tg_uid, "IDLE", locale=locale)

    if len(query) < 2:
        await client.send_message(chat_id, t("search.too_short", locale))
        return

    if not project_id:
        await client.send_message(chat_id, t("error.no_project", locale))
        return

    svc     = SearchService(db)
    results = await svc.search_tasks(
        tenant_id=tenant_id,
        project_id=project_id,
        query=query,
        user_id=bot_ctx.get("user_id", ""),
        limit=10,
    )

    count = len(results)
    if count == 0:
        text = t("search.no_results", locale, query=query)
    else:
        text = t("search.results_header", locale, query=query) + f"\n\n{t('search.count', locale, count=count)}"

    kb = InlineKeyboards.search_results(results, query, locale)
    await client.send_message(chat_id, text, reply_markup=kb)


async def search_callback_handler(update: dict, ctx: dict) -> None:
    """A23Y1F3: Handle search:new callback — re-prompt search."""
    cb     = ctx.get("callback_data", "")
    cq     = ctx.get("callback_query", {})
    client = ctx["client"]
    await client.answer_callback_query(cq.get("id", ""))

    if cb == "search:new":
        await search_prompt_handler(update, ctx)
