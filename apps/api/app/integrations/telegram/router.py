# ID: AX17      |  Local: A4Y4          |  Module: X05 (M04)
# Functions: A4Y4F1
# Processes: XN04
from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

from apps.api.app.integrations.telegram.middleware.rate_limit import TelegramRateLimiter
from apps.api.app.integrations.telegram.middleware.idempotency import IdempotencyGuard
from apps.api.app.services.bot_state_service import BotStateService
from apps.api.app.services.i18n_service import t

logger = logging.getLogger("ayzen.telegram.router")

HandlerFunc = Callable[[dict, dict], Awaitable[None]]


class BotRouter:
    """Telegram update dispatcher. Routes commands, callbacks, and state-driven text."""

    def __init__(
        self,
        state_service: BotStateService,
        rate_limiter: TelegramRateLimiter,
        idempotency: IdempotencyGuard,
        telegram_client: Any,
    ) -> None:
        self._state_service = state_service
        self._rate_limiter = rate_limiter
        self._idempotency = idempotency
        self._client = telegram_client

        self._commands: dict[str, HandlerFunc] = {}
        self._callback_prefixes: dict[str, HandlerFunc] = {}
        self._state_handlers: dict[str, HandlerFunc] = {}

    def register_command(self, command: str, handler: HandlerFunc) -> None:
        self._commands[command.lstrip("/")] = handler

    def register_callback_prefix(self, prefix: str, handler: HandlerFunc) -> None:
        self._callback_prefixes[prefix] = handler

    def register_state_handler(self, state: str, handler: HandlerFunc) -> None:
        self._state_handlers[state] = handler

    # XN04  Handler Router Registration
    async def dispatch(self, update: dict) -> None:
        """Main dispatch method. Defensive — never raises."""
        try:
            await self._dispatch_inner(update)
        except Exception as exc:
            logger.exception("Unhandled error dispatching update: %s", exc)

    async def _dispatch_inner(self, update: dict) -> None:
        # Extract common fields defensively
        message = update.get("message") or update.get("edited_message")
        callback_query = update.get("callback_query")
        inline_query = update.get("inline_query")

        user_data = None
        chat_id = None

        if message:
            user_data = message.get("from")
            chat_id = message.get("chat", {}).get("id")
        elif callback_query:
            user_data = callback_query.get("from")
            chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
        elif inline_query:
            user_data = inline_query.get("from")
        else:
            logger.debug("Unknown update type, skipping")
            return

        if not user_data:
            logger.debug("No user_data in update, skipping")
            return

        telegram_user_id = user_data.get("id")
        if not telegram_user_id:
            return

        # Build context
        ctx: dict[str, Any] = {
            "user_data": user_data,
            "chat_id": chat_id,
            "telegram_user_id": telegram_user_id,
            "client": self._client,
        }

        # Load bot state for locale (needed for error messages)
        bot_state = await self._state_service.get(telegram_user_id)
        locale = bot_state.locale
        ctx["bot_state"] = bot_state
        ctx["locale"] = locale

        # Stateless mode check
        if await self._state_service.is_stateless_mode():
            allowed_stateless = {"start", "help", "menu", "status"}
            text = (message or {}).get("text", "")
            cmd = text.lstrip("/").split()[0].lower() if text.startswith("/") else ""
            if cmd not in allowed_stateless and not callback_query:
                await self._client.send_message(chat_id, t("error.maintenance", locale))
                return

        # Rate limiting
        action_type = "wizard_input" if bot_state.state.startswith("WIZARD_") else "update"
        is_admin = ctx.get("is_admin", False)
        allowed = await self._rate_limiter.check(telegram_user_id, action_type, is_admin)
        if not allowed:
            if chat_id:
                await self._client.send_message(chat_id, t("error.rate_limit", locale))
            return

        # Idempotency check for callback queries
        if callback_query:
            callback_id = callback_query.get("id", "")
            user_id_str = str(user_data.get("id", ""))
            is_new = await self._idempotency.check_and_mark(callback_id, user_id_str)
            if not is_new:
                return
            ctx["callback_query"] = callback_query
            ctx["callback_data"] = callback_query.get("data", "")
            await self._route_callback(update, ctx)
            return

        if inline_query:
            handler = self._commands.get("inline_query")
            if handler:
                await handler(update, ctx)
            return

        if message:
            text = message.get("text", "")
            ctx["text"] = text
            await self._route_message(update, ctx)

    async def _route_message(self, update: dict, ctx: dict) -> None:
        text = ctx.get("text", "")
        chat_id = ctx["chat_id"]
        locale = ctx["locale"]

        if text.startswith("/"):
            parts = text.lstrip("/").split()
            cmd = parts[0].lower().split("@")[0]  # handle /cmd@BotName
            args = parts[1:] if len(parts) > 1 else []
            ctx["args"] = args
            handler = self._commands.get(cmd)
            if handler:
                await handler(update, ctx)
            else:
                await self._client.send_message(chat_id, t("error.unknown", locale))
            return

        # State-driven text input (wizards)
        bot_state = ctx["bot_state"]
        if bot_state.state in self._state_handlers:
            await self._state_handlers[bot_state.state](update, ctx)
            return

        # Menu text buttons
        menu_handler = self._commands.get("menu_text")
        if menu_handler:
            await menu_handler(update, ctx)
        else:
            # Fallback to /menu
            handler = self._commands.get("menu")
            if handler:
                await handler(update, ctx)

    async def _route_callback(self, update: dict, ctx: dict) -> None:
        data = ctx.get("callback_data", "")
        # Match prefix
        for prefix, handler in self._callback_prefixes.items():
            if data.startswith(prefix):
                await handler(update, ctx)
                return
        # Answer unknown callback
        callback_query = ctx.get("callback_query", {})
        if callback_query.get("id"):
            await self._client.answer_callback_query(
                callback_query["id"], t("error.invalid_callback", ctx["locale"])
            )
