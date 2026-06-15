# ID: AX35      |  Local: A18Y1         |  Module: X19 (M18)
# Functions: A18Y1F1 A18Y1F2 A18Y1F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging
from uuid import UUID

from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.services.completion_service import CompletionService
from apps.api.app.integrations.telegram.keyboards.builders import KeyboardBuilders
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.submit_single")


async def submit_single_entry(update: dict, ctx: dict) -> None:
    """A18Y1F1: Entry — show slot picker for single submission."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")
    task_id = ctx.get("resolved_task_id", "")

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
    if not bot_ctx or not bot_ctx.get("project_id"):
        await client.send_message(chat_id, t("error.session_expired", locale))
        return

    user_id = bot_ctx["user_id"]
    project_id = bot_ctx["project_id"]
    tenant_id = bot_ctx["tenant_id"]

    completion_svc = CompletionService(db)
    slots = await completion_svc.get_user_slots(user_id, project_id, tenant_id)

    if not slots:
        await client.send_message(chat_id, t("slot.no_slots", locale))
        return

    submitted_ids = await completion_svc.get_submitted_slot_ids(UUID(task_id), user_id, tenant_id)

    state_svc = BotStateService(redis, db)
    await state_svc.transition(telegram_user_id, "SINGLE_SLOT_SELECT", task_id=UUID(task_id))

    keyboard = KeyboardBuilders.slot_picker(slots, task_id, locale, submitted_ids)
    await client.send_message(chat_id, t("submit.choose_slot", locale), reply_markup=keyboard)


async def slot_select_callback(update: dict, ctx: dict) -> None:
    """A18Y1F2: Handle submit:{task_id}:{slot_id} callback."""
    callback_query = ctx.get("callback_query", {})
    callback_data = ctx.get("callback_data", "")
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")

    await client.answer_callback_query(callback_query.get("id", ""))

    parts = callback_data.split(":")
    if len(parts) < 3 or parts[1] == "already_done":
        if len(parts) >= 2 and parts[1] == "already_done":
            await client.answer_callback_query(callback_query.get("id", ""), t("submit.duplicate", locale))
        return

    task_id_str = parts[1]
    slot_id_str = parts[2]

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
    if not bot_ctx:
        await client.send_message(chat_id, t("error.session_expired", locale))
        return

    result = await CompletionService(db).submit_single(
        task_id=UUID(task_id_str),
        slot_id=UUID(slot_id_str),
        user_id=bot_ctx["user_id"],
        tenant_id=bot_ctx["tenant_id"],
    )

    if result.duplicate:
        await client.send_message(chat_id, t("submit.duplicate", locale))
    elif result.success:
        keyboard = InlineKeyboards.from_rows([
            [InlineKeyboards.button(t("button.back", locale), f"task_page:0")],
            [InlineKeyboards.button(t("button.menu", locale), "menu:main")],
        ])
        await client.send_message(
            chat_id,
            t("submit.success", locale, points=result.points_earned),
            reply_markup=keyboard
        )
        state_svc = BotStateService(redis, db)
        await state_svc.transition(telegram_user_id, "TASK_LIST")
    else:
        await client.send_message(chat_id, t("error.unknown", locale))


async def confirm_submit_callback(update: dict, ctx: dict) -> None:
    """A18Y1F3: Confirm submit callback."""
    callback_query = ctx.get("callback_query", {})
    await ctx["client"].answer_callback_query(callback_query.get("id", ""))
    await slot_select_callback(update, ctx)
