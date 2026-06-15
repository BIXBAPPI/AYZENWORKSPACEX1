# ID: AX53      |  Local: A34Y1         |  Module: X36 (M35)
# Functions: A34Y1F1 A34Y1F2 A34Y1F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging
import secrets
from typing import Any
from uuid import UUID

logger = logging.getLogger("ayzen.owner_transfer")

_TRANSFER_CODE_TTL = 600  # 10 minutes
_TRANSFER_KEY_PREFIX = "ayzen:transfer:"


class OwnerTransferService:
    """Handles secure project ownership transfer flow."""

    def __init__(self, redis: Any | None, db_session_factory: Any) -> None:
        self._redis = redis
        self._db = db_session_factory

    async def initiate_transfer(
        self, project_id: UUID, current_owner_id: UUID, new_owner_email: str, tenant_id: UUID
    ) -> str:
        """A34Y1F1: Initiate ownership transfer. Generates a confirmation token."""
        async with self._db() as session:
            await session.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")

            # Verify current owner
            owner_check = await session.execute(
                "SELECT role FROM project_members WHERE project_id = :pid AND user_id = :uid",
                {"pid": str(project_id), "uid": str(current_owner_id)},
            )
            row = owner_check.fetchone()
            if not row or row.role != "owner":
                raise ValueError("Only project owner can transfer ownership")

            # Find new owner by email
            new_owner_result = await session.execute(
                "SELECT id FROM users WHERE email = :email AND tenant_id = :tid",
                {"email": new_owner_email, "tid": str(tenant_id)},
            )
            new_owner_row = new_owner_result.fetchone()
            if not new_owner_row:
                raise ValueError("New owner not found in this tenant")
            new_owner_id = new_owner_row.id

        # Generate confirmation token
        token = secrets.token_urlsafe(16)
        key = f"{_TRANSFER_KEY_PREFIX}{token}"
        import json
        payload = json.dumps({
            "project_id": str(project_id),
            "current_owner_id": str(current_owner_id),
            "new_owner_id": str(new_owner_id),
        })

        if self._redis:
            await self._redis.set(key, payload, ex=_TRANSFER_CODE_TTL)

        logger.info("Owner transfer initiated: project=%s new_owner=%s", project_id, new_owner_email)
        return token

    async def confirm_transfer(self, token: str) -> bool:
        """A34Y1F2: Confirm and execute ownership transfer."""
        key = f"{_TRANSFER_KEY_PREFIX}{token}"
        if not self._redis:
            return False

        import json
        raw = await self._redis.get(key)
        if not raw:
            return False

        data = json.loads(raw)
        await self._redis.delete(key)

        project_id = data["project_id"]
        current_owner_id = data["current_owner_id"]
        new_owner_id = data["new_owner_id"]

        async with self._db() as session:
            # Demote current owner to manager
            await session.execute(
                "UPDATE project_members SET role = 'manager' WHERE project_id = :pid AND user_id = :uid",
                {"pid": project_id, "uid": current_owner_id},
            )
            # Promote new owner
            await session.execute(
                """
                INSERT INTO project_members (project_id, user_id, role)
                VALUES (:pid, :uid, 'owner')
                ON CONFLICT (project_id, user_id) DO UPDATE SET role = 'owner'
                """,
                {"pid": project_id, "uid": new_owner_id},
            )
            # Also update projects.created_by as informal reference
            await session.execute(
                "UPDATE projects SET updated_at = NOW() WHERE id = :pid",
                {"pid": project_id},
            )
            await session.commit()

        logger.info("Owner transfer completed: project=%s new_owner=%s", project_id, new_owner_id)
        return True

    async def cancel_transfer(self, token: str) -> None:
        """A34Y1F3: Cancel a pending transfer."""
        if self._redis:
            await self._redis.delete(f"{_TRANSFER_KEY_PREFIX}{token}")
