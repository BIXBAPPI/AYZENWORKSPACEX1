from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Header, Request, Response

logger = logging.getLogger("ayzen.telegram.webhook")

router = APIRouter()

_TELEGRAM_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")


@router.post("/bot/webhook")
async def webhook_handler(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> Response:
    if _TELEGRAM_SECRET and x_telegram_bot_api_secret_token != _TELEGRAM_SECRET:
        logger.warning("Invalid Telegram webhook secret token — dropping update")
        return Response(status_code=200)

    update: dict = {}
    try:
        update = await request.json()
    except Exception as exc:
        logger.warning("Failed to parse webhook JSON: %s", exc)
        return Response(status_code=200)

    try:
        bot_router = get_bot_router(request.app)
        await bot_router.dispatch(update, app=request.app)
    except Exception as exc:
        logger.exception("Unhandled error in webhook dispatch: %s", exc)

    return Response(status_code=200)


def get_bot_router(app: object) -> object:
    if not hasattr(app.state, "bot_router"):
        from apps.api.app.integrations.telegram.client import get_telegram_client
        from apps.api.app.services.bot_state_service import BotStateService
        from apps.api.app.integrations.telegram.middleware.rate_limit import TelegramRateLimiter
        from apps.api.app.integrations.telegram.middleware.idempotency import IdempotencyGuard
        from apps.api.app.integrations.telegram.router import BotRouter

        redis = getattr(app.state, "redis", None)
        db = app.state.db
        client = get_telegram_client()

        bot_router = BotRouter(
            state_service=BotStateService(redis, db),
            rate_limiter=TelegramRateLimiter(redis),
            idempotency=IdempotencyGuard(redis, db),
            telegram_client=client,
        )

        _register_all_handlers(bot_router)
        app.state.bot_router = bot_router

    return app.state.bot_router


def _register_all_handlers(router: object) -> None:
    from apps.api.app.integrations.telegram.handlers.start import start_handler, link_handler
    from apps.api.app.integrations.telegram.handlers.menu import (
        menu_handler, cancel_handler, menu_callback_handler, menu_text_handler,
    )
    from apps.api.app.integrations.telegram.handlers.help import help_handler
    from apps.api.app.integrations.telegram.handlers.profile import profile_handler, profile_refresh_callback
    from apps.api.app.integrations.telegram.handlers.settings import settings_handler, settings_callback
    from apps.api.app.integrations.telegram.handlers.projects import (
        projects_handler, project_select_callback, project_page_callback, project_detail_callback,
    )
    from apps.api.app.integrations.telegram.handlers.tasks import (
        tasks_handler, task_page_callback, task_filter_callback, task_detail_callback, task_action_callback,
    )
    from apps.api.app.integrations.telegram.handlers.submit_single import (
        submit_single_entry, slot_select_callback, confirm_submit_callback,
    )
    from apps.api.app.integrations.telegram.handlers.submit_batch import (
        batch_submit_entry, toggle_slot_callback, confirm_batch_callback, cancel_batch_callback,
    )
    from apps.api.app.integrations.telegram.handlers.status import status_handler
    from apps.api.app.integrations.telegram.handlers.admin.panel import admin_panel_handler, admin_action_callback
    from apps.api.app.integrations.telegram.handlers.inline_query import inline_query_handler
    from apps.api.app.integrations.telegram.wizards.task_create import (
        wizard_task_start, wizard_task_step_handler, wizard_task_cancel,
    )
    from apps.api.app.integrations.telegram.wizards.slot_setup import (
        wizard_slot_start, wizard_slot_step_handler,
    )
    from apps.api.app.integrations.telegram.wizards.broadcast import (
        broadcast_wizard_start, broadcast_wizard_step,
    )

    router.register_command("start", start_handler)
    router.register_command("link", link_handler)
    router.register_command("menu", menu_handler)
    router.register_command("help", help_handler)
    router.register_command("status", status_handler)
    router.register_command("cancel", cancel_handler)
    router.register_command("settings", settings_handler)
    router.register_command("profile", profile_handler)
    router.register_command("menu_text", menu_text_handler)
    router.register_command("inline_query", inline_query_handler)

    router.register_callback_prefix("menu:", menu_callback_handler)
    router.register_callback_prefix("project:", project_select_callback)
    router.register_callback_prefix("proj_page:", project_page_callback)
    router.register_callback_prefix("proj_detail:", project_detail_callback)
    router.register_callback_prefix("task:", task_detail_callback)
    router.register_callback_prefix("task_page:", task_page_callback)
    router.register_callback_prefix("task_filter:", task_filter_callback)
    router.register_callback_prefix("task_action:", task_action_callback)
    router.register_callback_prefix("submit:", slot_select_callback)
    router.register_callback_prefix("confirm_submit:", confirm_submit_callback)
    router.register_callback_prefix("batch:", toggle_slot_callback)
    router.register_callback_prefix("batch_confirm:", confirm_batch_callback)
    router.register_callback_prefix("batch_cancel:", cancel_batch_callback)
    router.register_callback_prefix("settings:", settings_callback)
    router.register_callback_prefix("profile_refresh:", profile_refresh_callback)
    router.register_callback_prefix("admin:", admin_action_callback)
    router.register_callback_prefix("wizard_cancel:", wizard_task_cancel)
    router.register_callback_prefix("wizard_slot:", wizard_slot_start)
    router.register_callback_prefix("broadcast_wizard:", broadcast_wizard_start)

    router.register_state_handler("WIZARD_NEW_TASK", wizard_task_step_handler)
    router.register_state_handler("WIZARD_NEW_SLOT", wizard_slot_step_handler)
    router.register_state_handler("WIZARD_BROADCAST", broadcast_wizard_step)
