# ID: AX42      |  Local: A25Y1         |  Module: X26 (M25)
# Functions: A25Y1F1 A25Y1F2 A25Y1F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.admin")


async def _require_admin(ctx: dict) -> dict | None:
    """Returns bot_ctx if user is owner/manager, else None and sends error."""
    telegram_user_id = ctx["telegram_user_id"]
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    app = ctx.get("app")

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
    if not bot_ctx:
        await client.send_message(chat_id, t("error.not_linked", locale))
        return None

    role = bot_ctx.get("project_role") or bot_ctx.get("role")
    if role not in ("owner", "manager"):
        await client.send_message(chat_id, t("admin.no_permission", locale))
        return None

    return bot_ctx


async def admin_panel_handler(update: dict, ctx: dict) -> None:
    """A25Y1F1: Show admin panel with project stats."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    app = ctx.get("app")

    bot_ctx = await _require_admin(ctx)
    if not bot_ctx:
        return

    db = app.state.db if app else None
    project_id = bot_ctx.get("project_id")
    tenant_id = bot_ctx.get("tenant_id")
    project_name = bot_ctx.get("project_name", "—")

    member_count = 0
    task_count = 0

    if project_id and db:
        async with db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            mc = await session.execute(
                "SELECT COUNT(*) FROM project_members WHERE project_id = :pid",
                {"pid": str(project_id)},
            )
            member_count = mc.scalar() or 0
            tc = await session.execute(
                "SELECT COUNT(*) FROM tasks WHERE project_id = :pid AND archived_at IS NULL",
                {"pid": str(project_id)},
            )
            task_count = tc.scalar() or 0

    text = t("admin.panel_header", locale,
             project_name=escape_md(project_name),
             member_count=member_count,
             task_count=task_count)

    keyboard = InlineKeyboards.from_rows([
        [
            InlineKeyboards.button("📋 Create Task", "admin:create_task"),
            InlineKeyboards.button("📢 Broadcast", "admin:broadcast"),
        ],
        [
            InlineKeyboards.button("👥 Members", "admin:members"),
            InlineKeyboards.button("📈 Progress", "admin:progress"),
        ],
        [InlineKeyboards.button(t("button.menu", locale), "menu:main")],
    ])

    await client.send_message(chat_id, text, reply_markup=keyboard)


async def admin_action_callback(update: dict, ctx: dict) -> None:
    """A25Y1F2: Route admin: callbacks."""
    callback_query = ctx.get("callback_query", {})
    callback_data = ctx.get("callback_data", "")
    await ctx["client"].answer_callback_query(callback_query.get("id", ""))

    bot_ctx = await _require_admin(ctx)
    if not bot_ctx:
        return

    action = callback_data.replace("admin:", "")

    if action == "create_task":
        from apps.api.app.integrations.telegram.wizards.task_create import wizard_task_start
        await wizard_task_start(update, ctx)
    elif action == "broadcast":
        from apps.api.app.integrations.telegram.wizards.broadcast import broadcast_wizard_start
        await broadcast_wizard_start(update, ctx)
    elif action == "members":
        from apps.api.app.integrations.telegram.handlers.admin.members import admin_members_handler
        await admin_members_handler(update, ctx)
    elif action == "progress":
        from apps.api.app.integrations.telegram.handlers.admin.progress import admin_progress_handler
        await admin_progress_handler(update, ctx)
    else:
        await admin_panel_handler(update, ctx)
