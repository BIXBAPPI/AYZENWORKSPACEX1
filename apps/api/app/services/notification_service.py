# ID: AX63      |  Local: A40Y1         |  Module: X44 (M43)
# Functions: A40Y1F1 A40Y1F2 A40Y1F3 A40Y1F4
# Processes: XN01 XN02 XN03 XN04
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from apps.api.app.services.i18n_service import t

logger = logging.getLogger("ayzen.notification")

_QUIET_QUEUE_KEY_PREFIX = "ayzen:quiet_queue:"


class NotificationService:
    """Sends notifications to Telegram users with quiet-hours awareness."""

    def __init__(self, redis: Any | None, db_session_factory: Any, telegram_client: Any) -> None:
        self._redis = redis
        self._db = db_session_factory
        self._client = telegram_client

    # XN01  Send or Queue
    async def send_or_queue(
        self,
        telegram_user_id: int,
        message_key: str,
        locale: str = "bn",
        **kwargs: Any,
    ) -> None:
        """
        Check quiet hours; if in quiet window → queue in Redis sorted set;
        else send immediately.
        """
        in_quiet = await self._in_quiet_hours(telegram_user_id)
        text = t(message_key, locale, **kwargs)

        if in_quiet:
            await self._enqueue(telegram_user_id, text)
        else:
            try:
                await self._client.send_message(telegram_user_id, text)
            except Exception as exc:
                logger.warning("Notification send failed uid=%d: %s", telegram_user_id, exc)

    # XN02  Check quiet hours
    async def _in_quiet_hours(self, telegram_user_id: int) -> bool:
        if not self._db:
            return False
        try:
            async with self._db() as session:
                result = await session.execute(
                    """
                    SELECT us.quiet_hours_start, us.quiet_hours_end
                    FROM user_settings us
                    JOIN users u ON u.id = us.user_id
                    WHERE u.telegram_user_id = :tid
                    """,
                    {"tid": telegram_user_id},
                )
                row = result.fetchone()
                if not row or not row.quiet_hours_start or not row.quiet_hours_end:
                    return False

            now_time = datetime.now(timezone.utc).time().replace(second=0, microsecond=0)
            start = row.quiet_hours_start
            end = row.quiet_hours_end

            if start <= end:
                return start <= now_time <= end
            else:  # Spans midnight
                return now_time >= start or now_time <= end
        except Exception:
            return False

    # XN03  Queue notification
    async def _enqueue(self, telegram_user_id: int, text: str) -> None:
        if not self._redis:
            return
        import json
        import time
        key = f"{_QUIET_QUEUE_KEY_PREFIX}{telegram_user_id}"
        payload = json.dumps({"text": text, "queued_at": time.time()})
        try:
            await self._redis.rpush(key, payload)
            await self._redis.expire(key, 86400)  # Expire in 24 hours
        except Exception as exc:
            logger.warning("Queue notification failed: %s", exc)

    # XN04  Flush queued notifications
    async def flush_queue(self, telegram_user_id: int) -> int:
        """Send all queued notifications for user. Returns count sent."""
        if not self._redis:
            return 0

        import json
        key = f"{_QUIET_QUEUE_KEY_PREFIX}{telegram_user_id}"
        count = 0
        try:
            while True:
                item = await self._redis.lpop(key)
                if not item:
                    break
                payload = json.loads(item)
                await self._client.send_message(telegram_user_id, payload.get("text", ""))
                count += 1
                await asyncio.sleep(0.05)
        except Exception as exc:
            logger.warning("Flush queue error uid=%d: %s", telegram_user_id, exc)
        return count

    async def notify_deadline(
        self, telegram_user_id: int, task_title: str, deadline: str, remaining: str, locale: str = "bn"
    ) -> None:
        await self.send_or_queue(telegram_user_id, "notification.deadline", locale,
                                  task_title=task_title, deadline=deadline, remaining=remaining)

    async def notify_assignment(
        self, telegram_user_id: int, task_title: str, project_name: str, deadline: str, locale: str = "bn"
    ) -> None:
        await self.send_or_queue(telegram_user_id, "notification.assignment", locale,
                                  task_title=task_title, project_name=project_name, deadline=deadline)
