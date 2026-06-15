# ID: AX61      |  Local: A38Y1         |  Module: X42 (M41)
# Functions: A38Y1F1 A38Y1F2 A38Y1F3 A38Y1F4
# Processes: XN01 XN02 XN03 XN04
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

logger = logging.getLogger("ayzen.onboarding")


class OnboardingService:
    """Guides new users through onboarding checklist."""

    STEPS = ["create_project", "create_task", "add_member", "link_bot", "complete"]

    def __init__(self, db_session_factory: Any) -> None:
        self._db = db_session_factory

    async def get_status(self, user_id: UUID, tenant_id: UUID) -> dict:
        """A38Y1F1: Check which onboarding steps are complete."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")

            has_project = bool((await session.execute(
                "SELECT 1 FROM projects WHERE tenant_id = :tid LIMIT 1", {"tid": str(tenant_id)}
            )).fetchone())

            has_task = bool((await session.execute(
                "SELECT 1 FROM tasks t JOIN projects p ON p.id = t.project_id WHERE p.tenant_id = :tid LIMIT 1",
                {"tid": str(tenant_id)}
            )).fetchone())

            has_member = bool((await session.execute(
                """SELECT 1 FROM project_members pm
                   JOIN projects p ON p.id = pm.project_id
                   WHERE p.tenant_id = :tid AND pm.user_id != :uid LIMIT 1""",
                {"tid": str(tenant_id), "uid": str(user_id)}
            )).fetchone())

            has_bot = bool((await session.execute(
                "SELECT 1 FROM users WHERE id = :uid AND telegram_user_id IS NOT NULL",
                {"uid": str(user_id)}
            )).fetchone())

        steps = {
            "create_project": has_project,
            "create_task": has_task,
            "add_member": has_member,
            "link_bot": has_bot,
        }
        completed_count = sum(1 for v in steps.values() if v)
        is_complete = completed_count == len(steps)

        return {
            "steps": steps,
            "completed_count": completed_count,
            "total_steps": len(steps),
            "is_complete": is_complete,
            "next_step": next((k for k, v in steps.items() if not v), "complete"),
        }

    async def get_current_step(self, user_id: UUID, tenant_id: UUID) -> str:
        """A38Y1F2: Get next incomplete onboarding step."""
        status = await self.get_status(user_id, tenant_id)
        return status["next_step"]

    async def mark_complete(self, user_id: UUID) -> None:
        """A38Y1F3: Mark onboarding as complete in user record."""
        async with self._db() as session:
            await session.execute(
                "UPDATE users SET onboarding_completed = true WHERE id = :uid",
                {"uid": str(user_id)},
            )
            await session.commit()

    async def is_complete(self, user_id: UUID, tenant_id: UUID) -> bool:
        """A38Y1F4: Quick check if onboarding is done."""
        status = await self.get_status(user_id, tenant_id)
        return status["is_complete"]
