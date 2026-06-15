# ID: AX49      |  Local: A32Y1         |  Module: X33 (M32)
# Functions: A32Y1F1 A32Y1F2
# Processes: XN01 XN02
from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger("ayzen.jobs.daily_digest")


async def run() -> None:
    """
    A32Y1F1: APScheduler cron job — runs daily at 08:00 UTC.
    Sends a morning digest to all active bot users with pending tasks.
    """
    try:
        from apps.api.main import session_factory, redis_client
    except ImportError:
        return

    if not session_factory:
        return

    from apps.api.app.integrations.telegram.client import get_telegram_client
    from apps.api.app.services.i18n_service import t, escape_md

    client = get_telegram_client()
    today = date.today()

    try:
        async with session_factory() as session:
            result = await session.execute(
                """
                SELECT
                    u.telegram_user_id,
                    COALESCE(ubs.locale, 'bn') as locale,
                    COUNT(DISTINCT t.id) as pending_tasks,
                    ubs.active_project_id,
                    p.name as project_name
                FROM users u
                JOIN user_bot_state ubs ON ubs.user_id = u.id
                LEFT JOIN projects p ON p.id = ubs.active_project_id
                JOIN project_members pm ON pm.project_id = ubs.active_project_id AND pm.user_id = u.id
                JOIN tasks t ON t.project_id = ubs.active_project_id
                    AND t.archived_at IS NULL
                    AND (t.deadline IS NULL OR t.deadline >= NOW())
                WHERE u.telegram_user_id IS NOT NULL
                  AND ubs.active_project_id IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM task_completions tc
                    JOIN account_slots asl ON asl.id = tc.account_slot_id
                    WHERE tc.task_id = t.id AND asl.user_id = u.id
                  )
                GROUP BY u.telegram_user_id, ubs.locale, ubs.active_project_id, p.name
                HAVING COUNT(DISTINCT t.id) > 0
                """,
            )
            rows = result.fetchall()

        sent = 0
        for row in rows:
            try:
                locale = row.locale or "bn"
                project_name = row.project_name or "—"
                msg = (
                    f"🌅 *Good morning\\!*\n\n"
                    f"📌 {escape_md(project_name)}\n"
                    f"📋 {row.pending_tasks} pending tasks today\n\n"
                    + t("help.commands", locale)
                )
                await client.send_message(row.telegram_user_id, msg)
                sent += 1
            except Exception as exc:
                logger.warning("Daily digest send failed uid=%d: %s", row.telegram_user_id, exc)

        logger.info("Daily digest sent to %d users", sent)

    except Exception as exc:
        logger.exception("Daily digest job failed: %s", exc)
