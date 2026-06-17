"""Activation Codes — admin-only management of invite codes."""
from __future__ import annotations

import logging
import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.activation")
router = APIRouter()


async def _admin(request: Request):
    from apps.api.app.middleware.auth import verify_token, require_admin
    user = await verify_token(request)
    await require_admin(user)
    return user


def _generate_code() -> str:
    chars = string.ascii_uppercase + string.digits
    part1 = "".join(random.choices(chars, k=4))
    part2 = "".join(random.choices(chars, k=4))
    return f"AYZEN-{part1}-{part2}"


class GenerateCodesRequest(BaseModel):
    count: int = 5
    expires_in_days: int | None = 30


@router.get("/")
async def list_codes(request: Request) -> list[dict]:
    user = await _admin(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("""
                SELECT ac.id, ac.code, ac.is_used, ac.created_at, ac.expires_at, ac.used_at,
                       u.email AS used_by_email
                FROM activation_codes ac
                LEFT JOIN users u ON u.id = ac.used_by
                WHERE ac.created_by IN (
                    SELECT id FROM users WHERE tenant_id = :tid
                )
                ORDER BY ac.created_at DESC
                LIMIT 200
            """),
            {"tid": str(user.tenant_id)}
        )
        rows = r.mappings().fetchall()
        return [
            {
                "id": str(row["id"]),
                "code": row["code"],
                "is_used": row["is_used"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
                "used_at": row["used_at"].isoformat() if row["used_at"] else None,
                "used_by_email": row["used_by_email"],
            }
            for row in rows
        ]


@router.post("/generate")
async def generate_codes(body: GenerateCodesRequest, request: Request) -> list[dict]:
    user = await _admin(request)
    if body.count < 1 or body.count > 50:
        raise HTTPException(400, "count must be 1–50")
    db = request.app.state.db
    expires = None
    if body.expires_in_days:
        expires = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)
    codes = []
    async with db() as session:
        for _ in range(body.count):
            code = _generate_code()
            await session.execute(
                text("""
                    INSERT INTO activation_codes (code, created_by, expires_at)
                    VALUES (:code, :cby, :exp)
                """),
                {"code": code, "cby": str(user.user_id), "exp": expires}
            )
            codes.append({"code": code, "expires_at": expires.isoformat() if expires else None})
        await session.commit()
    return codes


@router.delete("/{code_id}")
async def revoke_code(code_id: str, request: Request) -> dict:
    user = await _admin(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("SELECT id, is_used FROM activation_codes WHERE id = :id AND created_by = :uid"),
            {"id": code_id, "uid": str(user.user_id)}
        )
        row = r.fetchone()
        if not row:
            raise HTTPException(404, "code_not_found")
        if row.is_used:
            raise HTTPException(400, "code_already_used")
        await session.execute(
            text("DELETE FROM activation_codes WHERE id = :id"),
            {"id": code_id}
        )
        await session.commit()
        return {"deleted": True}
