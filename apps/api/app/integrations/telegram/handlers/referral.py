# ID: AX45      |  Local: A25Y1         |  Module: X25 (M18)
# Functions: A25Y1F1 A25Y1F2
# Processes: XN01 XN03
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.services.referral_service import ReferralService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.referral")


async def referral_handler(update: dict, ctx: dict) -> None:
    """A25Y1F1: Show referral link and stats."""
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

    locale    = bot_ctx.get("locale", "bn")
    user_id   = bot_ctx.get("user_id", "")
    tenant_id = bot_ctx.get("tenant_id", "")

    svc        = ReferralService(db)
    ref_link   = await svc.get_or_create_link(tenant_id=tenant_id, user_id=user_id)
    stats      = await svc.get_stats(tenant_id=tenant_id, user_id=user_id)

    ref_count  = stats.get("referral_count", 0)
    bonus_pts  = stats.get("bonus_points", 0)

    full_link  = f"https://t.me/{ctx.get('bot_username', 'AyzenBot')}?start={ref_link}"

    text = (
        f"🔗 *{t('referral.link_header', locale)}*\n\n"
        f"{t('referral.your_link', locale, link=full_link)}\n\n"
        f"{t('referral.stats', locale, count=ref_count, points=bonus_pts)}"
    )

    kb = InlineKeyboards.referral_actions(full_link, locale)
    await client.send_message(chat_id, text, reply_markup=kb, parse_mode="MarkdownV2")


async def referral_callback_handler(update: dict, ctx: dict) -> None:
    """A25Y1F2: Handle referral:refresh callback."""
    cb     = ctx.get("callback_data", "")
    cq     = ctx.get("callback_query", {})
    client = ctx["client"]
    await client.answer_callback_query(cq.get("id", ""))
    if cb == "referral:refresh":
        await referral_handler(update, ctx)
