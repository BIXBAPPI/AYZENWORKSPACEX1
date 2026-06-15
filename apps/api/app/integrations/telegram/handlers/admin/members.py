# ID: AX46      |  Local: A28Y1         |  Module: X29 (M28)
# Functions: A28Y1F1 A28Y1F2
# Processes: XN01 XN02
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.admin.members")


async def admin_members_handler(update: dict, ctx: dict) -> None:
    """A28Y1F1: Show project member list for admin."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    app = ctx.get("app")
    telegram_user_id = ctx["telegram_user_id"]

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    from apps.api.app.services.bot_context_service import BotContextService
    bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
    if not bot_ctx or not bot_ctx.get("project_id"):
        await client.send_message(chat_id, t("project.empty", locale))
        return

    tenant_id = bot_ctx["tenant_id"]
    project_id = bot_ctx["project_id"]

    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
        result = await session.execute(
            """
            SELECT u.full_name, u.email, pm.role, pm.assigned_at,
                   COUNT(tc.id) as done_count
            FROM project_members pm
            JOIN users u ON u.id = pm.user_id
            LEFT JOIN task_completions tc ON tc.user_id = u.id
            WHERE pm.project_id = :pid
            GROUP BY u.full_name, u.email, pm.role, pm.assigned_at
            ORDER BY done_count DESC
            LIMIT 20
            """,
            {"pid": str(project_id)},
        )
        members = result.fetchall()

    if not members:
        await client.send_message(chat_id, "👥 No members found.")
        return

    lines = [f"👥 *Members — {escape_md(bot_ctx.get('project_name', '—'))}*\n"]
    for m in members:
        name = escape_md(m.full_name or m.email or "—")
        role_icon = "👑" if m.role == "owner" else "🔑" if m.role == "manager" else "👤"
        lines.append(f"{role_icon} {name} — {m.done_count} tasks")

    text = "\n".join(lines)
    keyboard = InlineKeyboards.from_rows([
        [InlineKeyboards.button("◀ Admin Panel", "admin:panel")],
        [InlineKeyboards.button(t("button.menu", locale), "menu:main")],
    ])

    await client.send_message(chat_id, text, reply_markup=keyboard)
