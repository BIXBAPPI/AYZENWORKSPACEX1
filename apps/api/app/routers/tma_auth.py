# ID: AX68      |  Local: A45Y1         |  Module: X49 (M48)
# Functions: A45Y1F1 A45Y1F2 A45Y1F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from urllib.parse import parse_qsl

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

logger = logging.getLogger("ayzen.routers.tma_auth")

router = APIRouter()

_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


class TmaInitDataRequest(BaseModel):
    init_data: str


def validate_telegram_init_data(init_data: str, bot_token: str) -> dict | None:
    """
    Validate Telegram Mini App init_data using HMAC-SHA256.
    Returns parsed user dict if valid, None if invalid.
    """
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", "")
        if not received_hash:
            return None

        # Sort and build data-check-string
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        # HMAC-SHA256 with secret key derived from "WebAppData" + bot_token
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(received_hash, expected_hash):
            return None

        # Parse user from JSON
        import json
        user_json = parsed.get("user", "{}")
        user = json.loads(user_json)
        return {"user": user, "parsed": parsed}

    except Exception as exc:
        logger.warning("TMA init_data validation error: %s", exc)
        return None


@router.post("/verify")
async def verify_tma(body: TmaInitDataRequest, request: Request, response: Response) -> dict:
    """
    A45Y1F1: Verify Telegram Mini App init_data and issue session cookie.
    Used by TMA web app on first load.
    """
    if not _BOT_TOKEN:
        raise HTTPException(status_code=500, detail="bot_not_configured")

    validated = validate_telegram_init_data(body.init_data, _BOT_TOKEN)
    if not validated:
        raise HTTPException(status_code=401, detail="invalid_init_data")

    tg_user = validated["user"]
    telegram_user_id = tg_user.get("id")
    if not telegram_user_id:
        raise HTTPException(status_code=400, detail="no_user_id")

    # Look up linked web user
    db = request.app.state.db
    async with db() as session:
        result = await session.execute(
            """
            SELECT u.id, u.email, u.full_name, u.tenant_id, u.role,
                   COALESCE(ubs.locale, 'bn') as locale
            FROM users u
            LEFT JOIN user_bot_state ubs ON ubs.user_id = u.id
            WHERE u.telegram_user_id = :tid
            """,
            {"tid": telegram_user_id},
        )
        row = result.fetchone()

    if not row:
        return {
            "status": "not_linked",
            "telegram_user_id": telegram_user_id,
            "first_name": tg_user.get("first_name"),
        }

    # Set TMA session cookie (short-lived, 1 hour)
    import jwt as pyjwt
    import time
    tma_token = pyjwt.encode(
        {
            "sub": str(row.id),
            "telegram_user_id": telegram_user_id,
            "tenant_id": str(row.tenant_id),
            "role": row.role,
            "exp": int(time.time()) + 3600,
        },
        os.environ.get("SESSION_SECRET", ""),
        algorithm="HS256",
    )
    response.set_cookie("tma-token", tma_token, httponly=True, secure=True, samesite="strict", max_age=3600)

    return {
        "status": "linked",
        "user_id": str(row.id),
        "full_name": row.full_name,
        "locale": row.locale,
        "role": row.role,
    }


@router.get("/me")
async def tma_me(request: Request) -> dict:
    """A45Y1F2: Get current TMA user info from token."""
    import jwt as pyjwt
    token = request.cookies.get("tma-token")
    if not token:
        raise HTTPException(status_code=401, detail="not_authenticated")

    try:
        payload = pyjwt.decode(
            token,
            os.environ.get("SESSION_SECRET", ""),
            algorithms=["HS256"],
        )
        return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token_expired")
    except Exception:
        raise HTTPException(status_code=401, detail="invalid_token")


@router.post("/logout")
async def tma_logout(response: Response) -> dict:
    """A45Y1F3: Clear TMA session."""
    response.delete_cookie("tma-token")
    return {"status": "logged_out"}
