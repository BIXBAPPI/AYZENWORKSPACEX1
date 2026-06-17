"""AI Assistant — Groq + OpenRouter powered chat with full member data context."""
from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.ai")
router = APIRouter()

GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
]

OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct",
    "openai/gpt-4o-mini",
    "anthropic/claude-3-haiku",
]


async def _admin(request: Request):
    from apps.api.app.middleware.auth import verify_token, require_admin
    user = await verify_token(request)
    await require_admin(user)
    return user


class AskRequest(BaseModel):
    question: str
    model: str | None = None  # optional model override


def _tier(xp: int) -> str:
    if xp >= 20000: return "Platinum 💎"
    if xp >= 5000: return "Gold 🥇"
    if xp >= 1000: return "Silver 🥈"
    return "Bronze 🥉"


async def _build_context(session, tenant_id: str) -> str:
    r = await session.execute(
        text("""
            SELECT u.id, u.email, u.full_name, u.username, u.role, u.global_xp,
                   u.global_streak, u.wallet_address, u.twitter_handle, u.discord_handle,
                   u.telegram_handle, u.github_handle, u.bio, u.two_fa_enabled,
                   u.created_at, u.last_active_date, u.email_verified,
                   av.evm_address, av.solana_address, av.cosmos_address,
                   av.sui_address, av.aptos_address, av.btc_address,
                   av.twitter AS vault_twitter, av.discord AS vault_discord,
                   av.telegram AS vault_telegram, av.github AS vault_github,
                   av.totp_enabled,
                   (SELECT COUNT(*) FROM tasks t WHERE t.assigned_to = u.id AND t.status = 'completed') AS tasks_done,
                   (SELECT COUNT(*) FROM tasks t WHERE t.assigned_to = u.id) AS tasks_total
            FROM users u
            LEFT JOIN account_vault av ON av.user_id = u.id
            WHERE u.tenant_id = :tid
            ORDER BY u.global_xp DESC NULLS LAST
            LIMIT 200
        """),
        {"tid": tenant_id}
    )
    rows = r.mappings().fetchall()
    lines = []
    for row in rows:
        xp = row.get("global_xp") or 0
        name = row.get("username") or row.get("full_name") or row.get("email", "").split("@")[0]
        parts = [
            f"User: {name} ({row['email']})",
            f"Role: {row['role']} | Tier: {_tier(xp)} | XP: {xp} | Streak: {row.get('global_streak') or 0}",
            f"Tasks: {row.get('tasks_done') or 0}/{row.get('tasks_total') or 0} completed",
        ]
        wallets = []
        for label, key in [("EVM", "evm_address"), ("SOL", "solana_address"), ("BTC", "btc_address"),
                            ("COSMOS", "cosmos_address"), ("SUI", "sui_address")]:
            val = row.get(key) or (key == "evm_address" and row.get("wallet_address"))
            if val:
                wallets.append(f"{label}:{val[:10]}…")
        if wallets:
            parts.append("Wallets: " + " ".join(wallets))
        socials = []
        for platform, key in [("𝕏", "twitter_handle"), ("Discord", "discord_handle"),
                               ("TG", "telegram_handle"), ("GH", "github_handle")]:
            val = row.get(key) or row.get(f"vault_{platform.lower()}")
            if val:
                socials.append(f"{platform}:{val}")
        if socials:
            parts.append(" ".join(socials))
        if row.get("bio"):
            parts.append(f"Bio: {row['bio'][:80]}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


async def _call_groq(question: str, system_prompt: str, model: str | None = None) -> dict:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")

    target_model = model if model in GROQ_MODELS else GROQ_MODELS[0]

    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=target_model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )
        return {
            "answer": response.choices[0].message.content,
            "model": f"groq/{target_model}",
            "provider": "groq",
        }
    except Exception as e:
        raise RuntimeError(f"Groq error: {e}") from e


async def _call_openrouter(question: str, system_prompt: str, model: str | None = None) -> dict:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not set")

    target_model = model if model in OPENROUTER_MODELS else OPENROUTER_MODELS[0]

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://ayzen.workspace",
                "X-Title": "AYZEN Workspace",
                "Content-Type": "application/json",
            },
            json={
                "model": target_model,
                "max_tokens": 2048,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data["choices"][0]["message"]["content"]
        return {
            "answer": answer,
            "model": f"openrouter/{target_model}",
            "provider": "openrouter",
        }


@router.post("/ask")
async def ask(body: AskRequest, request: Request) -> dict:
    user = await _admin(request)

    groq_key = os.environ.get("GROQ_API_KEY", "")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")

    if not groq_key and not openrouter_key:
        raise HTTPException(503, "AI assistant not configured — add GROQ_API_KEY or OPENROUTER_API_KEY in Secrets")

    db = request.app.state.db
    async with db() as session:
        member_data = await _build_context(session, str(user.tenant_id))

    system_prompt = f"""You are AYZEN Assistant — an elite AI for the AYZEN WORKSPACE Web3 community platform.
You have real-time access to all member data below. Answer questions about members, wallets, XP, tiers, streaks, tasks, and airdrop progress.
Be precise, concise, and helpful. Use markdown tables for multi-member queries.
Data is confidential — only visible to admins. Today: {__import__('datetime').date.today()}.

=== MEMBER DATA ({member_data.count(chr(10)) + 1} members) ===
{member_data}
=== END ==="""

    errors = []

    # Try Groq first
    if groq_key:
        try:
            return await _call_groq(body.question, system_prompt, body.model)
        except Exception as e:
            errors.append(f"Groq: {e}")
            logger.warning("Groq failed, trying OpenRouter: %s", e)

    # Fallback to OpenRouter
    if openrouter_key:
        try:
            return await _call_openrouter(body.question, system_prompt, body.model)
        except Exception as e:
            errors.append(f"OpenRouter: {e}")
            logger.error("OpenRouter also failed: %s", e)

    raise HTTPException(500, f"All AI providers failed: {'; '.join(errors)}")


@router.get("/models")
async def get_models(request: Request) -> dict:
    await _admin(request)
    return {
        "groq": {
            "available": bool(os.environ.get("GROQ_API_KEY")),
            "models": GROQ_MODELS,
        },
        "openrouter": {
            "available": bool(os.environ.get("OPENROUTER_API_KEY")),
            "models": OPENROUTER_MODELS,
        },
    }
