# ID: AX48      |  Local: A31Y1         |  Module: X32 (M31)
# Functions: A31Y1F1 A31Y1F2 A31Y1F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("ayzen.jobs.deadline_reminder")


async def run() -> None:
    """
    A31Y1F1: APScheduler job — runs every 15 minutes.
    Finds tasks with deadlines in next 24h that haven't been notified.
    Sends deadline alerts to assigned users who haven't completed the task.
    """
    from apps.api.app.integrations.telegram.client import get_telegram_client
    from apps.api.app.services.notification_service import NotificationService

    # Import app-level db/redis from global state
    try:
        from apps.api.main import session_factory, redis_client
    except ImportError:
        logger.error("Cannot import app state for deadline_reminder job")
        return

    if not session_factory:
        return

    client = get_telegram_client()
    notif_svc = NotificationService(redis_client, session_factory, client)

    now = datetime.now(timezone.utc)
    deadline_window = now + timedelta(hours=24)

    try:
        async with session_factory() as session:
            result = await session.execute(
                """
                SELECT
                    t.id as task_id, t.title, t.deadline, t.project_id, t.tenant_id,
                    p.name as project_name,
                    u.telegram_user_id, u.id as user_id,
                    COALESCE(ubs.locale, 'bn') as locale
                FROM tasks t
                JOIN projects p ON p.id = t.project_id
                JOIN project_members pm ON pm.project_id = t.project_id
                JOIN users u ON u.id = pm.user_id
                LEFT JOIN user_bot_state ubs ON ubs.user_id = u.id
                WHERE t.deadline BETWEEN :now AND :window
                  AND t.notify_sent = false
                  AND t.archived_at IS NULL
                  AND u.telegram_user_id IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM task_completions tc
                    JOIN account_slots asl ON asl.id = tc.account_slot_id
                    WHERE tc.task_id = t.id AND asl.user_id = u.id
                  )
                """,
                {"now": now, "window": deadline_window},
            )
            rows = result.fetchall()

        notified_task_ids: set[str] = set()

        for row in rows:
            if not row.telegram_user_id:
                continue

            deadline_str = row.deadline.strftime("%Y-%m-%d %H:%M UTC") if row.deadline else "—"
            remaining = str(row.deadline - now).split(".")[0] if row.deadline else "—"

            await notif_svc.notify_deadline(
                telegram_user_id=row.telegram_user_id,
                task_title=row.title,
                deadline=deadline_str,
                remaining=remaining,
                locale=row.locale,
            )
            notified_task_ids.add(str(row.task_id))

        # Mark tasks as notified (notify_sent = true)
        if notified_task_ids:
            async with session_factory() as session:
                for task_id in notified_task_ids:
                    await session.execute(
                        "UPDATE tasks SET notify_sent = true WHERE id = :tid",
                        {"tid": task_id},
                    )
                await session.commit()

        logger.info("Deadline reminder: notified %d task assignments", len(rows))

    except Exception as exc:
        logger.exception("Deadline reminder job failed: %s", exc)
