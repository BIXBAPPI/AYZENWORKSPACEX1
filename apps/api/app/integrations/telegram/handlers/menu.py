# ID: AX29      |  Local: A12Y1         |  Module: X13 (M12)
# Functions: A12Y1F1–A12Y1F8
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.integrations.telegram.keyboards.reply import ReplyKeyboards
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.menu")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _db_redis(ctx: dict):
    app = ctx.get("app")
    return (app.state.db if app else None), (app.state.redis if app else None)


async def _resolve(ctx: dict) -> dict | None:
    db, redis = _db_redis(ctx)
    return await BotContextService(redis, db).resolve(ctx["telegram_user_id"])


# ── Main menu ─────────────────────────────────────────────────────────────────

async def menu_handler(update: dict, ctx: dict) -> None:
    """A12Y1F1: /menu — show main menu and return to IDLE state."""
    chat_id = ctx["chat_id"]
    client  = ctx["client"]
    locale  = ctx.get("locale", "bn")
    db, redis = _db_redis(ctx)

    bot_ctx = await BotContextService(redis, db).resolve(ctx["telegram_user_id"])
    if not bot_ctx:
        await client.send_message(chat_id, t("error.not_linked", locale))
        return

    locale   = bot_ctx.get("locale", "bn")
    is_admin = bot_ctx.get("role") in ("owner", "manager")

    await BotStateService(redis, db).transition(ctx["telegram_user_id"], "IDLE", locale=locale)

    kb = ReplyKeyboards.main_menu(locale, is_admin)
    await client.send_message(chat_id, t("menu.header", locale), reply_markup=kb)


async def cancel_handler(update: dict, ctx: dict) -> None:
    """A12Y1F2: /cancel — cancel any wizard state, return to main menu."""
    chat_id   = ctx["chat_id"]
    client    = ctx["client"]
    locale    = ctx.get("locale", "bn")
    db, redis = _db_redis(ctx)

    bot_ctx = await _resolve(ctx)
    if bot_ctx:
        locale = bot_ctx.get("locale", locale)

    is_admin = bot_ctx.get("role") in ("owner", "manager") if bot_ctx else False
    await BotStateService(redis, db).transition(ctx["telegram_user_id"], "IDLE")

    kb = ReplyKeyboards.main_menu(locale, is_admin)
    await client.send_message(chat_id, t("wizard.cancelled", locale), reply_markup=kb)


# ── Inline menu: callbacks ────────────────────────────────────────────────────

async def menu_callback_handler(update: dict, ctx: dict) -> None:
    """A12Y1F3: Handle menu:* callbacks — navigation."""
    cq      = ctx.get("callback_query", {})
    cb      = ctx.get("callback_data", "")
    client  = ctx["client"]
    db, redis = _db_redis(ctx)

    await client.answer_callback_query(cq.get("id", ""))
    action = cb.replace("menu:", "")

    if action in ("main", "back"):
        await BotStateService(redis, db).transition(ctx["telegram_user_id"], "IDLE")
        await menu_handler(update, ctx)
    elif action == "cancel":
        await cancel_handler(update, ctx)


# ── Sub-menu display helpers ──────────────────────────────────────────────────

async def _show_submenu(update: dict, ctx: dict, submenu: str) -> None:
    chat_id   = ctx["chat_id"]
    client    = ctx["client"]
    locale    = ctx.get("locale", "bn")
    db, redis = _db_redis(ctx)

    bot_ctx = await BotContextService(redis, db).resolve(ctx["telegram_user_id"])
    if not bot_ctx:
        await client.send_message(chat_id, t("error.not_linked", locale))
        return
    locale = bot_ctx.get("locale", locale)

    builders = {
        "tasks":     (ReplyKeyboards.tasks_submenu,     "tasks_menu.header"),
        "analytics": (ReplyKeyboards.analytics_submenu, "analytics_menu.header"),
        "points":    (ReplyKeyboards.points_submenu,    "points_menu.header"),
        "rewards":   (ReplyKeyboards.rewards_submenu,   "rewards_menu.header"),
        "settings":  (ReplyKeyboards.settings_submenu,  "settings_menu.header"),
        "admin":     (ReplyKeyboards.admin_submenu,     "admin_menu.header"),
    }
    kb_fn, header_key = builders.get(submenu, (ReplyKeyboards.main_menu, "menu.header"))
    kb = kb_fn(locale)
    await client.send_message(chat_id, t(header_key, locale), reply_markup=kb)


# ── Reply keyboard text router ────────────────────────────────────────────────

async def menu_text_handler(update: dict, ctx: dict) -> None:
    """A12Y1F4: Route reply keyboard text to the correct handler."""
    text   = ctx.get("text", "")
    locale = ctx.get("locale", "bn")
    action = ReplyKeyboards.match_menu_text(text, locale)

    if not action:
        await menu_handler(update, ctx)
        return

    # ── Top-level menu buttons — show sub-menu ───────────────────────────
    if action in ("tasks", "analytics", "points", "rewards", "settings", "admin"):
        await _show_submenu(update, ctx, action)
        return

    # ── Global controls ──────────────────────────────────────────────────
    if action == "back_main":
        await menu_handler(update, ctx)
        return
    if action == "cancel":
        await cancel_handler(update, ctx)
        return
    if action == "wizard_back":
        # Handled by active wizard; fall through to menu as safety
        await menu_handler(update, ctx)
        return

    # ── Direct-action buttons ────────────────────────────────────────────
    if action == "search":
        from apps.api.app.integrations.telegram.handlers.search import search_prompt_handler
        await search_prompt_handler(update, ctx)
    elif action == "pinned":
        from apps.api.app.integrations.telegram.handlers.pins import pins_handler
        await pins_handler(update, ctx)
    elif action == "profile":
        from apps.api.app.integrations.telegram.handlers.profile import profile_handler
        await profile_handler(update, ctx)

    # ── Tasks sub-menu ───────────────────────────────────────────────────
    elif action.startswith("tasks:"):
        filter_key = action.split(":")[1]  # all | deadline | twitter | discord | onchain | form
        from apps.api.app.integrations.telegram.handlers.tasks import tasks_handler
        ctx["task_filter"] = filter_key
        await tasks_handler(update, ctx)

    # ── Analytics sub-menu ───────────────────────────────────────────────
    elif action == "analytics:leaderboard":
        from apps.api.app.integrations.telegram.handlers.leaderboard import leaderboard_handler
        await leaderboard_handler(update, ctx)
    elif action.startswith("analytics:"):
        period = action.split(":")[1]
        from apps.api.app.integrations.telegram.handlers.analytics import analytics_handler
        await analytics_handler(update, ctx, period=period)

    # ── Points sub-menu ──────────────────────────────────────────────────
    elif action == "points:balance":
        from apps.api.app.integrations.telegram.handlers.wallet import wallet_balance_handler
        await wallet_balance_handler(update, ctx)
    elif action == "points:history":
        from apps.api.app.integrations.telegram.handlers.wallet import wallet_history_handler
        await wallet_history_handler(update, ctx)
    elif action == "points:breakdown":
        from apps.api.app.integrations.telegram.handlers.wallet import wallet_breakdown_handler
        await wallet_breakdown_handler(update, ctx)
    elif action == "points:referral":
        from apps.api.app.integrations.telegram.handlers.referral import referral_handler
        await referral_handler(update, ctx)

    # ── Rewards sub-menu ─────────────────────────────────────────────────
    elif action == "rewards:badges":
        from apps.api.app.integrations.telegram.handlers.achievements import achievements_handler
        await achievements_handler(update, ctx)
    elif action == "rewards:milestones":
        from apps.api.app.integrations.telegram.handlers.achievements import milestones_handler
        await milestones_handler(update, ctx)
    elif action == "rewards:streak":
        from apps.api.app.integrations.telegram.handlers.achievements import streak_handler
        await streak_handler(update, ctx)
    elif action == "rewards:top_earners":
        from apps.api.app.integrations.telegram.handlers.leaderboard import leaderboard_handler
        await leaderboard_handler(update, ctx)

    # ── Settings sub-menu ────────────────────────────────────────────────
    elif action == "settings:language":
        from apps.api.app.integrations.telegram.handlers.settings import settings_language_handler
        await settings_language_handler(update, ctx)
    elif action == "settings:notifications":
        from apps.api.app.integrations.telegram.handlers.settings import settings_notifications_handler
        await settings_notifications_handler(update, ctx)
    elif action == "settings:quiet_hours":
        from apps.api.app.integrations.telegram.handlers.settings import settings_quiet_hours_handler
        await settings_quiet_hours_handler(update, ctx)
    elif action == "settings:slots":
        from apps.api.app.integrations.telegram.handlers.settings import settings_handler
        await settings_handler(update, ctx)
    elif action == "settings:unlink":
        from apps.api.app.integrations.telegram.handlers.settings import unlink_handler
        await unlink_handler(update, ctx)

    # ── Admin sub-menu ───────────────────────────────────────────────────
    elif action == "admin:members":
        from apps.api.app.integrations.telegram.handlers.admin.members import admin_members_handler
        await admin_members_handler(update, ctx)
    elif action == "admin:new_task":
        from apps.api.app.integrations.telegram.wizards.task_create import task_create_start
        await task_create_start(update, ctx)
    elif action == "admin:broadcast":
        from apps.api.app.integrations.telegram.wizards.broadcast import broadcast_start
        await broadcast_start(update, ctx)
    elif action == "admin:exports":
        from apps.api.app.integrations.telegram.handlers.admin.panel import admin_export_handler
        await admin_export_handler(update, ctx)
    elif action == "admin:analytics":
        from apps.api.app.integrations.telegram.handlers.analytics import analytics_handler
        await analytics_handler(update, ctx, period="week")
    elif action == "admin:project_settings":
        from apps.api.app.integrations.telegram.handlers.admin.panel import admin_project_settings_handler
        await admin_project_settings_handler(update, ctx)
    elif action == "admin:transfer":
        from apps.api.app.integrations.telegram.wizards.owner_transfer import transfer_start_handler
        await transfer_start_handler(update, ctx)

    else:
        await menu_handler(update, ctx)
