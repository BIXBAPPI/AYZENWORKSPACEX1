# ID: AX55      |  Local: A36Y1         |  Module: X38 (M37)
# Functions: A36Y1F1 A36Y1F2
# Processes: XN01 XN02
from __future__ import annotations

import logging

logger = logging.getLogger("ayzen.jobs.stale_user")


async def run() -> None:
    """
    A36Y1F1: APScheduler cron job — runs daily at 03:00 UTC.
    Cleans up stale wizard drafts and expired bot idempotency records.
    """
    try:
        from apps.api.main import session_factory
    except ImportError:
        return

    if not session_factory:
        return

    try:
        async with session_factory() as session:
            # Clean expired wizard drafts
            result = await session.execute(
                "DELETE FROM bot_wizard_drafts WHERE expires_at < NOW() RETURNING id",
            )
            draft_count = len(result.fetchall())

            # Clean expired idempotency records (backup to pg_cron)
            result2 = await session.execute(
                "DELETE FROM bot_idempotency WHERE processed_at < NOW() - INTERVAL '10 minutes' RETURNING callback_id",
            )
            idempotency_count = len(result2.fetchall())

            # Clean old audit log entries older than 90 days
            await session.execute(
                "DELETE FROM bot_audit_log WHERE created_at < NOW() - INTERVAL '90 days'",
            )

            await session.commit()
            logger.info(
                "Stale cleanup: drafts=%d idempotency=%d",
                draft_count, idempotency_count,
            )
    except Exception as exc:
        logger.exception("Stale user job failed: %s", exc)
