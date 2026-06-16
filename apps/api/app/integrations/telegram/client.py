# ID: AX14      |  Local: A4Y1          |  Module: X05 (M04)
# Functions: A4Y1F1 A4Y1F2 A4Y1F3 A4Y1F4
# Processes: XN01
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("ayzen.telegram.client")

_BASE_URL = "https://api.telegram.org/bot{token}/{method}"
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.5


class TelegramClient:
    """Async Telegram Bot API client with retry + 429 handling."""

    def __init__(self, token: str | None = None) -> None:
        self._token = token or os.environ["TELEGRAM_BOT_TOKEN"]
        self._client = httpx.AsyncClient(timeout=30.0)

    def _url(self, method: str) -> str:
        return _BASE_URL.format(token=self._token, method=method)

    async def _request(self, method: str, payload: dict[str, Any]) -> dict:
        url = self._url(method)
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await self._client.post(url, json=payload)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    logger.warning("Telegram 429 on %s, retry_after=%ds", method, retry_after)
                    await asyncio.sleep(retry_after)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if not data.get("ok"):
                    logger.error("Telegram API error %s: %s", method, data)
                return data
            except httpx.NetworkError as exc:
                wait = _BACKOFF_BASE ** attempt
                logger.warning("Network error on %s attempt %d: %s — retry in %.1fs", method, attempt + 1, exc, wait)
                if attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(wait)
        return {}

    # XN01  Telegram API Client

    async def send_message(
        self,
        chat_id: int | str,
        text: str,
        reply_markup: dict | None = None,
        parse_mode: str | None = "MarkdownV2",
        **kwargs: Any,
    ) -> dict:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        if reply_markup:
            payload["reply_markup"] = reply_markup
        payload.update(kwargs)
        return await self._request("sendMessage", payload)

    async def edit_message_text(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        reply_markup: dict | None = None,
        parse_mode: str = "MarkdownV2",
        **kwargs: Any,
    ) -> dict:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        payload.update(kwargs)
        try:
            return await self._request("editMessageText", payload)
        except Exception as exc:
            # Suppress MessageNotModified silently
            if "message is not modified" in str(exc).lower():
                return {}
            raise

    async def edit_message_reply_markup(
        self,
        chat_id: int | str,
        message_id: int,
        reply_markup: dict | None = None,
    ) -> dict:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": reply_markup or {},
        }
        try:
            return await self._request("editMessageReplyMarkup", payload)
        except Exception as exc:
            if "message is not modified" in str(exc).lower():
                return {}
            raise

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: str | None = None,
        show_alert: bool = False,
    ) -> dict:
        payload: dict[str, Any] = {
            "callback_query_id": callback_query_id,
            "show_alert": show_alert,
        }
        if text:
            # Truncate to 200 chars as per Telegram limit
            payload["text"] = text[:200]
        try:
            return await self._request("answerCallbackQuery", payload)
        except Exception as exc:
            logger.warning("answerCallbackQuery failed: %s", exc)
            return {}

    async def delete_message(self, chat_id: int | str, message_id: int) -> dict:
        payload = {"chat_id": chat_id, "message_id": message_id}
        try:
            return await self._request("deleteMessage", payload)
        except Exception as exc:
            if "message to delete not found" in str(exc).lower():
                return {}
            logger.warning("deleteMessage failed: %s", exc)
            return {}

    async def send_chat_action(self, chat_id: int | str, action: str = "typing") -> dict:
        return await self._request("sendChatAction", {"chat_id": chat_id, "action": action})

    async def aclose(self) -> None:
        await self._client.aclose()


# Singleton — initialized at startup
_client: TelegramClient | None = None


def get_telegram_client() -> TelegramClient:
    global _client
    if _client is None:
        _client = TelegramClient()
    return _client
