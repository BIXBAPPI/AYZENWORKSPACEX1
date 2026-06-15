# ID: AX36      |  Local: A19Y1         |  Module: X20 (M19)
# Functions: A19Y1F1 A19Y1F2 A19Y1F3 A19Y1F4 A19Y1F5
# Processes: XN01 XN02 XN03 XN04
from __future__ import annotations

import logging
from uuid import UUID

from apps.api.app.services.i18n_service import t
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.services.completion_service import CompletionService
from apps.api.app.integrations.telegram.keyboards.builders import KeyboardBuilders
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.submit_batch")


async def batch_submit_entry(update: dict, ctx: dict) -> None:
    """A19Y1F1: Entry — show batch slot selection keyboard."""
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
    available_slots = [s for s in slots if str(s["id"]) not in submitted_ids]

    if not available_slots:
        await client.send_message(chat_id, t("submit.all_done", locale, points=0))
        return

    state_svc = BotStateService(redis, db)
    await state_svc.transition(
        telegram_user_id, "BATCH_SLOT_SELECT",
        task_id=UUID(task_id),
        batch_selected=[],
    )

    keyboard = KeyboardBuilders.batch_toggle(
        items=available_slots,
        selected_ids=[],
        prefix="batch:",
        locale=locale,
    )
    await client.send_message(chat_id, t("submit.batch_header", locale), reply_markup=keyboard)


async def toggle_slot_callback(update: dict, ctx: dict) -> None:
    """A19Y1F2: Toggle batch slot selection."""
    callback_query = ctx.get("callback_query", {})
    callback_data = ctx.get("callback_data", "")
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")

    await client.answer_callback_query(callback_query.get("id", ""))

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    state_svc = BotStateService(redis, db)
    bot_state = await state_svc.get(telegram_user_id)

    bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
    if not bot_ctx or not bot_ctx.get("project_id"):
        return

    user_id = bot_ctx["user_id"]
    project_id = bot_ctx["project_id"]
    tenant_id = bot_ctx["tenant_id"]
    task_id = bot_state.task_id

    completion_svc = CompletionService(db)
    slots = await completion_svc.get_user_slots(user_id, project_id, tenant_id)
    submitted_ids = await completion_svc.get_submitted_slot_ids(task_id, user_id, tenant_id)
    available_slots = [s for s in slots if str(s["id"]) not in submitted_ids]

    selected_ids = [str(s) for s in bot_state.batch_selected]

    # Parse action
    parts = callback_data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action == "toggle" and len(parts) > 2:
        slot_id = parts[2]
        if slot_id in selected_ids:
            selected_ids.remove(slot_id)
        else:
            selected_ids.append(slot_id)
    elif action == "select_all":
        selected_ids = [str(s["id"]) for s in available_slots]
    elif action == "clear":
        selected_ids = []
    elif action == "confirm":
        await confirm_batch_callback(update, ctx)
        return

    await state_svc.transition(
        telegram_user_id, "BATCH_SLOT_SELECT",
        batch_selected=[UUID(s) for s in selected_ids],
    )

    keyboard = KeyboardBuilders.batch_toggle(available_slots, selected_ids, "batch:", locale)
    msg_id = callback_query.get("message", {}).get("message_id")
    if msg_id:
        await client.edit_message_reply_markup(chat_id, msg_id, keyboard)


async def confirm_batch_callback(update: dict, ctx: dict) -> None:
    """A19Y1F3: Confirm and execute batch submission."""
    callback_query = ctx.get("callback_query", {})
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")

    await client.answer_callback_query(callback_query.get("id", ""))

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    state_svc = BotStateService(redis, db)
    bot_state = await state_svc.get(telegram_user_id)

    if not bot_state.batch_selected:
        await client.send_message(chat_id, t("submit.none_selected", locale))
        return

    bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
    if not bot_ctx:
        return

    result = await CompletionService(db).submit_batch(
        task_id=bot_state.task_id,
        slot_ids=bot_state.batch_selected,
        user_id=bot_ctx["user_id"],
        tenant_id=bot_ctx["tenant_id"],
    )

    total = result["success"] + result["duplicate"]
    if result["success"] == total and result["success"] > 0:
        msg = t("submit.all_done", locale, points=result["total_points"])
    else:
        msg = t("submit.partial_success", locale,
                done=result["success"],
                total=total,
                failed=result["duplicate"])

    keyboard = InlineKeyboards.from_rows([
        [InlineKeyboards.button(t("button.menu", locale), "menu:main")]
    ])
    await client.send_message(chat_id, msg, reply_markup=keyboard)
    await state_svc.transition(telegram_user_id, "IDLE")


async def cancel_batch_callback(update: dict, ctx: dict) -> None:
    """A19Y1F4: Cancel batch submission."""
    callback_query = ctx.get("callback_query", {})
    await ctx["client"].answer_callback_query(callback_query.get("id", ""))
    locale = ctx.get("locale", "bn")
    chat_id = ctx["chat_id"]
    await ctx["client"].send_message(chat_id, t("wizard.cancelled", locale))
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")
    db = app.state.db if app else None
    redis = app.state.redis if app else None
    await BotStateService(redis, db).transition(telegram_user_id, "IDLE")
