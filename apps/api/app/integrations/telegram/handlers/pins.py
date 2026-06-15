# ID: AX44      |  Local: A24Y1         |  Module: X24 (M18)
# Functions: A24Y1F1 A24Y1F2 A24Y1F3
# Processes: XN01 XN03
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.services.pin_service import PinService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.pins")

MAX_PINS = 5


async def pins_handler(update: dict, ctx: dict) -> None:
    """A24Y1F1: Show pinned tasks list."""
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

    locale     = bot_ctx.get("locale", "bn")
    user_id    = bot_ctx.get("user_id", "")
    tenant_id  = bot_ctx.get("tenant_id", "")
    project_id = bot_ctx.get("active_project_id", "")

    if not project_id:
        await client.send_message(chat_id, t("error.no_project", locale))
        return

    svc    = PinService(db)
    pinned = await svc.get_pinned(tenant_id=tenant_id, user_id=user_id, project_id=project_id)

    count = len(pinned)
    if count == 0:
        text = f"📌 *{t('pin.list_header', locale)}*\n\n{t('pin.empty', locale)}"
    else:
        text = f"📌 *{t('pin.list_header', locale)}*\n\n{t('pin.count', locale, count=count, max=MAX_PINS)}"

    kb = InlineKeyboards.pin_list(pinned, locale)
    await client.send_message(chat_id, text, reply_markup=kb, parse_mode="MarkdownV2")


async def pin_callback_handler(update: dict, ctx: dict) -> None:
    """A24Y1F2: Handle pin:add:<id> and pin:remove:<id> callbacks."""
    cb      = ctx.get("callback_data", "")
    cq      = ctx.get("callback_query", {})
    chat_id = ctx["chat_id"]
    client  = ctx["client"]
    locale  = ctx.get("locale", "bn")
    app     = ctx.get("app")
    db      = app.state.db if app else None
    redis   = app.state.redis if app else None
    tg_uid  = ctx["telegram_user_id"]

    await client.answer_callback_query(cq.get("id", ""))

    parts = cb.split(":")
    if len(parts) < 3:
        return

    action  = parts[1]   # add | remove
    task_id = parts[2]

    bot_ctx = await BotContextService(redis, db).resolve(tg_uid)
    if not bot_ctx:
        return

    locale     = bot_ctx.get("locale", "bn")
    user_id    = bot_ctx.get("user_id", "")
    tenant_id  = bot_ctx.get("tenant_id", "")
    project_id = bot_ctx.get("active_project_id", "")

    svc = PinService(db)

    if action == "add":
        current = await svc.get_pinned(tenant_id=tenant_id, user_id=user_id, project_id=project_id)
        if len(current) >= MAX_PINS:
            await client.send_message(chat_id, t("pin.limit", locale, max=MAX_PINS))
            return
        already = any(str(p.get("id")) == task_id for p in current)
        if already:
            await client.send_message(chat_id, t("pin.already_pinned", locale))
            return
        await svc.pin(tenant_id=tenant_id, user_id=user_id, task_id=task_id)
        await client.send_message(chat_id, t("pin.pinned", locale))

    elif action == "remove":
        await svc.unpin(tenant_id=tenant_id, user_id=user_id, task_id=task_id)
        await client.send_message(chat_id, t("pin.unpinned", locale))
        # Refresh pinned list inline
        await pins_handler(update, ctx)


async def pin_toggle_from_task_callback(update: dict, ctx: dict) -> None:
    """A24Y1F3: Re-route pin:add/remove triggered from task detail view."""
    await pin_callback_handler(update, ctx)
