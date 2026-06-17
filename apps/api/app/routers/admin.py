"""Admin Panel API — user management, system stats, audit."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.admin")
router = APIRouter()


async def _admin(request: Request):
    from apps.api.app.middleware.auth import verify_token, require_admin
    user = await verify_token(request)
    await require_admin(user)
    return user


class UpdateUserRequest(BaseModel):
    role: str | None = None
    email_verified: bool | None = None
    xp_transferable: bool | None = None
    global_xp: int | None = None


class BroadcastRequest(BaseModel):
    message: str
    user_ids: list[str] | None = None  # None = all


# ── Users ──────────────────────────────────────────────────────────────────


@router.get("/users")
async def list_users(request: Request, q: str = "", page: int = 1, limit: int = 50) -> dict:
    admin = await _admin(request)
    db = request.app.state.db
    offset = (page - 1) * limit
    search = f"%{q}%"
    async with db() as session:
        r = await session.execute(
            text("""
                SELECT u.id, u.email, u.full_name, u.username, u.role,
                       u.global_xp, u.global_streak, u.email_verified,
                       u.two_fa_enabled, u.telegram_user_id, u.telegram_handle,
                       u.twitter_handle, u.discord_handle, u.created_at, u.last_active_date,
                       u.activation_code_used, u.wallet_address, u.avatar_url,
                       (SELECT COUNT(*) FROM tasks t WHERE t.assignee_id = u.id AND t.status = 'completed') AS tasks_done
                FROM users u
                WHERE u.tenant_id = :tid
                  AND (:q = '' OR u.email ILIKE :search OR u.full_name ILIKE :search OR u.username ILIKE :search)
                ORDER BY u.global_xp DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """),
            {"tid": str(admin.tenant_id), "q": q, "search": search, "limit": limit, "offset": offset}
        )
        rows = r.mappings().fetchall()

        count_r = await session.execute(
            text("""
                SELECT COUNT(*) FROM users u
                WHERE u.tenant_id = :tid
                  AND (:q = '' OR u.email ILIKE :search OR u.full_name ILIKE :search OR u.username ILIKE :search)
            """),
            {"tid": str(admin.tenant_id), "q": q, "search": search}
        )
        total = count_r.scalar() or 0

    return {
        "users": [
            {
                "id": str(row["id"]),
                "email": row["email"],
                "full_name": row["full_name"],
                "username": row["username"],
                "role": row["role"],
                "global_xp": row["global_xp"] or 0,
                "global_streak": row["global_streak"] or 0,
                "email_verified": row["email_verified"],
                "two_fa_enabled": row["two_fa_enabled"],
                "telegram_user_id": row["telegram_user_id"],
                "telegram_handle": row["telegram_handle"],
                "twitter_handle": row["twitter_handle"],
                "discord_handle": row["discord_handle"],
                "wallet_address": row["wallet_address"],
                "avatar_url": row["avatar_url"],
                "tasks_done": int(row["tasks_done"] or 0),
                "activation_code_used": row["activation_code_used"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "last_active_date": str(row["last_active_date"]) if row["last_active_date"] else None,
            }
            for row in rows
        ],
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
    }


@router.patch("/users/{user_id}")
async def update_user(user_id: str, body: UpdateUserRequest, request: Request) -> dict:
    admin = await _admin(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("SELECT id FROM users WHERE id = :id AND tenant_id = :tid"),
            {"id": user_id, "tid": str(admin.tenant_id)}
        )
        if not r.fetchone():
            raise HTTPException(404, "user_not_found")

        updates = {}
        if body.role is not None:
            if body.role not in ("owner", "manager", "member"):
                raise HTTPException(400, "invalid_role")
            updates["role"] = body.role
        if body.email_verified is not None:
            updates["email_verified"] = body.email_verified
        if body.xp_transferable is not None:
            updates["xp_transferable"] = body.xp_transferable
        if body.global_xp is not None:
            if body.global_xp < 0:
                raise HTTPException(400, "xp_must_be_non_negative")
            updates["global_xp"] = body.global_xp

        if not updates:
            raise HTTPException(400, "no_fields_to_update")

        set_clause = ", ".join(f"{k} = :{k}" for k in updates.keys())
        updates["id"] = user_id
        await session.execute(
            text(f"UPDATE users SET {set_clause}, updated_at = NOW() WHERE id = :id"),
            updates
        )
        await session.commit()
    return {"updated": True}


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, request: Request) -> dict:
    admin = await _admin(request)
    if str(admin.user_id) == user_id:
        raise HTTPException(400, "cannot_delete_self")
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("SELECT id, role FROM users WHERE id = :id AND tenant_id = :tid"),
            {"id": user_id, "tid": str(admin.tenant_id)}
        )
        row = r.fetchone()
        if not row:
            raise HTTPException(404, "user_not_found")
        if row.role == "owner" and admin.role != "owner":
            raise HTTPException(403, "cannot_delete_owner")
        await session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
        await session.commit()
    return {"deleted": True}


# ── System Stats ────────────────────────────────────────────────────────────


@router.get("/stats")
async def system_stats(request: Request) -> dict:
    admin = await _admin(request)
    db = request.app.state.db
    async with db() as session:
        stats = {}

        r = await session.execute(
            text("SELECT COUNT(*) FROM users WHERE tenant_id = :tid"), {"tid": str(admin.tenant_id)}
        )
        stats["total_users"] = r.scalar() or 0

        r = await session.execute(
            text("SELECT COUNT(*) FROM users WHERE tenant_id = :tid AND email_verified = TRUE"),
            {"tid": str(admin.tenant_id)}
        )
        stats["verified_users"] = r.scalar() or 0

        r = await session.execute(
            text("SELECT COUNT(*) FROM tasks WHERE tenant_id = :tid"), {"tid": str(admin.tenant_id)}
        )
        stats["total_tasks"] = r.scalar() or 0

        r = await session.execute(
            text("SELECT COUNT(*) FROM tasks WHERE tenant_id = :tid AND status = 'completed'"),
            {"tid": str(admin.tenant_id)}
        )
        stats["completed_tasks"] = r.scalar() or 0

        r = await session.execute(
            text("SELECT COUNT(*) FROM activation_codes WHERE created_by IN (SELECT id FROM users WHERE tenant_id = :tid) AND is_used = FALSE"),
            {"tid": str(admin.tenant_id)}
        )
        stats["unused_codes"] = r.scalar() or 0

        r = await session.execute(
            text("SELECT COUNT(*) FROM referral_requests rr JOIN users u ON u.id = rr.referrer_id WHERE u.tenant_id = :tid AND rr.status = 'pending'"),
            {"tid": str(admin.tenant_id)}
        )
        stats["pending_referrals"] = r.scalar() or 0

        # Error logs (last 24h) — separate try with rollback on failure
        try:
            r = await session.execute(
                text("SELECT COUNT(*) FROM error_logs WHERE timestamp > NOW() - INTERVAL '24 hours'")
            )
            stats["errors_24h"] = r.scalar() or 0
        except Exception:
            await session.rollback()
            stats["errors_24h"] = 0

        # XP total in tenant
        r = await session.execute(
            text("SELECT COALESCE(SUM(global_xp), 0) FROM users WHERE tenant_id = :tid"),
            {"tid": str(admin.tenant_id)}
        )
        stats["total_xp"] = r.scalar() or 0

        # Telegram linked users
        r = await session.execute(
            text("SELECT COUNT(*) FROM users WHERE tenant_id = :tid AND telegram_user_id IS NOT NULL"),
            {"tid": str(admin.tenant_id)}
        )
        stats["telegram_linked"] = r.scalar() or 0

    return stats


# ── Error Logs ──────────────────────────────────────────────────────────────


@router.get("/errors")
async def get_error_logs(request: Request, limit: int = 50) -> list[dict]:
    await _admin(request)
    db = request.app.state.db
    async with db() as session:
        try:
            r = await session.execute(
                text("""
                    SELECT id, level, message, function_name AS module, user_id, timestamp AS created_at, route
                    FROM error_logs
                    ORDER BY timestamp DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            )
            rows = r.mappings().fetchall()
            return [
                {
                    "id": str(row["id"]),
                    "level": row["level"],
                    "message": row["message"],
                    "module": row["module"],
                    "user_id": str(row["user_id"]) if row["user_id"] else None,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                }
                for row in rows
            ]
        except Exception:
            return []


# ── Telegram Link Code ──────────────────────────────────────────────────────


@router.get("/telegram-link-code/{user_id}")
async def get_telegram_link_code(user_id: str, request: Request) -> dict:
    """Admin: get or generate a Telegram link code for a user."""
    await _admin(request)
    db = request.app.state.db
    async with db() as session:
        r = await session.execute(
            text("SELECT id, email, pending_link_code, pending_link_expires FROM users WHERE id = :uid"),
            {"uid": user_id}
        )
        user = r.fetchone()
        if not user:
            raise HTTPException(404, "user_not_found")

        from datetime import datetime, timezone
        link_code = None
        if user.pending_link_code and user.pending_link_expires:
            if datetime.now(timezone.utc) < user.pending_link_expires.replace(tzinfo=timezone.utc):
                link_code = user.pending_link_code

        if not link_code:
            import secrets as secrets_lib
            link_code = secrets_lib.token_urlsafe(8)
            await session.execute(
                text("""
                    UPDATE users
                    SET pending_link_code = :code,
                        pending_link_expires = NOW() + INTERVAL '24 hours'
                    WHERE id = :uid
                """),
                {"uid": user_id, "code": link_code}
            )
            await session.commit()

        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        bot_username = ""
        if bot_token:
            try:
                import httpx
                r2 = httpx.get(f"https://api.telegram.org/bot{bot_token}/getMe")
                bot_username = r2.json().get("result", {}).get("username", "")
            except Exception:
                pass

        return {
            "link_code": link_code,
            "bot_url": f"https://t.me/{bot_username}?start={link_code}" if bot_username else None,
            "command": f"/link {link_code}",
        }
