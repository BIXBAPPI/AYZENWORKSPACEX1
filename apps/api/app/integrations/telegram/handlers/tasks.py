# ID: AX34      |  Local: A17Y1         |  Module: X18 (M17)
# Functions: A17Y1F1 A17Y1F2 A17Y1F3 A17Y1F4 A17Y1F5
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.integrations.telegram.keyboards.builders import KeyboardBuilders
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.tasks")

TYPE_EMOJI = {"twitter": "🐦", "discord": "💬", "onchain": "🔗", "form": "📝", "other": "📋"}


async def _get_project_tasks(db: Any, user_id: UUID, project_id: UUID, tenant_id: UUID) -> list[dict]:
    async with db() as session:
        await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
        result = await session.execute(
            text("""
            SELECT t.id, t.title, t.task_type, t.target_url, t.points_per_account,
                   t.deadline, t.max_slots_per_user,
                   COUNT(DISTINCT tc.id) FILTER (WHERE tc.user_id = :uid) as done_count,
                   COUNT(DISTINCT asl.id) as slot_count
            FROM tasks t
            LEFT JOIN task_completions tc ON tc.task_id = t.id AND tc.user_id = :uid
            LEFT JOIN account_slots asl ON asl.user_id = :uid AND asl.project_id = :pid
            WHERE t.project_id = :pid
              AND t.archived_at IS NULL
              AND (t.deadline IS NULL OR t.deadline > NOW())
            GROUP BY t.id, t.title, t.task_type, t.target_url, t.points_per_account, t.deadline, t.max_slots_per_user
            ORDER BY t.created_at DESC
            """),
            {"uid": str(user_id), "pid": str(project_id)},
        )
        return [dict(r._mapping) for r in result.fetchall()]


async def tasks_handler(update: dict, ctx: dict) -> None:
    """A17Y1F1: Show user's task list for active project."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
    if not bot_ctx:
        await client.send_message(chat_id, t("error.not_linked", locale))
        return

    project_id = bot_ctx.get("project_id")
    if not project_id:
        await client.send_message(chat_id, t("project.empty", locale))
        return

    locale = bot_ctx.get("locale", "bn")
    user_id = bot_ctx["user_id"]
    tenant_id = bot_ctx["tenant_id"]
    project_name = bot_ctx.get("project_name", "—")

    tasks = await _get_project_tasks(db, user_id, project_id, tenant_id)

    state_svc = BotStateService(redis, db)
    await state_svc.transition(telegram_user_id, "TASK_LIST", project_id=project_id, page=0)

    header = t("task.list_header", locale, project_name=escape_md(project_name))

    if not tasks:
        await client.send_message(chat_id, header + "\n\n" + t("task.empty", locale))
        return

    keyboard = KeyboardBuilders.task_list(tasks, page=0, locale=locale)
    await client.send_message(chat_id, header, reply_markup=keyboard)


async def task_page_callback(update: dict, ctx: dict) -> None:
    """A17Y1F2: Handle task_page:{n} pagination."""
    callback_query = ctx.get("callback_query", {})
    callback_data = ctx.get("callback_data", "")
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")

    await client.answer_callback_query(callback_query.get("id", ""))

    try:
        page = int(callback_data.split(":")[1])
    except (IndexError, ValueError):
        page = 0

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
    if not bot_ctx or not bot_ctx.get("project_id"):
        return

    tasks = await _get_project_tasks(db, bot_ctx["user_id"], bot_ctx["project_id"], bot_ctx["tenant_id"])
    keyboard = KeyboardBuilders.task_list(tasks, page=page, locale=locale)

    msg_id = callback_query.get("message", {}).get("message_id")
    if msg_id:
        await client.edit_message_reply_markup(chat_id, msg_id, keyboard)

    state_svc = BotStateService(redis, db)
    await state_svc.transition(telegram_user_id, "TASK_LIST", page=page)


async def task_filter_callback(update: dict, ctx: dict) -> None:
    """A17Y1F3: Filter task list."""
    callback_query = ctx.get("callback_query", {})
    await ctx["client"].answer_callback_query(callback_query.get("id", ""))
    await tasks_handler(update, ctx)


async def task_detail_callback(update: dict, ctx: dict) -> None:
    """A17Y1F4: Show task detail on task:{uuid} callback."""
    callback_query = ctx.get("callback_query", {})
    callback_data = ctx.get("callback_data", "")
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")

    await client.answer_callback_query(callback_query.get("id", ""))

    task_id = callback_data.replace("task:", "")

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)
    if not bot_ctx:
        return

    tenant_id = bot_ctx.get("tenant_id")
    user_id = bot_ctx.get("user_id")

    async with db() as session:
        await session.execute(text(f"SET LOCAL app.current_tenant = '{tenant_id}'"))
        result = await session.execute(
            text("""
            SELECT t.id, t.title, t.task_type, t.target_url, t.points_per_account,
                   t.deadline, t.project_id,
                   p.name as project_name,
                   COUNT(DISTINCT tc.id) FILTER (WHERE tc.user_id = :uid) as done_count,
                   COUNT(DISTINCT asl.id) as slot_count
            FROM tasks t
            JOIN projects p ON p.id = t.project_id
            LEFT JOIN task_completions tc ON tc.task_id = t.id AND tc.user_id = :uid
            LEFT JOIN account_slots asl ON asl.user_id = :uid AND asl.project_id = t.project_id
            WHERE t.id = :tid
            GROUP BY t.id, t.title, t.task_type, t.target_url, t.points_per_account, t.deadline, t.project_id, p.name
            """),
            {"tid": task_id, "uid": str(user_id)},
        )
        task = result.fetchone()

    if not task:
        await client.send_message(chat_id, t("task.not_found", locale))
        return

    state_svc = BotStateService(redis, db)
    await state_svc.transition(telegram_user_id, "TASK_DETAIL", task_id=UUID(str(task.id)))

    deadline_str = task.deadline.strftime("%Y\\-%m\\-%d") if task.deadline else "None"
    emoji = TYPE_EMOJI.get(task.task_type, "📋")
    short_id = str(task.id)[:8]

    text = t("task.detail_template", locale,
             short_id=escape_md(short_id),
             type_emoji=emoji,
             title=escape_md(task.title),
             project_name=escape_md(task.project_name),
             target_url=escape_md(str(task.target_url or "—")),
             points=task.points_per_account,
             deadline=deadline_str,
             done=task.done_count,
             total=task.slot_count)

    rows = []
    if task.target_url:
        rows.append([InlineKeyboards.url_button(t("task.go_to_target", locale), str(task.target_url))])
    rows.append([
        InlineKeyboards.button(t("task.submit_single", locale), f"task_action:single:{task.id}"),
        InlineKeyboards.button(t("task.submit_batch", locale), f"task_action:batch:{task.id}"),
    ])
    rows.append(InlineKeyboards.back_menu_row(locale))
    keyboard = InlineKeyboards.from_rows(rows)

    await client.send_message(chat_id, text, reply_markup=keyboard)


async def task_action_callback(update: dict, ctx: dict) -> None:
    """A17Y1F5: Route task actions — single/batch submit."""
    callback_query = ctx.get("callback_query", {})
    callback_data = ctx.get("callback_data", "")
    await ctx["client"].answer_callback_query(callback_query.get("id", ""))

    parts = callback_data.split(":")
    if len(parts) < 3:
        return

    action = parts[1]  # single | batch | target
    task_id = parts[2]

    ctx["resolved_task_id"] = task_id

    if action == "single":
        from apps.api.app.integrations.telegram.handlers.submit_single import submit_single_entry
        await submit_single_entry(update, ctx)
    elif action == "batch":
        from apps.api.app.integrations.telegram.handlers.submit_batch import batch_submit_entry
        await batch_submit_entry(update, ctx)
