"""Referral System — member submits referral, admin approves."""
from __future__ import annotations

import logging
import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.referrals")
router = APIRouter()


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


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


class ReferralRequest(BaseModel):
    referred_email: EmailStr
    referred_username: str | None = None


class RejectRequest(BaseModel):
    note: str | None = None


@router.post("/request")
async def submit_referral(body: ReferralRequest, request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        existing = await session.execute(
            text("""
                SELECT id FROM referral_requests
                WHERE referrer_id = :rid AND referred_email = :email AND status = 'pending'
            """),
            {"rid": str(user.user_id), "email": body.referred_email}
        )
        if existing.fetchone():
            raise HTTPException(400, "referral_already_pending")
        r = await session.execute(
            text("""
                INSERT INTO referral_requests (referrer_id, referred_email, referred_username)
                VALUES (:rid, :email, :uname) RETURNING id
            """),
            {"rid": str(user.user_id), "email": body.referred_email, "uname": body.referred_username}
        )
        row = r.fetchone()
        await session.commit()
        return {"id": str(row.id), "status": "pending"}


@router.get("/my")
async def my_referrals(request: Request) -> list[dict]:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("""
                SELECT rr.id, rr.referred_email, rr.referred_username, rr.status,
                       rr.admin_note, rr.created_at, rr.reviewed_at,
                       ac.code AS activation_code
                FROM referral_requests rr
                LEFT JOIN activation_codes ac ON ac.id = rr.activation_code_id
                WHERE rr.referrer_id = :uid
                ORDER BY rr.created_at DESC
            """),
            {"uid": str(user.user_id)}
        )
        rows = r.mappings().fetchall()
        return [
            {
                "id": str(row["id"]),
                "referred_email": row["referred_email"],
                "referred_username": row["referred_username"],
                "status": row["status"],
                "admin_note": row["admin_note"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "reviewed_at": row["reviewed_at"].isoformat() if row["reviewed_at"] else None,
                "activation_code": row["activation_code"],
            }
            for row in rows
        ]


@router.get("/pending")
async def pending_referrals(request: Request) -> list[dict]:
    user = await _admin(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("""
                SELECT rr.id, rr.referred_email, rr.referred_username, rr.status,
                       rr.created_at, u.email AS referrer_email, u.full_name AS referrer_name
                FROM referral_requests rr
                LEFT JOIN users u ON u.id = rr.referrer_id
                WHERE rr.status = 'pending'
                ORDER BY rr.created_at DESC
            """)
        )
        rows = r.mappings().fetchall()
        return [
            {
                "id": str(row["id"]),
                "referred_email": row["referred_email"],
                "referred_username": row["referred_username"],
                "status": row["status"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "referrer_email": row["referrer_email"],
                "referrer_name": row["referrer_name"],
            }
            for row in rows
        ]


@router.post("/{referral_id}/approve")
async def approve_referral(referral_id: str, request: Request) -> dict:
    user = await _admin(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("SELECT id, status, referred_email FROM referral_requests WHERE id = :id"),
            {"id": referral_id}
        )
        row = r.fetchone()
        if not row:
            raise HTTPException(404, "referral_not_found")
        if row.status != "pending":
            raise HTTPException(400, "referral_not_pending")

        code = _generate_code()
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        code_r = await session.execute(
            text("""
                INSERT INTO activation_codes (code, created_by, expires_at)
                VALUES (:code, :uid, :exp) RETURNING id
            """),
            {"code": code, "uid": str(user.user_id), "exp": expires}
        )
        code_id = code_r.fetchone().id
        await session.execute(
            text("""
                UPDATE referral_requests
                SET status = 'approved', reviewed_at = NOW(), reviewed_by = :uid,
                    activation_code_id = :cid
                WHERE id = :id
            """),
            {"uid": str(user.user_id), "cid": str(code_id), "id": referral_id}
        )
        await session.commit()
        return {"approved": True, "activation_code": code, "expires_at": expires.isoformat()}


@router.post("/{referral_id}/reject")
async def reject_referral(referral_id: str, body: RejectRequest, request: Request) -> dict:
    user = await _admin(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("SELECT id, status FROM referral_requests WHERE id = :id"),
            {"id": referral_id}
        )
        row = r.fetchone()
        if not row:
            raise HTTPException(404, "referral_not_found")
        if row.status != "pending":
            raise HTTPException(400, "referral_not_pending")
        await session.execute(
            text("""
                UPDATE referral_requests
                SET status = 'rejected', reviewed_at = NOW(), reviewed_by = :uid, admin_note = :note
                WHERE id = :id
            """),
            {"uid": str(user.user_id), "note": body.note, "id": referral_id}
        )
        await session.commit()
        return {"rejected": True}
