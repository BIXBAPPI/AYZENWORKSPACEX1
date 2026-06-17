"""XP Wallet — balance, transfers, history, rank."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.wallet_xp")
router = APIRouter()


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


TIER_THRESHOLDS = [(20000, "Platinum"), (5000, "Gold"), (1000, "Silver"), (0, "Bronze")]

def _tier(xp: int) -> str:
    for threshold, name in TIER_THRESHOLDS:
        if xp >= threshold:
            return name
    return "Bronze"


class TransferRequest(BaseModel):
    to_username: str
    amount: int
    note: str | None = None


@router.get("/balance")
async def get_balance(request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("SELECT global_xp, xp_transferable FROM users WHERE id = :uid"),
            {"uid": str(user.user_id)}
        )
        row = r.fetchone()
        if not row:
            raise HTTPException(404, "user_not_found")
        xp = row.global_xp or 0
        return {
            "xp": xp,
            "xp_transferable": row.xp_transferable or 0,
            "tier": _tier(xp),
        }


@router.get("/rank")
async def get_rank(request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("""
                SELECT global_xp FROM users WHERE id = :uid
            """),
            {"uid": str(user.user_id)}
        )
        row = r.fetchone()
        xp = (row.global_xp or 0) if row else 0

        rank_r = await session.execute(
            text("""
                SELECT COUNT(*) + 1 AS rank
                FROM users
                WHERE global_xp > :xp AND tenant_id = (SELECT tenant_id FROM users WHERE id = :uid)
            """),
            {"xp": xp, "uid": str(user.user_id)}
        )
        rank_row = rank_r.fetchone()
        rank = rank_row.rank if rank_row else 1

        return {"xp": xp, "tier": _tier(xp), "rank": rank}


@router.get("/streak")
async def get_streak(request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("SELECT global_streak, last_active_date FROM users WHERE id = :uid"),
            {"uid": str(user.user_id)}
        )
        row = r.fetchone()
        return {
            "streak": (row.global_streak or 0) if row else 0,
            "last_active_date": str(row.last_active_date) if row and row.last_active_date else None,
        }


@router.get("/transactions")
async def get_transactions(request: Request) -> list[dict]:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("""
                SELECT xt.id, xt.amount, xt.note, xt.created_at,
                       CASE WHEN xt.from_user_id = :uid THEN 'sent' ELSE 'received' END AS type,
                       CASE WHEN xt.from_user_id = :uid
                            THEN tu.full_name ELSE fu.full_name END AS counterpart_name,
                       CASE WHEN xt.from_user_id = :uid
                            THEN tu.email ELSE fu.email END AS counterpart_email
                FROM xp_transfers xt
                LEFT JOIN users fu ON fu.id = xt.from_user_id
                LEFT JOIN users tu ON tu.id = xt.to_user_id
                WHERE xt.from_user_id = :uid OR xt.to_user_id = :uid
                ORDER BY xt.created_at DESC
                LIMIT 100
            """),
            {"uid": str(user.user_id)}
        )
        rows = r.mappings().fetchall()
        return [
            {
                "id": str(row["id"]),
                "amount": row["amount"],
                "note": row["note"],
                "type": row["type"],
                "counterpart": row["counterpart_name"] or row["counterpart_email"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }
            for row in rows
        ]


@router.post("/transfer")
async def transfer_xp(body: TransferRequest, request: Request) -> dict:
    user = await _auth(request)
    if body.amount <= 0:
        raise HTTPException(400, "amount_must_be_positive")
    db = request.app.state.db
    async with db() as session:
        # Check sender balance
        r = await session.execute(
            text("SELECT xp_transferable FROM users WHERE id = :uid"),
            {"uid": str(user.user_id)}
        )
        row = r.fetchone()
        if not row or (row.xp_transferable or 0) < body.amount:
            raise HTTPException(400, "insufficient_transferable_xp")

        # Find recipient
        r2 = await session.execute(
            text("""
                SELECT id FROM users
                WHERE username = :uname OR full_name = :uname OR email = :uname
                LIMIT 1
            """),
            {"uname": body.to_username}
        )
        to_row = r2.fetchone()
        if not to_row:
            raise HTTPException(404, "recipient_not_found")
        to_id = str(to_row.id)
        if to_id == str(user.user_id):
            raise HTTPException(400, "cannot_transfer_to_self")

        # Atomic transfer
        await session.execute(
            text("UPDATE users SET xp_transferable = xp_transferable - :amt WHERE id = :uid"),
            {"amt": body.amount, "uid": str(user.user_id)}
        )
        await session.execute(
            text("UPDATE users SET global_xp = global_xp + :amt, xp_transferable = xp_transferable + :amt WHERE id = :uid"),
            {"amt": body.amount, "uid": to_id}
        )
        await session.execute(
            text("""
                INSERT INTO xp_transfers (from_user_id, to_user_id, amount, note)
                VALUES (:fid, :tid, :amt, :note)
            """),
            {"fid": str(user.user_id), "tid": to_id, "amt": body.amount, "note": body.note}
        )
        await session.commit()
        return {"transferred": True, "amount": body.amount, "to": body.to_username}
