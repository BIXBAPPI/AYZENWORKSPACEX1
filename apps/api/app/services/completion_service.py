# ID: AX37      |  Local: A20Y1         |  Module: X21 (M20)
# Functions: A20Y1F1 A20Y1F2 A20Y1F3 A20Y1F4
# Processes: XN01 XN02 XN03 XN04
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger("ayzen.completion")


class CompletionResult:
    __slots__ = ("success", "duplicate", "points_earned", "error")

    def __init__(self, success: bool, duplicate: bool = False, points_earned: int = 0, error: str | None = None) -> None:
        self.success = success
        self.duplicate = duplicate
        self.points_earned = points_earned
        self.error = error


class CompletionService:
    """Handles task completion submissions — single and batch."""

    def __init__(self, db_session_factory: Any) -> None:
        self._db = db_session_factory

    # XN01  Submit Single
    async def submit_single(
        self,
        task_id: UUID,
        slot_id: UUID,
        user_id: UUID,
        tenant_id: UUID,
    ) -> CompletionResult:
        """
        INSERT into task_completions (UNIQUE constraint on task_id, slot_id).
        Returns CompletionResult: success, duplicate (409), or error.
        """
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")

            # Verify slot belongs to user
            slot_check = await session.execute(
                "SELECT id FROM account_slots WHERE id = :sid AND user_id = :uid",
                {"sid": str(slot_id), "uid": str(user_id)},
            )
            if not slot_check.fetchone():
                return CompletionResult(success=False, error="slot_not_owned")

            # Get task points
            task_result = await session.execute(
                "SELECT points_per_account FROM tasks WHERE id = :tid",
                {"tid": str(task_id)},
            )
            task_row = task_result.fetchone()
            if not task_row:
                return CompletionResult(success=False, error="task_not_found")
            points = task_row.points_per_account

            try:
                await session.execute(
                    """
                    INSERT INTO task_completions
                        (task_id, account_slot_id, user_id, submitted_via, points_earned)
                    VALUES (:tid, :sid, :uid, 'bot', :pts)
                    """,
                    {"tid": str(task_id), "sid": str(slot_id), "uid": str(user_id), "pts": points},
                )
                await session.commit()
                return CompletionResult(success=True, points_earned=points)
            except Exception as exc:
                await session.rollback()
                if "unique" in str(exc).lower() or "duplicate" in str(exc).lower():
                    return CompletionResult(success=False, duplicate=True)
                logger.error("submit_single error: %s", exc)
                return CompletionResult(success=False, error=str(exc))

    # XN02  Submit Batch
    async def submit_batch(
        self,
        task_id: UUID,
        slot_ids: list[UUID],
        user_id: UUID,
        tenant_id: UUID,
    ) -> dict:
        """
        Submit multiple slots atomically.
        Returns {success: int, duplicate: int, error: int, total_points: int}.
        Validates ALL slot_ids belong to user before any insert.
        """
        if not slot_ids:
            return {"success": 0, "duplicate": 0, "error": 0, "total_points": 0}

        result = {"success": 0, "duplicate": 0, "error": 0, "total_points": 0}

        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")

            # Validate all slots belong to user
            slot_ids_str = [str(s) for s in slot_ids]
            check_result = await session.execute(
                "SELECT id FROM account_slots WHERE id = ANY(:sids) AND user_id = :uid",
                {"sids": slot_ids_str, "uid": str(user_id)},
            )
            valid_slot_ids = {str(r.id) for r in check_result.fetchall()}
            invalid_count = len(slot_ids) - len(valid_slot_ids)
            result["error"] += invalid_count

            # Get task points
            task_result = await session.execute(
                "SELECT points_per_account FROM tasks WHERE id = :tid",
                {"tid": str(task_id)},
            )
            task_row = task_result.fetchone()
            points = task_row.points_per_account if task_row else 0

            for slot_id_str in slot_ids_str:
                if slot_id_str not in valid_slot_ids:
                    continue
                try:
                    await session.execute(
                        """
                        INSERT INTO task_completions
                            (task_id, account_slot_id, user_id, submitted_via, points_earned)
                        VALUES (:tid, :sid, :uid, 'bot_batch', :pts)
                        """,
                        {"tid": str(task_id), "sid": slot_id_str, "uid": str(user_id), "pts": points},
                    )
                    result["success"] += 1
                    result["total_points"] += points
                except Exception as exc:
                    if "unique" in str(exc).lower():
                        result["duplicate"] += 1
                    else:
                        result["error"] += 1

            await session.commit()
        return result

    # XN03  Get User's Submitted Slots
    async def get_submitted_slot_ids(self, task_id: UUID, user_id: UUID, tenant_id: UUID) -> list[str]:
        """Returns slot_ids already submitted by user for this task."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                "SELECT account_slot_id FROM task_completions WHERE task_id = :tid AND user_id = :uid",
                {"tid": str(task_id), "uid": str(user_id)},
            )
            return [str(r.account_slot_id) for r in result.fetchall()]

    # XN04  Get User's Slots for Project
    async def get_user_slots(self, user_id: UUID, project_id: UUID, tenant_id: UUID) -> list[dict]:
        """Returns all account slots for user in project."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            result = await session.execute(
                """
                SELECT id, slot_name, twitter_username, discord_username, wallet_address
                FROM account_slots
                WHERE user_id = :uid AND project_id = :pid
                ORDER BY slot_name
                """,
                {"uid": str(user_id), "pid": str(project_id)},
            )
            return [dict(r._mapping) for r in result.fetchall()]
