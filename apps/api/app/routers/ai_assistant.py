"""AI Assistant — Claude-powered chat with full member data context."""
from __future__ import annotations

import logging
import os

import anthropic
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.ai")
router = APIRouter()


async def _admin(request: Request):
    from apps.api.app.middleware.auth import verify_token, require_admin
    user = await verify_token(request)
    await require_admin(user)
    return user


class AskRequest(BaseModel):
    question: str
    context: str | None = None  # "vault" | "member" | None


async def _build_context(session, tenant_id: str) -> str:
    r = await session.execute(
        text("""
            SELECT u.id, u.email, u.full_name, u.username, u.role, u.global_xp,
                   u.global_streak, u.wallet_address, u.twitter_handle, u.discord_handle,
                   u.telegram_handle, u.github_handle, u.bio, u.two_fa_enabled,
                   u.created_at,
                   av.evm_address, av.solana_address, av.cosmos_address,
                   av.sui_address, av.aptos_address, av.btc_address,
                   av.twitter AS vault_twitter, av.discord AS vault_discord,
                   av.telegram AS vault_telegram, av.github AS vault_github,
                   av.totp_enabled
            FROM users u
            LEFT JOIN account_vault av ON av.user_id = u.id
            WHERE u.tenant_id = :tid
            ORDER BY u.global_xp DESC NULLS LAST
            LIMIT 200
        """),
        {"tid": tenant_id}
    )
    rows = r.mappings().fetchall()

    def _tier(xp: int) -> str:
        if xp >= 20000: return "Platinum"
        if xp >= 5000: return "Gold"
        if xp >= 1000: return "Silver"
        return "Bronze"

    lines = []
    for row in rows:
        xp = row.get("global_xp") or 0
        name = row.get("username") or row.get("full_name") or row.get("email", "").split("@")[0]
        parts = [
            f"User: {name}",
            f"Email: {row['email']}",
            f"Role: {row['role']}",
            f"XP: {xp} ({_tier(xp)})",
            f"Streak: {row.get('global_streak') or 0}",
        ]
        if row.get("wallet_address") or row.get("evm_address"):
            parts.append(f"EVM Wallet: {row.get('evm_address') or row.get('wallet_address')}")
        if row.get("solana_address"):
            parts.append(f"Solana: {row['solana_address']}")
        if row.get("btc_address"):
            parts.append(f"BTC: {row['btc_address']}")
        socials = []
        for platform, key in [("Twitter", "twitter_handle"), ("Discord", "discord_handle"),
                               ("Telegram", "telegram_handle"), ("GitHub", "github_handle")]:
            val = row.get(key) or row.get(f"vault_{platform.lower()}")
            if val:
                socials.append(f"{platform}: {val}")
        if socials:
            parts.append("Socials: " + ", ".join(socials))
        if row.get("bio"):
            parts.append(f"Bio: {row['bio']}")
        lines.append(" | ".join(parts))

    return "\n".join(lines)


@router.post("/ask")
async def ask(body: AskRequest, request: Request) -> dict:
    user = await _admin(request)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(503, "AI assistant not configured — ANTHROPIC_API_KEY missing")

    db = request.app.state.db
    async with db() as session:
        member_data = await _build_context(session, str(user.tenant_id))

    system_prompt = f"""You are AYZEN Assistant, an AI for the AYZEN WORKSPACE crypto community platform.
You have access to all member data. Answer questions about members, wallets, accounts, tasks, XP, tiers, and projects.
Be concise, precise, and helpful. Format tables in markdown when listing multiple members.
All data is confidential and only visible to admins.

MEMBER DATA:
{member_data}"""

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": body.question}],
            system=system_prompt,
        )
        answer = response.content[0].text
        return {"answer": answer, "model": "claude-sonnet-4-5"}
    except Exception as e:
        logger.error("AI request failed: %s", e)
        raise HTTPException(500, f"AI error: {str(e)}")
