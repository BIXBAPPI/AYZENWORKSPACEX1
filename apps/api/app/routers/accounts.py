from __future__ import annotations

import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.accounts")
router = APIRouter()


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


class CategoryCreate(BaseModel):
    name: str
    color: str = "#6366f1"
    icon: str = "key"


class AccountCreate(BaseModel):
    category_id: UUID
    label: str
    username: str = ""
    email: str = ""
    password: str
    recovery_email: str = ""
    recovery_phone: str = ""
    recovery_codes: str = ""
    notes: str = ""
    url: str = ""


class AccountUpdate(BaseModel):
    label: str | None = None
    username: str | None = None
    email: str | None = None
    password: str | None = None
    recovery_email: str | None = None
    recovery_phone: str | None = None
    recovery_codes: str | None = None
    notes: str | None = None
    url: str | None = None


async def _ensure_tables(session) -> None:
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS account_categories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            user_id UUID NOT NULL,
            name TEXT NOT NULL,
            color TEXT NOT NULL DEFAULT '#6366f1',
            icon TEXT NOT NULL DEFAULT 'key',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS account_vault (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            user_id UUID NOT NULL,
            category_id UUID NOT NULL REFERENCES account_categories(id) ON DELETE CASCADE,
            label TEXT NOT NULL,
            username TEXT NOT NULL DEFAULT '',
            email TEXT NOT NULL DEFAULT '',
            password_enc TEXT NOT NULL,
            recovery_email TEXT NOT NULL DEFAULT '',
            recovery_phone TEXT NOT NULL DEFAULT '',
            recovery_codes TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    await session.commit()


@router.get("/categories")
async def list_categories(request: Request) -> list[dict]:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        result = await session.execute(
            text("""
                SELECT c.id, c.name, c.color, c.icon, c.created_at,
                    COUNT(a.id) AS account_count
                FROM account_categories c
                LEFT JOIN account_vault a ON a.category_id = c.id
                WHERE c.tenant_id = :tid AND c.user_id = :uid
                GROUP BY c.id ORDER BY c.created_at ASC
            """),
            {"tid": str(user.tenant_id), "uid": str(user.user_id)},
        )
        return [
            {"id": str(r.id), "name": r.name, "color": r.color, "icon": r.icon,
             "account_count": r.account_count or 0,
             "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in result.fetchall()
        ]


@router.post("/categories", status_code=201)
async def create_category(body: CategoryCreate, request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        result = await session.execute(
            text("""
                INSERT INTO account_categories (id, tenant_id, user_id, name, color, icon)
                VALUES (:id, :tid, :uid, :name, :color, :icon)
                RETURNING id, name, color, icon, created_at
            """),
            {"id": str(uuid4()), "tid": str(user.tenant_id), "uid": str(user.user_id),
             "name": body.name, "color": body.color, "icon": body.icon},
        )
        row = result.fetchone()
        await session.commit()
        return {"id": str(row.id), "name": row.name, "color": row.color, "icon": row.icon,
                "account_count": 0, "created_at": row.created_at.isoformat() if row.created_at else None}


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(category_id: UUID, request: Request):
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        await session.execute(
            text("DELETE FROM account_categories WHERE id = :id AND tenant_id = :tid AND user_id = :uid"),
            {"id": str(category_id), "tid": str(user.tenant_id), "uid": str(user.user_id)},
        )
        await session.commit()


@router.get("/")
async def list_accounts(request: Request, category_id: str | None = None) -> list[dict]:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        filters = "WHERE a.tenant_id = :tid AND a.user_id = :uid"
        params: dict = {"tid": str(user.tenant_id), "uid": str(user.user_id)}
        if category_id:
            filters += " AND a.category_id = :cid"
            params["cid"] = category_id
        result = await session.execute(
            text(f"""
                SELECT a.id, a.category_id, c.name AS category_name, c.color AS category_color,
                    a.label, a.username, a.email, a.password_enc,
                    a.recovery_email, a.recovery_phone, a.recovery_codes,
                    a.notes, a.url, a.created_at, a.updated_at
                FROM account_vault a
                JOIN account_categories c ON c.id = a.category_id
                {filters}
                ORDER BY c.name, a.label
            """),
            params,
        )
        return [
            {
                "id": str(r.id), "category_id": str(r.category_id),
                "category_name": r.category_name, "category_color": r.category_color,
                "label": r.label, "username": r.username, "email": r.email,
                "password": r.password_enc,
                "recovery_email": r.recovery_email, "recovery_phone": r.recovery_phone,
                "recovery_codes": r.recovery_codes, "notes": r.notes, "url": r.url,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in result.fetchall()
        ]


@router.post("/", status_code=201)
async def create_account(body: AccountCreate, request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        cat = await session.execute(
            text("SELECT id FROM account_categories WHERE id = :id AND tenant_id = :tid AND user_id = :uid"),
            {"id": str(body.category_id), "tid": str(user.tenant_id), "uid": str(user.user_id)},
        )
        if not cat.fetchone():
            raise HTTPException(status_code=404, detail="category_not_found")

        result = await session.execute(
            text("""
                INSERT INTO account_vault
                    (id, tenant_id, user_id, category_id, label, username, email, password_enc,
                     recovery_email, recovery_phone, recovery_codes, notes, url)
                VALUES
                    (:id, :tid, :uid, :cid, :label, :username, :email, :password,
                     :recovery_email, :recovery_phone, :recovery_codes, :notes, :url)
                RETURNING id, label, created_at
            """),
            {
                "id": str(uuid4()), "tid": str(user.tenant_id), "uid": str(user.user_id),
                "cid": str(body.category_id), "label": body.label,
                "username": body.username, "email": body.email, "password": body.password,
                "recovery_email": body.recovery_email, "recovery_phone": body.recovery_phone,
                "recovery_codes": body.recovery_codes, "notes": body.notes, "url": body.url,
            },
        )
        row = result.fetchone()
        await session.commit()
        return {"id": str(row.id), "label": row.label, "created_at": row.created_at.isoformat() if row.created_at else None}


@router.patch("/{account_id}")
async def update_account(account_id: UUID, body: AccountUpdate, request: Request) -> dict:
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        sets = []
        params: dict = {"id": str(account_id), "tid": str(user.tenant_id), "uid": str(user.user_id)}
        field_map = {
            "label": "label", "username": "username", "email": "email",
            "password": "password_enc", "recovery_email": "recovery_email",
            "recovery_phone": "recovery_phone", "recovery_codes": "recovery_codes",
            "notes": "notes", "url": "url",
        }
        for field, col in field_map.items():
            val = getattr(body, field)
            if val is not None:
                sets.append(f"{col} = :{field}")
                params[field] = val
        if not sets:
            raise HTTPException(status_code=400, detail="no_fields_to_update")
        sets.append("updated_at = NOW()")
        result = await session.execute(
            text(f"UPDATE account_vault SET {', '.join(sets)} WHERE id = :id AND tenant_id = :tid AND user_id = :uid RETURNING id, label"),
            params,
        )
        row = result.fetchone()
        await session.commit()
        if not row:
            raise HTTPException(status_code=404, detail="account_not_found")
        return {"id": str(row.id), "label": row.label}


@router.delete("/{account_id}", status_code=204)
async def delete_account(account_id: UUID, request: Request):
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        await session.execute(
            text("DELETE FROM account_vault WHERE id = :id AND tenant_id = :tid AND user_id = :uid"),
            {"id": str(account_id), "tid": str(user.tenant_id), "uid": str(user.user_id)},
        )
        await session.commit()
