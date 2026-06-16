from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal
from uuid import UUID

import redis.asyncio as aioredis
from pydantic import BaseModel, Field
from redis.exceptions import RedisError
from sqlalchemy import text

logger = logging.getLogger("ayzen.bot_state")

BotStateEnum = Literal[
    "IDLE", "PROJECT_SELECT", "TASK_LIST", "TASK_DETAIL",
    "SINGLE_SLOT_SELECT", "BATCH_SLOT_SELECT", "WIZARD_NEW_TASK",
    "WIZARD_NEW_SLOT", "WIZARD_BROADCAST", "SETTINGS", "HELP", "UNLINKED",
]


class BotState(BaseModel):
    state: BotStateEnum = "IDLE"
    project_id: UUID | None = None
    task_id: UUID | None = None
    page: int = 0
    batch_selected: list[UUID] = Field(default_factory=list)
    wizard_step: int = 0
    wizard_data: dict[str, Any] = Field(default_factory=dict)
    last_message_id: int | None = None
    locale: Literal["bn", "en"] = "bn"


class BotStateService:
    KEY_PATTERN = "ayzen:bot:{uid}:state"
    LOCK_PATTERN = "ayzen:bot:{uid}:lock"
    TTL_SECONDS = 7200  # 2 hours

    def __init__(self, redis: aioredis.Redis | None, db_session_factory: Any) -> None:
        self._redis = redis
        self._db = db_session_factory

    def _key(self, uid: int) -> str:
        return self.KEY_PATTERN.format(uid=uid)

    def _lock_key(self, uid: int) -> str:
        return self.LOCK_PATTERN.format(uid=uid)

    async def get(self, telegram_user_id: int) -> BotState:
        try:
            if self._redis:
                raw = await self._redis.get(self._key(telegram_user_id))
                if raw:
                    return BotState.model_validate_json(raw)
        except RedisError as exc:
            logger.warning("Redis GET failed for uid=%d: %s", telegram_user_id, exc)
            return await self._fallback_from_db(telegram_user_id)

        return await self._fallback_from_db(telegram_user_id)

    async def _fallback_from_db(self, telegram_user_id: int) -> BotState:
        try:
            async with self._db() as session:
                result = await session.execute(
                    text("SELECT active_project_id, locale FROM user_bot_state WHERE telegram_user_id = :uid"),
                    {"uid": telegram_user_id},
                )
                row = result.fetchone()
                if row:
                    return BotState(
                        state="IDLE",
                        project_id=row.active_project_id,
                        locale=row.locale or "bn",
                    )
        except Exception as exc:
            logger.error("DB fallback failed for uid=%d: %s", telegram_user_id, exc)
        return BotState(state="UNLINKED")

    async def set(self, telegram_user_id: int, state: BotState) -> None:
        try:
            if self._redis:
                await self._redis.set(
                    self._key(telegram_user_id),
                    state.model_dump_json(),
                    ex=self.TTL_SECONDS,
                )
            asyncio.create_task(self._persist_to_db(telegram_user_id, state))
        except RedisError as exc:
            logger.warning("Redis SET failed uid=%d: %s — falling back to DB only", telegram_user_id, exc)
            await self._persist_to_db(telegram_user_id, state)

    async def clear(self, telegram_user_id: int) -> None:
        try:
            if self._redis:
                await self._redis.delete(self._key(telegram_user_id))
        except RedisError:
            pass

    async def transition(self, telegram_user_id: int, new_state: BotStateEnum, **updates: Any) -> BotState:
        lock_key = self._lock_key(telegram_user_id)
        acquired = False
        try:
            if self._redis:
                acquired = bool(await self._redis.set(lock_key, "1", nx=True, ex=5))
        except RedisError:
            pass

        try:
            current = await self.get(telegram_user_id)
            current.state = new_state
            for k, v in updates.items():
                if hasattr(current, k):
                    setattr(current, k, v)
            await self.set(telegram_user_id, current)
            return current
        finally:
            if acquired and self._redis:
                try:
                    await self._redis.delete(lock_key)
                except RedisError:
                    pass

    async def is_stateless_mode(self) -> bool:
        if not self._redis:
            return True
        try:
            await self._redis.ping()
            return False
        except RedisError:
            return True

    async def _persist_to_db(self, telegram_user_id: int, state: BotState) -> None:
        try:
            async with self._db() as session:
                await session.execute(
                    text("""
                    INSERT INTO user_bot_state (telegram_user_id, active_project_id, locale, last_seen_at)
                    VALUES (:uid, :pid, :locale, NOW())
                    ON CONFLICT (telegram_user_id) DO UPDATE SET
                        active_project_id = EXCLUDED.active_project_id,
                        locale = EXCLUDED.locale,
                        last_seen_at = NOW()
                    """),
                    {
                        "uid": telegram_user_id,
                        "pid": str(state.project_id) if state.project_id else None,
                        "locale": state.locale,
                    },
                )
                await session.commit()
        except Exception as exc:
            logger.warning("DB persist failed uid=%d: %s", telegram_user_id, exc)
