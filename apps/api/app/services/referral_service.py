# ID: AX58      |  Local: A37Y3         |  Module: X41 (M40)
# Functions: A37Y3F1 A37Y3F2 A37Y3F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import logging
import os
import secrets
from typing import Any
from uuid import UUID

logger = logging.getLogger("ayzen.referral")

_BOT_USERNAME = os.environ.get("BOT_USERNAME", "AyzenBot")


class ReferralService:
    """Manages referral codes for new member recruitment."""

    def __init__(self, redis: Any | None, db_session_factory: Any) -> None:
        self._redis = redis
        self._db = db_session_factory

    async def generate_referral_code(self, user_id: UUID, project_id: UUID) -> str:
        """A37Y3F1: Generate referral link for user to share."""
        code = secrets.token_urlsafe(8)
        key = f"ayzen:referral:{code}"

        import json
        payload = json.dumps({"user_id": str(user_id), "project_id": str(project_id)})

        if self._redis:
            await self._redis.set(key, payload, ex=604800)  # 7 days

        return f"https://t.me/{_BOT_USERNAME}?start=ref_{code}"

    async def resolve_referral(self, code: str) -> dict | None:
        """A37Y3F2: Resolve referral code to referrer and project."""
        key = f"ayzen:referral:{code}"
        if not self._redis:
            return None
        try:
            import json
            raw = await self._redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return None

    async def record_referral(self, referrer_id: UUID, new_user_id: UUID, project_id: UUID) -> None:
        """A37Y3F3: Record successful referral in DB."""
        async with self._db() as session:
            try:
                await session.execute(
                    """
                    INSERT INTO referrals (referrer_id, referred_user_id, project_id)
                    VALUES (:rid, :nid, :pid)
                    ON CONFLICT DO NOTHING
                    """,
                    {"rid": str(referrer_id), "nid": str(new_user_id), "pid": str(project_id)},
                )
                await session.commit()
            except Exception as exc:
                logger.warning("Referral record failed: %s", exc)
