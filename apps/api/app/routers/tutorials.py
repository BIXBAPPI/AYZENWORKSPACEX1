"""Tutorial system — CRUD, slides, progress, feedback."""
from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger("ayzen.routers.tutorials")
router = APIRouter()


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


async def _admin(request: Request):
    user = await _auth(request)
    if user.role not in ("owner", "manager", "admin"):
        raise HTTPException(status_code=403, detail="admin_required")
    return user


async def _ensure_tables(session) -> None:
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS tutorials (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            project_id UUID,
            slides JSONB NOT NULL DEFAULT '[]',
            difficulty TEXT NOT NULL DEFAULT 'beginner',
            estimated_time INTEGER NOT NULL DEFAULT 10,
            tags TEXT[] NOT NULL DEFAULT '{}',
            published BOOLEAN NOT NULL DEFAULT false,
            created_by UUID NOT NULL,
            view_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS tutorial_progress (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            tutorial_id UUID NOT NULL REFERENCES tutorials(id) ON DELETE CASCADE,
            completed BOOLEAN NOT NULL DEFAULT false,
            bookmarked BOOLEAN NOT NULL DEFAULT false,
            last_slide INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, tutorial_id)
        )
    """))
    await session.execute(text("""
        CREATE TABLE IF NOT EXISTS tutorial_feedback (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            tutorial_id UUID NOT NULL REFERENCES tutorials(id) ON DELETE CASCADE,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            comment TEXT NOT NULL DEFAULT '',
            admin_reply TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    await session.commit()


class SlideItem(BaseModel):
    id: str | None = None
    title: str = ""
    content: str = ""
    image_url: str = ""
    code_snippet: str = ""
    order: int = 0
    type: str = "text"


class TutorialCreate(BaseModel):
    title: str
    description: str = ""
    difficulty: str = "beginner"
    estimated_time: int = 10
    tags: list[str] = []
    slides: list[SlideItem] = []


class TutorialUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    difficulty: str | None = None
    estimated_time: int | None = None
    tags: list[str] | None = None
    slides: list[SlideItem] | None = None
    published: bool | None = None


class FeedbackCreate(BaseModel):
    rating: int
    comment: str = ""


class FeedbackReply(BaseModel):
    reply: str


class ProgressUpdate(BaseModel):
    completed: bool | None = None
    bookmarked: bool | None = None
    last_slide: int | None = None


import json


def _row_to_tutorial(row) -> dict:
    slides = row.slides if isinstance(row.slides, list) else json.loads(row.slides or "[]")
    return {
        "id": str(row.id),
        "title": row.title,
        "description": row.description,
        "difficulty": row.difficulty,
        "estimated_time": row.estimated_time,
        "tags": list(row.tags or []),
        "published": row.published,
        "view_count": row.view_count,
        "slides": slides,
        "slide_count": len(slides),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("")
async def list_tutorials(request: Request, published_only: bool = True):
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        if user.role in ("owner", "manager", "admin") and not published_only:
            rows = await session.execute(text("""
                SELECT t.*, COALESCE(tp.completed, false) as user_completed,
                       COALESCE(tp.bookmarked, false) as user_bookmarked
                FROM tutorials t
                LEFT JOIN tutorial_progress tp ON tp.tutorial_id = t.id AND tp.user_id = :uid
                WHERE t.tenant_id = :tid ORDER BY t.created_at DESC
            """), {"tid": user.tenant_id, "uid": user.user_id})
        else:
            rows = await session.execute(text("""
                SELECT t.*, COALESCE(tp.completed, false) as user_completed,
                       COALESCE(tp.bookmarked, false) as user_bookmarked
                FROM tutorials t
                LEFT JOIN tutorial_progress tp ON tp.tutorial_id = t.id AND tp.user_id = :uid
                WHERE t.tenant_id = :tid AND t.published = true ORDER BY t.created_at DESC
            """), {"tid": user.tenant_id, "uid": user.user_id})
        items = rows.fetchall()
        result = []
        for row in items:
            t = _row_to_tutorial(row)
            t["user_completed"] = row.user_completed
            t["user_bookmarked"] = row.user_bookmarked
            result.append(t)
        return result


@router.get("/{tutorial_id}")
async def get_tutorial(tutorial_id: str, request: Request):
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        row = await session.execute(text("""
            SELECT t.*, COALESCE(tp.completed, false) as user_completed,
                   COALESCE(tp.bookmarked, false) as user_bookmarked,
                   COALESCE(tp.last_slide, 0) as user_last_slide
            FROM tutorials t
            LEFT JOIN tutorial_progress tp ON tp.tutorial_id = t.id AND tp.user_id = :uid
            WHERE t.id = :id AND t.tenant_id = :tid
        """), {"id": tutorial_id, "tid": user.tenant_id, "uid": user.user_id})
        tut = row.fetchone()
        if not tut:
            raise HTTPException(status_code=404, detail="not_found")
        if not tut.published and user.role not in ("owner", "manager", "admin"):
            raise HTTPException(status_code=403, detail="not_published")
        await session.execute(text(
            "UPDATE tutorials SET view_count = view_count + 1 WHERE id = :id"
        ), {"id": tutorial_id})
        await session.commit()
        result = _row_to_tutorial(tut)
        result["user_completed"] = tut.user_completed
        result["user_bookmarked"] = tut.user_bookmarked
        result["user_last_slide"] = tut.user_last_slide
        feedback_rows = await session.execute(text("""
            SELECT f.id, f.rating, f.comment, f.admin_reply, f.status, f.created_at,
                   u.full_name, u.email
            FROM tutorial_feedback f
            JOIN users u ON u.id = f.user_id
            WHERE f.tutorial_id = :id ORDER BY f.created_at DESC LIMIT 20
        """), {"id": tutorial_id})
        result["feedback"] = [
            {
                "id": str(r.id), "rating": r.rating, "comment": r.comment,
                "admin_reply": r.admin_reply, "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "user_name": r.full_name or r.email,
            } for r in feedback_rows.fetchall()
        ]
        return result


@router.post("", status_code=201)
async def create_tutorial(body: TutorialCreate, request: Request):
    user = await _admin(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        slides = [
            {**s.model_dump(), "id": s.id or str(uuid4()), "order": i}
            for i, s in enumerate(body.slides)
        ]
        row = await session.execute(text("""
            INSERT INTO tutorials (tenant_id, title, description, difficulty,
                estimated_time, tags, slides, created_by)
            VALUES (:tid, :title, :desc, :diff, :est, :tags, :slides::jsonb, :uid)
            RETURNING *
        """), {
            "tid": user.tenant_id, "title": body.title, "desc": body.description,
            "diff": body.difficulty, "est": body.estimated_time,
            "tags": body.tags, "slides": json.dumps(slides), "uid": user.user_id
        })
        await session.commit()
        return _row_to_tutorial(row.fetchone())


@router.put("/{tutorial_id}")
async def update_tutorial(tutorial_id: str, body: TutorialUpdate, request: Request):
    user = await _admin(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        sets = ["updated_at = NOW()"]
        params: dict = {"id": tutorial_id, "tid": user.tenant_id}
        if body.title is not None:
            sets.append("title = :title"); params["title"] = body.title
        if body.description is not None:
            sets.append("description = :desc"); params["desc"] = body.description
        if body.difficulty is not None:
            sets.append("difficulty = :diff"); params["diff"] = body.difficulty
        if body.estimated_time is not None:
            sets.append("estimated_time = :est"); params["est"] = body.estimated_time
        if body.tags is not None:
            sets.append("tags = :tags"); params["tags"] = body.tags
        if body.published is not None:
            sets.append("published = :pub"); params["pub"] = body.published
        if body.slides is not None:
            slides = [
                {**s.model_dump(), "id": s.id or str(uuid4()), "order": i}
                for i, s in enumerate(body.slides)
            ]
            sets.append("slides = :slides::jsonb")
            params["slides"] = json.dumps(slides)
        row = await session.execute(text(f"""
            UPDATE tutorials SET {', '.join(sets)}
            WHERE id = :id AND tenant_id = :tid RETURNING *
        """), params)
        await session.commit()
        tut = row.fetchone()
        if not tut:
            raise HTTPException(status_code=404, detail="not_found")
        return _row_to_tutorial(tut)


@router.delete("/{tutorial_id}", status_code=204)
async def delete_tutorial(tutorial_id: str, request: Request):
    user = await _admin(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        await session.execute(text(
            "DELETE FROM tutorials WHERE id = :id AND tenant_id = :tid"
        ), {"id": tutorial_id, "tid": user.tenant_id})
        await session.commit()


@router.put("/{tutorial_id}/progress")
async def update_progress(tutorial_id: str, body: ProgressUpdate, request: Request):
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        sets = ["updated_at = NOW()"]
        params: dict = {"uid": user.user_id, "tid": tutorial_id}
        if body.completed is not None:
            sets.append("completed = :completed"); params["completed"] = body.completed
        if body.bookmarked is not None:
            sets.append("bookmarked = :bookmarked"); params["bookmarked"] = body.bookmarked
        if body.last_slide is not None:
            sets.append("last_slide = :last_slide"); params["last_slide"] = body.last_slide
        await session.execute(text(f"""
            INSERT INTO tutorial_progress (user_id, tutorial_id)
            VALUES (:uid, :tid)
            ON CONFLICT (user_id, tutorial_id) DO UPDATE SET {', '.join(sets)}
        """), params)
        await session.commit()
        return {"ok": True}


@router.post("/{tutorial_id}/feedback", status_code=201)
async def submit_feedback(tutorial_id: str, body: FeedbackCreate, request: Request):
    user = await _auth(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        await session.execute(text("""
            INSERT INTO tutorial_feedback (user_id, tutorial_id, rating, comment)
            VALUES (:uid, :tid, :rating, :comment)
        """), {"uid": user.user_id, "tid": tutorial_id, "rating": body.rating, "comment": body.comment})
        await session.commit()
        return {"ok": True}


@router.get("/admin/feedback")
async def admin_list_feedback(request: Request):
    user = await _admin(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        rows = await session.execute(text("""
            SELECT f.id, f.rating, f.comment, f.admin_reply, f.status, f.created_at,
                   u.full_name, u.email, t.title as tutorial_title, f.tutorial_id
            FROM tutorial_feedback f
            JOIN users u ON u.id = f.user_id
            JOIN tutorials t ON t.id = f.tutorial_id
            WHERE t.tenant_id = :tid
            ORDER BY f.created_at DESC
        """), {"tid": user.tenant_id})
        return [
            {
                "id": str(r.id), "rating": r.rating, "comment": r.comment,
                "admin_reply": r.admin_reply, "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "user_name": r.full_name or r.email,
                "tutorial_title": r.tutorial_title,
                "tutorial_id": str(r.tutorial_id),
            } for r in rows.fetchall()
        ]


@router.post("/admin/feedback/{feedback_id}/reply")
async def reply_to_feedback(feedback_id: str, body: FeedbackReply, request: Request):
    user = await _admin(request)
    db = request.app.state.db
    async with db() as session:
        await _ensure_tables(session)
        await session.execute(text("""
            UPDATE tutorial_feedback SET admin_reply = :reply, status = 'resolved'
            WHERE id = :id
        """), {"id": feedback_id, "reply": body.reply})
        await session.commit()
        return {"ok": True}
