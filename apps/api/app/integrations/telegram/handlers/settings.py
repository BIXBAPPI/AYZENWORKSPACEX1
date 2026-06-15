# ID: AX24      |  Local: A9Y1          |  Module: X09 (M08)
# Functions: A9Y1F1–A9Y1F7
# Processes: XN01 XN02
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t, invalidate_cache
from apps.api.app.services.user_settings_service import UserSettingsService
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards
from apps.api.app.integrations.telegram.keyboards.reply import ReplyKeyboards

logger = logging.getLogger("ayzen.handlers.settings")


def _db_redis(ctx: dict):
    app = ctx.get("app")
    return (app.state.db if app else None), (app.state.redis if app else None)


async def settings_handler(update: dict, ctx: dict) -> None:
    """A9Y1F1: /settings — show notification toggles + locale."""
    chat_id   = ctx["chat_id"]
    client    = ctx["client"]
    locale    = ctx.get("locale", "bn")
    db, redis = _db_redis(ctx)
    tg_uid    = ctx["telegram_user_id"]

    bot_ctx = await BotContextService(redis, db).resolve(tg_uid)
    if not bot_ctx:
        await client.send_message(chat_id, t("error.not_linked", locale))
        return

    locale    = bot_ctx.get("locale", locale)
    user_id   = bot_ctx.get("user_id", "")
    tenant_id = bot_ctx.get("tenant_id", "")

    svc   = UserSettingsService(db)
    prefs = await svc.get(tenant_id=tenant_id, user_id=user_id)

    quiet_start = prefs.get("quiet_start") or ""
    quiet_end   = prefs.get("quiet_end") or ""
    quiet_str   = (
        f"{quiet_start}–{quiet_end}"
        if quiet_start else t("settings_menu.quiet_hours_off", locale)
    )

    text = (
        f"⚙️ *{t('settings.header', locale)}*\n\n"
        f"🌐 {t('settings.current_locale', locale, locale=locale.upper())}\n"
        f"🔕 {t('settings_menu.quiet_hours', locale)}: {quiet_str}"
    )
    kb = InlineKeyboards.notification_settings(
        prefs={
            "deadline":   prefs.get("notify_deadline", True),
            "assignment": prefs.get("notify_assignment", True),
            "broadcast":  prefs.get("notify_broadcast", True),
            "digest":     prefs.get("notify_digest", True),
        },
        locale=locale,
    )
    await client.send_message(chat_id, text, reply_markup=kb, parse_mode="MarkdownV2")


async def settings_language_handler(update: dict, ctx: dict) -> None:
    """A9Y1F2: Language picker panel."""
    chat_id   = ctx["chat_id"]
    client    = ctx["client"]
    locale    = ctx.get("locale", "bn")
    db, redis = _db_redis(ctx)

    bot_ctx = await BotContextService(redis, db).resolve(ctx["telegram_user_id"])
    if bot_ctx:
        locale = bot_ctx.get("locale", locale)

    kb = InlineKeyboards.language_picker(locale)
    await client.send_message(chat_id, t("settings_menu.language_header", locale), reply_markup=kb)


async def settings_notifications_handler(update: dict, ctx: dict) -> None:
    """A9Y1F3: Notification settings view (same as main settings)."""
    await settings_handler(update, ctx)


async def settings_quiet_hours_handler(update: dict, ctx: dict) -> None:
    """A9Y1F4: Quiet hours picker."""
    chat_id   = ctx["chat_id"]
    client    = ctx["client"]
    locale    = ctx.get("locale", "bn")
    db, redis = _db_redis(ctx)

    bot_ctx = await BotContextService(redis, db).resolve(ctx["telegram_user_id"])
    if bot_ctx:
        locale = bot_ctx.get("locale", locale)

    kb = InlineKeyboards.quiet_hours_picker(locale)
    await client.send_message(chat_id, t("settings_menu.quiet_hours_header", locale), reply_markup=kb)


async def unlink_handler(update: dict, ctx: dict) -> None:
    """A9Y1F5: Confirm unlink prompt."""
    chat_id   = ctx["chat_id"]
    client    = ctx["client"]
    locale    = ctx.get("locale", "bn")
    db, redis = _db_redis(ctx)

    bot_ctx = await BotContextService(redis, db).resolve(ctx["telegram_user_id"])
    if bot_ctx:
        locale = bot_ctx.get("locale", locale)

    kb = InlineKeyboards.yes_no("unlink:confirm", "menu:main", locale)
    await client.send_message(chat_id, t("settings_menu.unlink_confirm", locale), reply_markup=kb)


async def settings_callback(update: dict, ctx: dict) -> None:
    """A9Y1F6: Handle settings:*, notify:*, qh:*, unlink:* callbacks."""
    cq      = ctx.get("callback_query", {})
    cb      = ctx.get("callback_data", "")
    chat_id = ctx["chat_id"]
    client  = ctx["client"]
    locale  = ctx.get("locale", "bn")
    db, redis = _db_redis(ctx)
    tg_uid  = ctx["telegram_user_id"]

    await client.answer_callback_query(cq.get("id", ""))

    bot_ctx   = await BotContextService(redis, db).resolve(tg_uid)
    if not bot_ctx:
        return
    locale    = bot_ctx.get("locale", locale)
    user_id   = bot_ctx.get("user_id", "")
    tenant_id = bot_ctx.get("tenant_id", "")
    svc       = UserSettingsService(db)

    # Language change  (settings:lang:xx  or legacy settings:locale:xx)
    if cb.startswith("settings:lang:") or cb.startswith("settings:locale:"):
        parts      = cb.split(":")
        new_locale = parts[2]
        await svc.set_locale(tenant_id=tenant_id, user_id=user_id, locale=new_locale)
        invalidate_cache(new_locale)
        await BotStateService(redis, db).transition(tg_uid, "IDLE", locale=new_locale)
        ctx["locale"] = new_locale
        await client.send_message(chat_id, t("settings.locale_changed", new_locale, locale=new_locale.upper()))
        return

    # Notification toggle (notify:deadline / notify:assignment / notify:broadcast / notify:digest)
    if cb.startswith("notify:"):
        notif_type = cb.split(":")[1]
        prefs      = await svc.get(tenant_id=tenant_id, user_id=user_id)
        key        = f"notify_{notif_type}"
        new_val    = not prefs.get(key, True)
        await svc.update(tenant_id=tenant_id, user_id=user_id, **{key: new_val})
        status = t("settings.on", locale) if new_val else t("settings.off", locale)
        await client.send_message(chat_id, t("settings.notify_toggled", locale, status=status, type=notif_type))
        await settings_handler(update, ctx)
        return

    # Legacy notify format
    if cb.startswith("settings:notify:"):
        notif_type = cb.split(":")[2]
        prefs      = await svc.get(tenant_id=tenant_id, user_id=user_id)
        key        = f"notify_{notif_type}"
        new_val    = not prefs.get(key, True)
        await svc.update(tenant_id=tenant_id, user_id=user_id, **{key: new_val})
        status = t("settings.on", locale) if new_val else t("settings.off", locale)
        await client.send_message(chat_id, t("settings.notify_toggled", locale, status=status, type=notif_type))
        await settings_handler(update, ctx)
        return

    # Quiet hours
    if cb.startswith("qh:set:"):
        parts = cb.split(":")
        start, end = parts[2], parts[3]
        await svc.update(tenant_id=tenant_id, user_id=user_id, quiet_start=start, quiet_end=end)
        await client.send_message(chat_id, t("settings.quiet_hours_set", locale, start=start, end=end))
        return

    if cb == "qh:off":
        await svc.update(tenant_id=tenant_id, user_id=user_id, quiet_start=None, quiet_end=None)
        await client.send_message(chat_id, t("settings.quiet_hours_off_msg", locale))
        return

    # Unlink
    if cb == "unlink:confirm":
        from apps.api.app.services.bot_user_service import BotUserService
        await BotUserService(db).unlink(tenant_id=tenant_id, user_id=user_id)
        await client.send_message(chat_id, t("welcome.unlinked", locale), reply_markup=ReplyKeyboards.remove())
        return

    # Fallback: refresh settings panel
    await settings_handler(update, ctx)


async def settings_menu_handler(update: dict, ctx: dict) -> None:
    """A9Y1F7: Reply keyboard 'Settings' button — open sub-menu."""
    await settings_handler(update, ctx)
