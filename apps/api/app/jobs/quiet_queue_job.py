# ID: AX64      |  Local: A41Y1         |  Module: X45 (M44)
# Functions: A41Y1F1 A41Y1F2
# Processes: XN01 XN02
from __future__ import annotations

import logging

logger = logging.getLogger("ayzen.jobs.quiet_queue")


async def run() -> None:
    """
    A41Y1F1: APScheduler job — runs every 5 minutes.
    Flushes queued notifications for users whose quiet hours have ended.
    """
    try:
        from apps.api.main import session_factory, redis_client
    except ImportError:
        return

    if not session_factory or not redis_client:
        return

    from apps.api.app.integrations.telegram.client import get_telegram_client
    from apps.api.app.services.notification_service import NotificationService

    client = get_telegram_client()
    notif_svc = NotificationService(redis_client, session_factory, client)

    try:
        # Find users with queued notifications that are no longer in quiet hours
        async with session_factory() as session:
            result = await session.execute(
                """
                SELECT u.telegram_user_id
                FROM users u
                JOIN user_settings us ON us.user_id = u.id
                WHERE u.telegram_user_id IS NOT NULL
                  AND (us.quiet_hours_start IS NULL OR us.quiet_hours_end IS NULL
                    OR NOT (
                      CURRENT_TIME BETWEEN us.quiet_hours_start AND us.quiet_hours_end
                    ))
                """,
            )
            users = result.fetchall()

        flushed = 0
        for row in users:
            tid = row.telegram_user_id
            count = await notif_svc.flush_queue(tid)
            if count > 0:
                flushed += count

        if flushed > 0:
            logger.info("Quiet queue flush: sent %d queued notifications", flushed)

    except Exception as exc:
        logger.exception("Quiet queue job failed: %s", exc)
