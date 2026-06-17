"""Subscription tiers and CoinGate payment integration."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.subscriptions")
router = APIRouter()

COINGATE_API_TOKEN = os.environ.get("COINGATE_API_TOKEN", "")
BASE_URL = os.environ.get("BASE_URL", "")

TIERS = {
    "free": {"name": "Free", "price": 0, "currency": "USD"},
    "pro": {"name": "Pro", "price": 3, "currency": "USD"},
    "elite": {"name": "Elite", "price": 9, "currency": "USD"},
}


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


async def _ensure_tables(session) -> None:
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            tenant_id UUID NOT NULL,
            tier TEXT NOT NULL DEFAULT 'free',
            amount DECIMAL,
            currency TEXT,
            coingate_order_id TEXT,
            coingate_payment_url TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            started_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    await session.commit()


class OrderRequest(BaseModel):
    tier: str


@router.get("/current")
async def get_current_subscription(request: Request):
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        row = await session.execute(text("""
            SELECT subscription_tier, subscription_expires_at FROM users WHERE id = :uid
        """), {"uid": user.user_id})
        u = row.fetchone()
        tier = u.subscription_tier if u else "free"
        expires_at = u.subscription_expires_at if u else None
        active_sub = await session.execute(text("""
            SELECT * FROM subscriptions
            WHERE user_id = :uid AND status = 'paid'
            ORDER BY created_at DESC LIMIT 1
        """), {"uid": user.user_id})
        sub = active_sub.fetchone()
        return {
            "tier": tier or "free",
            "expires_at": expires_at.isoformat() if expires_at else None,
            "is_active": expires_at is None or expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc),
            "subscription": {
                "id": str(sub.id), "tier": sub.tier, "status": sub.status,
                "started_at": sub.started_at.isoformat() if sub.started_at else None,
                "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
            } if sub else None,
        }


@router.post("/create-order")
async def create_order(body: OrderRequest, request: Request):
    user = await _auth(request)
    if body.tier not in ("pro", "elite"):
        raise HTTPException(status_code=400, detail="invalid_tier")

    tier_info = TIERS[body.tier]
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        import uuid
        order_ref = f"AYZEN-{str(user.user_id)[:8].upper()}-{uuid.uuid4().hex[:8].upper()}"

        if not COINGATE_API_TOKEN or not BASE_URL:
            sub_row = await session.execute(text("""
                INSERT INTO subscriptions (user_id, tenant_id, tier, amount, currency, status, coingate_order_id)
                VALUES (:uid, :tid, :tier, :amount, :currency, 'demo', :oid)
                RETURNING id
            """), {
                "uid": user.user_id, "tid": user.tenant_id,
                "tier": body.tier, "amount": tier_info["price"],
                "currency": tier_info["currency"], "oid": order_ref,
            })
            await session.commit()
            sub_id = sub_row.fetchone().id
            return {
                "demo_mode": True,
                "message": "Set COINGATE_API_TOKEN and BASE_URL to enable real payments",
                "order_id": order_ref,
                "subscription_id": str(sub_id),
                "tier": body.tier,
                "amount": tier_info["price"],
            }

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.coingate.com/v2/orders",
                    headers={
                        "Authorization": f"Token {COINGATE_API_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "order_id": order_ref,
                        "price_amount": tier_info["price"],
                        "price_currency": tier_info["currency"],
                        "receive_currency": "USDT",
                        "title": f"AYZEN {body.tier.upper()} Plan",
                        "callback_url": f"{BASE_URL}/api/v1/subscriptions/webhook/coingate",
                        "success_url": f"{BASE_URL}/dashboard?upgraded=true",
                        "cancel_url": f"{BASE_URL}/settings?tab=subscription",
                    },
                    timeout=15,
                )
                data = resp.json()

            payment_url = data.get("payment_url", "")
            sub_row = await session.execute(text("""
                INSERT INTO subscriptions (user_id, tenant_id, tier, amount, currency,
                    coingate_order_id, coingate_payment_url, status)
                VALUES (:uid, :tid, :tier, :amount, :currency, :oid, :purl, 'pending')
                RETURNING id
            """), {
                "uid": user.user_id, "tid": user.tenant_id,
                "tier": body.tier, "amount": tier_info["price"],
                "currency": tier_info["currency"], "oid": order_ref,
                "purl": payment_url,
            })
            await session.commit()
            sub_id = sub_row.fetchone().id
            return {
                "payment_url": payment_url,
                "order_id": order_ref,
                "subscription_id": str(sub_id),
                "coingate_response": data,
            }
        except Exception as e:
            logger.error(f"CoinGate error: {e}")
            raise HTTPException(status_code=502, detail=f"payment_gateway_error: {str(e)}")


@router.post("/webhook/coingate")
async def coingate_webhook(request: Request):
    data = await request.json()
    order_id = data.get("order_id", "")
    status = data.get("status", "")
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        if status == "paid":
            sub_row = await session.execute(text("""
                SELECT id, user_id, tier FROM subscriptions WHERE coingate_order_id = :oid
            """), {"oid": order_id})
            sub = sub_row.fetchone()
            if sub:
                now = datetime.now(timezone.utc)
                expires = now + timedelta(days=30)
                await session.execute(text("""
                    UPDATE subscriptions SET status = 'paid', started_at = :now, expires_at = :exp
                    WHERE id = :id
                """), {"id": sub.id, "now": now, "exp": expires})
                await session.execute(text("""
                    UPDATE users SET subscription_tier = :tier, subscription_expires_at = :exp
                    WHERE id = :uid
                """), {"tier": sub.tier, "exp": expires, "uid": sub.user_id})
                await session.commit()
    return {"ok": True}
