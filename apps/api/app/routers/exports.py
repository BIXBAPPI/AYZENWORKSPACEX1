# ID: AX81      |  Local: A58Y1         |  Module: X62 (M61)
# Functions: A58Y1F1 A58Y1F2 A58Y1F3
# Processes: XN01 XN02 XN03
from __future__ import annotations

import csv
import io
import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = logging.getLogger("ayzen.routers.exports")

router = APIRouter()


async def _auth(request: Request):
    from apps.api.app.middleware.auth import verify_token
    return await verify_token(request)


@router.get("/completions/{project_id}")
async def export_completions_csv(project_id: UUID, request: Request) -> StreamingResponse:
    """A58Y1F1: Export task completions as CSV."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{user.tenant_id}'")
        result = await session.execute(
            """
            SELECT
                u.email, u.full_name,
                t.title as task_title, t.task_type,
                asl.slot_name, asl.twitter_username, asl.discord_username, asl.wallet_address,
                tc.completed_at, tc.submitted_via, tc.points_earned
            FROM task_completions tc
            JOIN users u ON u.id = tc.user_id
            JOIN tasks t ON t.id = tc.task_id
            JOIN account_slots asl ON asl.id = tc.account_slot_id
            WHERE t.project_id = :pid
            ORDER BY tc.completed_at DESC
            """,
            {"pid": str(project_id)},
        )
        rows = result.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Email", "Full Name", "Task", "Type", "Slot",
        "Twitter", "Discord", "Wallet", "Completed At", "Via", "Points",
    ])
    for r in rows:
        writer.writerow([
            r.email, r.full_name, r.task_title, r.task_type,
            r.slot_name, r.twitter_username, r.discord_username, r.wallet_address,
            r.completed_at.isoformat() if r.completed_at else "",
            r.submitted_via, r.points_earned,
        ])

    output.seek(0)
    filename = f"completions_{project_id}_{date.today()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/members/{project_id}")
async def export_members_csv(project_id: UUID, request: Request) -> StreamingResponse:
    """A58Y1F2: Export member list as CSV."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{user.tenant_id}'")
        result = await session.execute(
            """
            SELECT u.email, u.full_name, pm.role, pm.assigned_at,
                   COUNT(tc.id) as completion_count,
                   COALESCE(SUM(tc.points_earned), 0) as total_points
            FROM project_members pm
            JOIN users u ON u.id = pm.user_id
            LEFT JOIN task_completions tc ON tc.user_id = u.id
            WHERE pm.project_id = :pid
            GROUP BY u.email, u.full_name, pm.role, pm.assigned_at
            ORDER BY total_points DESC
            """,
            {"pid": str(project_id)},
        )
        rows = result.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Email", "Full Name", "Role", "Assigned At", "Completions", "Total Points"])
    for r in rows:
        writer.writerow([
            r.email, r.full_name, r.role,
            r.assigned_at.isoformat() if r.assigned_at else "",
            r.completion_count, int(r.total_points),
        ])

    output.seek(0)
    filename = f"members_{project_id}_{date.today()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/slots/{project_id}")
async def export_slots_csv(project_id: UUID, request: Request) -> StreamingResponse:
    """A58Y1F3: Export account slots as CSV."""
    user = await _auth(request)
    db = request.app.state.db

    async with db() as session:
        await session.execute(f"SET LOCAL app.current_tenant = '{user.tenant_id}'")
        result = await session.execute(
            """
            SELECT u.email, asl.slot_name, asl.twitter_username, asl.discord_username, asl.wallet_address
            FROM account_slots asl
            JOIN users u ON u.id = asl.user_id
            WHERE asl.project_id = :pid
            ORDER BY u.email, asl.slot_name
            """,
            {"pid": str(project_id)},
        )
        rows = result.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Email", "Slot", "Twitter", "Discord", "Wallet"])
    for r in rows:
        writer.writerow([r.email, r.slot_name, r.twitter_username, r.discord_username, r.wallet_address])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="slots_{project_id}_{date.today()}.csv"'},
    )
