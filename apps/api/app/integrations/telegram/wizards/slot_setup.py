# ID: AX33      |  Local: A16Y1         |  Module: X17 (M16)
# Functions: A16Y1F1 A16Y1F2 A16Y1F3 A16Y1F4
# Processes: XN01 XN02 XN03 XN04
from __future__ import annotations

import logging
import re

from apps.api.app.services.i18n_service import t
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards
from apps.api.app.integrations.telegram.keyboards.reply import ReplyKeyboards

logger = logging.getLogger("ayzen.wizards.slot_setup")

STEPS = ["twitter", "discord", "wallet", "confirm"]
TWITTER_RE = re.compile(r"^@?[A-Za-z0-9_]{1,50}$")
DISCORD_RE = re.compile(r"^.{2,50}$")
WALLET_RE = re.compile(r"^0x[a-fA-F0-9]{40}$|^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^[a-zA-Z0-9]{32,64}$")


async def wizard_slot_start(update: dict, ctx: dict) -> None:
    """A16Y1F1: Start slot setup wizard."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")
    callback_data = ctx.get("callback_data", "")

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    # Parse slot_name from callback e.g. wizard_slot:M1
    slot_name = callback_data.split(":")[-1] if ":" in callback_data else "M1"

    state_svc = BotStateService(redis, db)
    await state_svc.transition(
        telegram_user_id, "WIZARD_NEW_SLOT",
        wizard_step=0,
        wizard_data={"slot_name": slot_name},
    )

    cancel_kb = ReplyKeyboards.cancel_only(locale)
    await client.send_message(
        chat_id,
        t("slot.setup_header", locale) + "\n\n" + t("slot.ask_twitter", locale),
        reply_markup=cancel_kb,
    )


async def wizard_slot_step_handler(update: dict, ctx: dict) -> None:
    """A16Y1F2: Process each slot setup step."""
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
        await client.send_message(chat_id, t("wizard.cancelled", locale),
                                  reply_markup=ReplyKeyboards.main_menu(locale))
        return

    state_svc = BotStateService(redis, db)
    bot_state = await state_svc.get(telegram_user_id)
    step = bot_state.wizard_step
    data = dict(bot_state.wizard_data)
    step_name = STEPS[step] if step < len(STEPS) else "confirm"

    if step_name == "twitter":
        if not TWITTER_RE.match(text):
            await client.send_message(chat_id, t("slot.invalid_format", locale))
            return
        data["twitter"] = text.lstrip("@")
        await state_svc.transition(telegram_user_id, "WIZARD_NEW_SLOT", wizard_step=1, wizard_data=data)
        skip_kb = InlineKeyboards.from_rows([[InlineKeyboards.button(t("button.skip", locale), "wizard:skip_discord")]])
        await client.send_message(chat_id, t("slot.ask_discord", locale), reply_markup=skip_kb)

    elif step_name == "discord":
        if not DISCORD_RE.match(text):
            await client.send_message(chat_id, t("slot.invalid_format", locale))
            return
        data["discord"] = text
        await state_svc.transition(telegram_user_id, "WIZARD_NEW_SLOT", wizard_step=2, wizard_data=data)
        skip_kb = InlineKeyboards.from_rows([[InlineKeyboards.button(t("button.skip", locale), "wizard:skip_wallet")]])
        await client.send_message(chat_id, t("slot.ask_wallet", locale), reply_markup=skip_kb)

    elif step_name == "wallet":
        if not WALLET_RE.match(text):
            await client.send_message(chat_id, t("slot.invalid_format", locale))
            return
        data["wallet"] = text
        await state_svc.transition(telegram_user_id, "WIZARD_NEW_SLOT", wizard_step=3, wizard_data=data)
        await _show_confirm(client, chat_id, locale, data, telegram_user_id, state_svc)

    elif step_name == "confirm":
        await _save_slot(ctx, data)


async def _show_confirm(client, chat_id, locale, data, telegram_user_id, state_svc) -> None:
    text = t("slot.confirm", locale,
             twitter=data.get("twitter", "—"),
             discord=data.get("discord", "—"),
             wallet=data.get("wallet", "—"))
    keyboard = InlineKeyboards.from_rows([
        [
            InlineKeyboards.button(t("button.yes", locale), "wizard:confirm_slot"),
            InlineKeyboards.button(t("button.no", locale), "wizard:cancel"),
        ]
    ])
    await client.send_message(chat_id, text, reply_markup=keyboard)


async def _save_slot(ctx: dict, data: dict) -> None:
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

    slot_name = data.get("slot_name", "M1")
    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{bot_ctx['tenant_id']}'")
        await session.execute(
            """
            INSERT INTO account_slots
                (user_id, project_id, slot_name, twitter_username, discord_username, wallet_address)
            VALUES (:uid, :pid, :sname, :tw, :dc, :wa)
            ON CONFLICT (user_id, project_id, slot_name)
            DO UPDATE SET
                twitter_username = EXCLUDED.twitter_username,
                discord_username = EXCLUDED.discord_username,
                wallet_address = EXCLUDED.wallet_address
            """,
            {
                "uid": str(bot_ctx["user_id"]), "pid": str(bot_ctx["project_id"]),
                "sname": slot_name,
                "tw": data.get("twitter"), "dc": data.get("discord"), "wa": data.get("wallet"),
            },
        )
        await session.commit()

    await BotStateService(redis, db).transition(telegram_user_id, "IDLE")
    keyboard = ReplyKeyboards.main_menu(locale)
    await client.send_message(chat_id, t("slot.saved", locale, slot_name=slot_name), reply_markup=keyboard)
