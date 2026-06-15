# ID: AX44      |  Local: A27Y1         |  Module: X28 (M27)
# Functions: A27Y1F1 A27Y1F2 A27Y1F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards
from apps.api.app.integrations.telegram.keyboards.reply import ReplyKeyboards

logger = logging.getLogger("ayzen.wizards.broadcast")


async def broadcast_wizard_start(update: dict, ctx: dict) -> None:
    """A27Y1F1: Start broadcast wizard."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")
    db = app.state.db if app else None
    redis = app.state.redis if app else None

    state_svc = BotStateService(redis, db)
    await state_svc.transition(
        telegram_user_id, "WIZARD_BROADCAST",
        wizard_step=0, wizard_data={},
    )

    cancel_kb = ReplyKeyboards.cancel_only(locale)
    await client.send_message(chat_id, t("admin.broadcast_prompt", locale), reply_markup=cancel_kb)


async def broadcast_wizard_step(update: dict, ctx: dict) -> None:
    """A27Y1F2: Handle broadcast message input."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    text = ctx.get("text", "").strip()
    app = ctx.get("app")
    db = app.state.db if app else None
    redis = app.state.redis if app else None

    if text == t("wizard.cancel", locale):
        await BotStateService(redis, db).transition(telegram_user_id, "IDLE")
        await client.send_message(chat_id, t("wizard.cancelled", locale), reply_markup=ReplyKeyboards.main_menu(locale, True))
        return

    if len(text) < 5:
        await client.send_message(chat_id, t("wizard.invalid_input", locale))
        return

    state_svc = BotStateService(redis, db)
    bot_state = await state_svc.get(telegram_user_id)
    step = bot_state.wizard_step

    if step == 0:
        # Show preview + confirm
        await state_svc.transition(telegram_user_id, "WIZARD_BROADCAST", wizard_step=1, wizard_data={"message": text})
        preview = f"📢 *Preview:*\n\n{escape_md(text)}\n\n*Send broadcast?*"
        keyboard = InlineKeyboards.from_rows([
            [
                InlineKeyboards.button(t("button.confirm", locale), "broadcast_wizard:confirm"),
                InlineKeyboards.button(t("button.cancel", locale), "broadcast_wizard:cancel"),
            ]
        ])
        await client.send_message(chat_id, preview, reply_markup=keyboard)
    elif step == 1:
        # Sent via callback — shouldn't reach here as text
        await client.send_message(chat_id, t("wizard.invalid_input", locale))


async def _do_broadcast(ctx: dict, message: str) -> None:
    """A27Y1F3: Execute broadcast to all project members."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")
    db = app.state.db if app else None
    redis = app.state.redis if app else None

    bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
    if not bot_ctx or not bot_ctx.get("project_id"):
        await client.send_message(chat_id, t("error.session_expired", locale))
        return

    from apps.api.app.services.broadcast_service import BroadcastService
    broadcast_svc = BroadcastService(db, client)
    count = await broadcast_svc.send_project_broadcast(
        project_id=bot_ctx["project_id"],
        tenant_id=bot_ctx["tenant_id"],
        sender_id=bot_ctx["user_id"],
        message=message,
        locale=locale,
    )

    await BotStateService(redis, db).transition(telegram_user_id, "IDLE")
    keyboard = ReplyKeyboards.main_menu(locale, True)
    await client.send_message(
        chat_id,
        t("admin.broadcast_sent", locale, count=count),
        reply_markup=keyboard,
    )


# Callback handler for broadcast confirm/cancel
async def broadcast_confirm_callback(update: dict, ctx: dict) -> None:
    callback_query = ctx.get("callback_query", {})
    callback_data = ctx.get("callback_data", "")
    await ctx["client"].answer_callback_query(callback_query.get("id", ""))

    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")
    db = app.state.db if app else None
    redis = app.state.redis if app else None

    state_svc = BotStateService(redis, db)
    bot_state = await state_svc.get(telegram_user_id)
    message = bot_state.wizard_data.get("message", "")

    if callback_data == "broadcast_wizard:confirm":
        await _do_broadcast(ctx, message)
    elif callback_data == "broadcast_wizard:cancel":
        await state_svc.transition(telegram_user_id, "IDLE")
        locale = ctx.get("locale", "bn")
        await ctx["client"].send_message(
            ctx["chat_id"],
            t("wizard.cancelled", locale),
            reply_markup=ReplyKeyboards.main_menu(locale, True),
        )
