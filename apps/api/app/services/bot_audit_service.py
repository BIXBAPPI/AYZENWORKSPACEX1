# ID: AX50      |  Local: A30Y1         |  Module: X31 (M30)
# Functions: A30Y1F1 A30Y1F2 A30Y1F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger("ayzen.audit")


class BotAuditService:
    """Write audit entries to bot_audit_log — never raises."""

    def __init__(self, db_session_factory: Any) -> None:
        self._db = db_session_factory

    async def log(
        self,
        user_id: UUID | str | None,
        tenant_id: UUID | str | None,
        action: str,
        payload: dict | None = None,
        telegram_msg_id: int | None = None,
        telegram_chat_id: int | None = None,
    ) -> None:
        """A30Y1F1: Insert audit log row — silently swallows all errors."""
        import json
        try:
            async with self._db() as session:
                await session.execute(
                    """
                    INSERT INTO bot_audit_log
                        (user_id, tenant_id, action, payload_json, telegram_msg_id, telegram_chat_id)
                    VALUES (:uid, :tid, :action, :payload, :msg_id, :chat_id)
                    """,
                    {
                        "uid": str(user_id) if user_id else None,
                        "tid": str(tenant_id) if tenant_id else None,
                        "action": action,
                        "payload": json.dumps(payload or {}),
                        "msg_id": telegram_msg_id,
                        "chat_id": telegram_chat_id,
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.warning("Audit log write failed action=%s: %s", action, exc)

    async def log_from_ctx(self, ctx: dict, action: str, payload: dict | None = None) -> None:
        """A30Y1F2: Log using BotRouter context dict."""
        bot_ctx = ctx.get("bot_ctx") or {}
        user_id = bot_ctx.get("user_id")
        tenant_id = bot_ctx.get("tenant_id")
        msg_id = ctx.get("last_message_id")
        chat_id = ctx.get("chat_id")
        await self.log(user_id, tenant_id, action, payload, msg_id, chat_id)

    async def get_recent(self, tenant_id: UUID, limit: int = 50) -> list[dict]:
        """A30Y1F3: Get recent audit entries for tenant."""
        async with self._db() as session:
            result = await session.execute(
                """
                SELECT a.action, a.payload_json, a.created_at, u.email as user_email
                FROM bot_audit_log a
                LEFT JOIN users u ON u.id = a.user_id
                WHERE a.tenant_id = :tid
                ORDER BY a.created_at DESC
                LIMIT :limit
                """,
                {"tid": str(tenant_id), "limit": limit},
            )
            return [dict(r._mapping) for r in result.fetchall()]
