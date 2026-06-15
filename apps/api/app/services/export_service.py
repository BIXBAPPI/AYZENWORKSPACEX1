# ID: AX70      |  Local: A47Y1         |  Module: X51 (M50)
# Functions: A47Y1F1 A47Y1F2 A47Y1F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import csv
import io
import logging
from datetime import date
from typing import Any
from uuid import UUID

logger = logging.getLogger("ayzen.export")


class ExportService:
    """Generates CSV exports for completions, members, and slots."""

    def __init__(self, db_session_factory: Any) -> None:
        self._db = db_session_factory

    async def export_completions(self, project_id: UUID, tenant_id: UUID) -> str:
        """A47Y1F1: Export task completions as CSV string."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT
                    u.email, u.full_name,
                    t.title as task_title, t.task_type,
                    asl.slot_name, asl.twitter_username, asl.discord_username, asl.wallet_address,
                    tc.completed_at, tc.submitted_via, tc.points_earned
                FROM task_completions tc
                JOIN users u ON u.id = tc.user_id
                JOIN tasks t ON t.id = tc.task_id
                JOIN account_slots asl ON asl.id = tc.account_slot_id
                WHERE t.project_id = :pid
                ORDER BY tc.completed_at DESC
                """,
                {"pid": str(project_id)},
            )
            rows = result.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Email", "Full Name", "Task", "Type",
            "Slot", "Twitter", "Discord", "Wallet",
            "Completed At", "Via", "Points",
        ])
        for r in rows:
            writer.writerow([
                r.email, r.full_name, r.task_title, r.task_type,
                r.slot_name, r.twitter_username, r.discord_username, r.wallet_address,
                r.completed_at.isoformat() if r.completed_at else "",
                r.submitted_via, r.points_earned,
            ])
        return output.getvalue()

    async def export_members(self, project_id: UUID, tenant_id: UUID) -> str:
        """A47Y1F2: Export members as CSV string."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT u.email, u.full_name, pm.role, pm.assigned_at,
                       COUNT(tc.id) as completion_count,
                       COALESCE(SUM(tc.points_earned), 0) as total_points
                FROM project_members pm
                JOIN users u ON u.id = pm.user_id
                LEFT JOIN task_completions tc ON tc.user_id = u.id
                WHERE pm.project_id = :pid
                GROUP BY u.email, u.full_name, pm.role, pm.assigned_at
                ORDER BY total_points DESC
                """,
                {"pid": str(project_id)},
            )
            rows = result.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Email", "Full Name", "Role", "Assigned At", "Completions", "Total Points"])
        for r in rows:
            writer.writerow([
                r.email, r.full_name, r.role,
                r.assigned_at.isoformat() if r.assigned_at else "",
                r.completion_count, int(r.total_points),
            ])
        return output.getvalue()

    async def export_slots(self, project_id: UUID, tenant_id: UUID) -> str:
        """A47Y1F3: Export account slots as CSV string."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT u.email, asl.slot_name,
                       asl.twitter_username, asl.discord_username, asl.wallet_address
                FROM account_slots asl
                JOIN users u ON u.id = asl.user_id
                WHERE asl.project_id = :pid
                ORDER BY u.email, asl.slot_name
                """,
                {"pid": str(project_id)},
            )
            rows = result.fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Email", "Slot", "Twitter", "Discord", "Wallet"])
        for r in rows:
            writer.writerow([r.email, r.slot_name, r.twitter_username, r.discord_username, r.wallet_address])
        return output.getvalue()
