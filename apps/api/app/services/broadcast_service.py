# ID: AX45      |  Local: A27Y2         |  Module: X28 (M27)
# Functions: A27Y2F1 A27Y2F2 A27Y2F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from apps.api.app.services.i18n_service import t

logger = logging.getLogger("ayzen.broadcast")

_BROADCAST_DELAY = 0.05  # 50ms between sends to avoid Telegram flooding


class BroadcastService:
    """Sends broadcast messages to project members via Telegram."""

    def __init__(self, db_session_factory: Any, telegram_client: Any) -> None:
        self._db = db_session_factory
        self._client = telegram_client

    # XN01  Get target users
    async def _get_project_members_with_telegram(
        self, project_id: UUID, tenant_id: UUID
    ) -> list[dict]:
        """SELECT users with telegram_user_id for project members."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT u.id, u.telegram_user_id, u.full_name, ubs.locale
                FROM project_members pm
                JOIN users u ON u.id = pm.user_id
                LEFT JOIN user_bot_state ubs ON ubs.user_id = u.id
                WHERE pm.project_id = :pid
                  AND u.telegram_user_id IS NOT NULL
                """,
                {"pid": str(project_id)},
            )
            return [dict(r._mapping) for r in result.fetchall()]

    # XN02  Send broadcast
    async def send_project_broadcast(
        self,
        project_id: UUID,
        tenant_id: UUID,
        sender_id: UUID,
        message: str,
        locale: str = "bn",
    ) -> int:
        """
        Send message to all project members with Telegram linked.
        Creates bot_broadcasts record. Returns count sent.
        """
        members = await self._get_project_members_with_telegram(project_id, tenant_id)
        target_count = len(members)
        sent_count = 0
        failed_count = 0

        # Create broadcast record
        broadcast_id = None
        async with self._db() as session:
            result = await session.execute(
                """
                INSERT INTO bot_broadcasts
                    (tenant_id, sender_id, project_id, message, target_count, status)
                VALUES (:tid, :sid, :pid, :msg, :tc, 'sending')
                RETURNING id
                """,
                {
                    "tid": str(tenant_id), "sid": str(sender_id),
                    "pid": str(project_id), "msg": message, "tc": target_count,
                },
            )
            row = result.fetchone()
            broadcast_id = row.id if row else None
            await session.commit()

        sender_name = "Admin"  # Could look up actual name
        text = t("notification.broadcast", locale, sender=sender_name, message=message)

        for member in members:
            try:
                await self._client.send_message(
                    member["telegram_user_id"],
                    text,
                )
                sent_count += 1
            except Exception as exc:
                logger.warning("Broadcast send failed uid=%s: %s", member["telegram_user_id"], exc)
                failed_count += 1
            await asyncio.sleep(_BROADCAST_DELAY)

        # Update broadcast record
        if broadcast_id:
            async with self._db() as session:
                await session.execute(
                    """
                    UPDATE bot_broadcasts SET
                        sent_count = :sc, failed_count = :fc,
                        status = 'completed', completed_at = NOW()
                    WHERE id = :bid
                    """,
                    {"sc": sent_count, "fc": failed_count, "bid": str(broadcast_id)},
                )
                await session.commit()

        logger.info("Broadcast done: sent=%d failed=%d", sent_count, failed_count)
        return sent_count

    # XN03  Get broadcast history
    async def get_recent_broadcasts(self, tenant_id: UUID, limit: int = 10) -> list[dict]:
        async with self._db() as session:
            result = await session.execute(
                """
                SELECT b.id, b.message, b.target_count, b.sent_count, b.status, b.created_at,
                       u.full_name as sender_name
                FROM bot_broadcasts b
                LEFT JOIN users u ON u.id = b.sender_id
                WHERE b.tenant_id = :tid
                ORDER BY b.created_at DESC
                LIMIT :limit
                """,
                {"tid": str(tenant_id), "limit": limit},
            )
            return [dict(r._mapping) for r in result.fetchall()]
