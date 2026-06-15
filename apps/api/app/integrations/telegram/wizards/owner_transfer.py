# ID: AX46      |  Local: A26Y1         |  Module: X26 (M19)
# Functions: A26Y1F1 A26Y1F2 A26Y1F3 A26Y1F4
# Processes: XN01 XN02 XN04
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.services.owner_transfer_service import OwnerTransferService
from apps.api.app.integrations.telegram.keyboards.builders import KeyboardBuilders
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards
from apps.api.app.integrations.telegram.keyboards.reply import ReplyKeyboards

logger = logging.getLogger("ayzen.wizards.owner_transfer")

# State machine keys
_STATE = "OWNER_TRANSFER"
_KEY_CANDIDATE = "transfer_candidate_id"
_KEY_CANDIDATE_NAME = "transfer_candidate_name"


async def transfer_start_handler(update: dict, ctx: dict) -> None:
    """A26Y1F1: Start owner transfer — show eligible manager list."""
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
    role       = bot_ctx.get("role", "member")
    project_id = bot_ctx.get("active_project_id", "")
    tenant_id  = bot_ctx.get("tenant_id", "")

    if role != "owner":
        await client.send_message(chat_id, t("owner_transfer.not_owner", locale))
        return

    svc        = OwnerTransferService(db)
    candidates = await svc.get_eligible_candidates(tenant_id=tenant_id, project_id=project_id)

    if not candidates:
        await client.send_message(
            chat_id,
            t("owner_transfer.no_candidates", locale),
        )
        return

    await BotStateService(redis, db).transition(
        tg_uid, f"{_STATE}_SELECT", locale=locale,
    )

    text = t("owner_transfer.select_candidate", locale)
    kb   = KeyboardBuilders.transfer_candidate_list(candidates, locale)
    await client.send_message(chat_id, text, reply_markup=kb)


async def transfer_candidate_callback(update: dict, ctx: dict) -> None:
    """A26Y1F2: User selected a transfer candidate — show confirmation."""
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

    # cb format: transfer_to:<candidate_user_id>
    if not cb.startswith("transfer_to:"):
        return

    candidate_id = cb.split(":")[1]

    bot_ctx = await BotContextService(redis, db).resolve(tg_uid)
    if not bot_ctx:
        return

    locale       = bot_ctx.get("locale", "bn")
    tenant_id    = bot_ctx.get("tenant_id", "")
    project_id   = bot_ctx.get("active_project_id", "")
    project_name = bot_ctx.get("project_name", "—")

    # Fetch candidate name
    svc  = OwnerTransferService(db)
    name = await svc.get_member_name(tenant_id=tenant_id, user_id=candidate_id)

    # Persist candidate in wizard state
    state_svc = BotStateService(redis, db)
    await state_svc.update_draft(
        tg_uid,
        {_KEY_CANDIDATE: candidate_id, _KEY_CANDIDATE_NAME: name},
    )
    await state_svc.transition(tg_uid, f"{_STATE}_CONFIRM", locale=locale)

    text = t("owner_transfer.prompt", locale, project_name=project_name, new_owner=name)
    kb   = InlineKeyboards.yes_no(
        yes_cb="transfer:confirm",
        no_cb="transfer:cancel",
        locale=locale,
    )
    await client.send_message(chat_id, text, reply_markup=kb)


async def transfer_confirm_callback(update: dict, ctx: dict) -> None:
    """A26Y1F3: Handle transfer:confirm — ask user to type project name."""
    cq      = ctx.get("callback_query", {})
    chat_id = ctx["chat_id"]
    client  = ctx["client"]
    locale  = ctx.get("locale", "bn")
    app     = ctx.get("app")
    db      = app.state.db if app else None
    redis   = app.state.redis if app else None
    tg_uid  = ctx["telegram_user_id"]

    await client.answer_callback_query(cq.get("id", ""))

    bot_ctx = await BotContextService(redis, db).resolve(tg_uid)
    if not bot_ctx:
        return

    locale       = bot_ctx.get("locale", "bn")
    project_name = bot_ctx.get("project_name", "—")

    await BotStateService(redis, db).transition(tg_uid, f"{_STATE}_TYPED", locale=locale)

    kb = ReplyKeyboards.cancel_only(locale)
    await client.send_message(
        chat_id,
        t("owner_transfer.confirm_code", locale, project_name=project_name),
        reply_markup=kb,
    )


async def transfer_typed_handler(update: dict, ctx: dict) -> None:
    """A26Y1F4: User typed project name — execute or reject transfer."""
    chat_id = ctx["chat_id"]
    client  = ctx["client"]
    locale  = ctx.get("locale", "bn")
    app     = ctx.get("app")
    db      = app.state.db if app else None
    redis   = app.state.redis if app else None
    tg_uid  = ctx["telegram_user_id"]
    typed   = ctx.get("text", "").strip()

    bot_ctx = await BotContextService(redis, db).resolve(tg_uid)
    if not bot_ctx:
        return

    locale       = bot_ctx.get("locale", "bn")
    tenant_id    = bot_ctx.get("tenant_id", "")
    project_id   = bot_ctx.get("active_project_id", "")
    project_name = bot_ctx.get("project_name", "—")
    user_id      = bot_ctx.get("user_id", "")

    state_svc = BotStateService(redis, db)
    draft     = await state_svc.get_draft(tg_uid) or {}
    candidate_id   = draft.get(_KEY_CANDIDATE, "")
    candidate_name = draft.get(_KEY_CANDIDATE_NAME, "—")

    is_admin = bot_ctx.get("role") in ("owner", "manager")
    kb_main  = ReplyKeyboards.main_menu(locale, is_admin)

    if typed != project_name:
        await state_svc.transition(tg_uid, "IDLE")
        await client.send_message(
            chat_id,
            t("owner_transfer.invalid_confirm", locale),
            reply_markup=kb_main,
        )
        return

    svc = OwnerTransferService(db)
    ok  = await svc.execute_transfer(
        tenant_id=tenant_id,
        project_id=project_id,
        current_owner_id=user_id,
        new_owner_id=candidate_id,
    )

    await state_svc.transition(tg_uid, "IDLE")

    if ok:
        await client.send_message(
            chat_id,
            t("owner_transfer.success", locale, project_name=project_name, new_owner=candidate_name),
            reply_markup=kb_main,
        )
    else:
        await client.send_message(
            chat_id,
            t("error.generic", locale),
            reply_markup=kb_main,
        )
