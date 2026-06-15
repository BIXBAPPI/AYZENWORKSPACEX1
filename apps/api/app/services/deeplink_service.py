# ID: AX57      |  Local: A37Y2         |  Module: X40 (M39)
# Functions: A37Y2F1 A37Y2F2 A37Y2F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging
import os
import secrets
from typing import Any

logger = logging.getLogger("ayzen.deeplink")

_BOT_USERNAME = os.environ.get("BOT_USERNAME", "AyzenBot")
_DEEPLINK_CACHE_TTL = 3600  # 1 hour


class DeeplinkService:
    """Generates and resolves Telegram deep links."""

    def __init__(self, redis: Any | None, db_session_factory: Any) -> None:
        self._redis = redis
        self._db = db_session_factory

    def make_start_link(self, payload: str) -> str:
        """A37Y2F1: Generate t.me/BotName?start=payload link."""
        return f"https://t.me/{_BOT_USERNAME}?start={payload}"

    async def generate_invite_link(self, project_id: str, inviter_id: str) -> str:
        """A37Y2F2: Generate project invite deep link (expires 24h)."""
        token = secrets.token_urlsafe(12)
        key = f"ayzen:invite:{token}"
        import json
        payload = json.dumps({"project_id": project_id, "inviter_id": inviter_id})

        if self._redis:
            await self._redis.set(key, payload, ex=86400)

        return self.make_start_link(f"invite_{token}")

    async def resolve_start_payload(self, payload: str) -> dict | None:
        """A37Y2F3: Resolve /start payload to action dict."""
        if not payload:
            return None

        if payload.startswith("invite_"):
            token = payload[7:]
            key = f"ayzen:invite:{token}"
            if self._redis:
                import json
                raw = await self._redis.get(key)
                if raw:
                    data = json.loads(raw)
                    await self._redis.delete(key)  # single-use
                    return {"action": "join_project", **data}
            return None

        # Link code start (redirect to /link flow)
        if len(payload) == 8 and payload.isalnum():
            return {"action": "link", "code": payload}

        return None
