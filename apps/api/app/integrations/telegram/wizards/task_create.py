# ID: AX43      |  Local: A26Y1         |  Module: X27 (M26)
# Functions: A26Y1F1 A26Y1F2 A26Y1F3 A26Y1F4
# Processes: XN01 XN02 XN03 XN04
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apps.api.app.services.i18n_service import t, escape_md
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards
from apps.api.app.integrations.telegram.keyboards.reply import ReplyKeyboards

logger = logging.getLogger("ayzen.wizards.task_create")

STEPS = ["title", "task_type", "target_url", "points", "deadline", "confirm"]
TASK_TYPES = ["twitter", "discord", "onchain", "form", "other"]


async def wizard_task_start(update: dict, ctx: dict) -> None:
    """A26Y1F1: Start task creation wizard."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    state_svc = BotStateService(redis, db)
    await state_svc.transition(
        telegram_user_id, "WIZARD_NEW_TASK",
        wizard_step=0,
        wizard_data={},
    )

    cancel_kb = ReplyKeyboards.cancel_only(locale)
    await client.send_message(
        chat_id,
        t("wizard.step_indicator", locale, current=1, total=len(STEPS)) + "\n\n*Task Title দাও:*",
        reply_markup=cancel_kb,
    )


async def wizard_task_step_handler(update: dict, ctx: dict) -> None:
    """A26Y1F2: Process each wizard step."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    text = ctx.get("text", "").strip()
    app = ctx.get("app")

    db = app.state.db if app else None
    redis = app.state.redis if app else None

    if text == t("wizard.cancel", locale):
        await wizard_task_cancel(update, ctx)
        return

    state_svc = BotStateService(redis, db)
    bot_state = await state_svc.get(telegram_user_id)
    step = bot_state.wizard_step
    data = dict(bot_state.wizard_data)

    step_name = STEPS[step] if step < len(STEPS) else "confirm"

    if step_name == "title":
        if len(text) < 3:
            await client.send_message(chat_id, t("wizard.invalid_input", locale))
            return
        data["title"] = text
        await state_svc.transition(telegram_user_id, "WIZARD_NEW_TASK", wizard_step=1, wizard_data=data)
        type_buttons = [[InlineKeyboards.button(tt.title(), f"task_type:{tt}")] for tt in TASK_TYPES]
        await client.send_message(
            chat_id,
            t("wizard.step_indicator", locale, current=2, total=len(STEPS)) + "\n\n*Task type select করো:*",
            reply_markup=InlineKeyboards.from_rows(type_buttons + [InlineKeyboards.back_menu_row(locale)]),
        )

    elif step_name == "task_type":
        if text.lower() in TASK_TYPES:
            data["task_type"] = text.lower()
            await state_svc.transition(telegram_user_id, "WIZARD_NEW_TASK", wizard_step=2, wizard_data=data)
            await client.send_message(chat_id, t("wizard.step_indicator", locale, current=3, total=len(STEPS)) + "\n\n*Target URL দাও:*")
        else:
            await client.send_message(chat_id, t("wizard.invalid_input", locale))

    elif step_name == "target_url":
        if not text.startswith("http"):
            await client.send_message(chat_id, t("wizard.invalid_input", locale))
            return
        data["target_url"] = text
        await state_svc.transition(telegram_user_id, "WIZARD_NEW_TASK", wizard_step=3, wizard_data=data)
        await client.send_message(chat_id, t("wizard.step_indicator", locale, current=4, total=len(STEPS)) + "\n\n*Points per account দাও \\(number\\):*")

    elif step_name == "points":
        try:
            pts = int(text)
            assert pts > 0
        except (ValueError, AssertionError):
            await client.send_message(chat_id, t("wizard.invalid_input", locale))
            return
        data["points"] = pts
        await state_svc.transition(telegram_user_id, "WIZARD_NEW_TASK", wizard_step=4, wizard_data=data)
        await client.send_message(
            chat_id,
            t("wizard.step_indicator", locale, current=5, total=len(STEPS)) + "\n\n*Deadline দাও \\(YYYY\\-MM\\-DD\\) বা skip:*",
            reply_markup=InlineKeyboards.from_rows([[InlineKeyboards.button(t("button.skip", locale), "wizard:skip_deadline")]]),
        )

    elif step_name == "deadline":
        try:
            deadline = datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            data["deadline"] = deadline.isoformat()
        except ValueError:
            await client.send_message(chat_id, t("wizard.invalid_input", locale))
            return
        await _show_confirm(client, chat_id, locale, data, telegram_user_id, state_svc)

    elif step_name == "confirm":
        if text.lower() in ("yes", "হ্যাঁ", "confirm"):
            await _create_task(ctx, data)


async def wizard_task_cancel(update: dict, ctx: dict) -> None:
    """A26Y1F3: Cancel wizard."""
    chat_id = ctx["chat_id"]
    client = ctx["client"]
    locale = ctx.get("locale", "bn")
    telegram_user_id = ctx["telegram_user_id"]
    app = ctx.get("app")
    db = app.state.db if app else None
    redis = app.state.redis if app else None

    from apps.api.app.services.bot_state_service import BotStateService
    await BotStateService(redis, db).transition(telegram_user_id, "IDLE")
    keyboard = ReplyKeyboards.main_menu(locale, True)
    await client.send_message(chat_id, t("wizard.cancelled", locale), reply_markup=keyboard)


async def _show_confirm(client, chat_id, locale, data, telegram_user_id, state_svc) -> None:
    await state_svc.transition(telegram_user_id, "WIZARD_NEW_TASK", wizard_step=5, wizard_data=data)
    text = (
        f"✅ *Confirm task:*\n\n"
        f"📋 Title: {escape_md(data.get('title', ''))}\n"
        f"🏷 Type: {data.get('task_type', '—')}\n"
        f"🔗 URL: {escape_md(data.get('target_url', ''))}\n"
        f"💰 Points: {data.get('points', 0)}\n"
        f"⏰ Deadline: {data.get('deadline', 'None')}"
    )
    keyboard = InlineKeyboards.from_rows([
        [
            InlineKeyboards.button(t("button.confirm", locale), "wizard:confirm_task"),
            InlineKeyboards.button(t("button.cancel", locale), "wizard:cancel"),
        ]
    ])
    await client.send_message(chat_id, text, reply_markup=keyboard)


async def _create_task(ctx: dict, data: dict) -> None:
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

    tenant_id = bot_ctx["tenant_id"]
    project_id = bot_ctx["project_id"]
    user_id = bot_ctx["user_id"]

    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
        await session.execute(
            """
            INSERT INTO tasks (project_id, title, task_type, target_url, points_per_account, deadline, created_by)
            VALUES (:pid, :title, :task_type, :url, :pts, :deadline, :uid)
            """,
            {
                "pid": str(project_id),
                "title": data.get("title"),
                "task_type": data.get("task_type", "other"),
                "url": data.get("target_url"),
                "pts": data.get("points", 0),
                "deadline": data.get("deadline"),
                "uid": str(user_id),
            },
        )
        await session.commit()

    await BotStateService(redis, db).transition(telegram_user_id, "IDLE")
    keyboard = ReplyKeyboards.main_menu(locale, True)
    await client.send_message(
        chat_id,
        t("admin.task_created", locale, title=escape_md(data.get("title", ""))),
        reply_markup=keyboard,
    )
