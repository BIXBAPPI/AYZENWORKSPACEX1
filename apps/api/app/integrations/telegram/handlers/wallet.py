# ID: AX42      |  Local: A22Y1         |  Module: X22 (M18)
# Functions: A22Y1F1 A22Y1F2 A22Y1F3 A22Y1F4
# Processes: XN01 XN03
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.integrations.telegram.keyboards.builders import KeyboardBuilders
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.wallet")

HISTORY_PAGE_SIZE = 10


async def _fetch_wallet(db, tenant_id: str, user_id: str, project_id: str) -> dict:
    try:
        async with db.acquire() as conn:
            await conn.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            total = await conn.fetchval(
                "SELECT COALESCE(SUM(points_awarded),0) FROM task_completions "
                "WHERE user_id=$1 AND project_id=$2", user_id, project_id,
            ) or 0
            today = await conn.fetchval(
                "SELECT COALESCE(SUM(points_awarded),0) FROM task_completions "
                "WHERE user_id=$1 AND project_id=$2 AND completed_at >= CURRENT_DATE",
                user_id, project_id,
            ) or 0
            week = await conn.fetchval(
                "SELECT COALESCE(SUM(points_awarded),0) FROM task_completions "
                "WHERE user_id=$1 AND project_id=$2 AND completed_at >= NOW() - INTERVAL '7 days'",
                user_id, project_id,
            ) or 0
            rank = await conn.fetchval(
                """
                SELECT rank FROM (
                  SELECT user_id, RANK() OVER (ORDER BY SUM(points_awarded) DESC) AS rank
                  FROM task_completions WHERE project_id=$1 GROUP BY user_id
                ) r WHERE user_id=$2
                """,
                project_id, user_id,
            ) or "—"
            return {"total": int(total), "today": int(today), "week": int(week), "rank": rank}
    except Exception as exc:
        logger.error("wallet fetch error: %s", exc)
        return {"total": 0, "today": 0, "week": 0, "rank": "—"}


async def wallet_balance_handler(update: dict, ctx: dict) -> None:
    """A22Y1F1: Points balance overview."""
    chat_id = ctx["chat_id"]
    client  = ctx["client"]
    locale  = ctx.get("locale", "bn")
    app     = ctx.get("app")
    db      = app.state.db if app else None
    redis   = app.state.redis if app else None

    bot_ctx = await BotContextService(redis, db).resolve(ctx["telegram_user_id"])
    if not bot_ctx:
        await client.send_message(chat_id, t("error.not_linked", locale))
        return

    locale     = bot_ctx.get("locale", "bn")
    user_id    = bot_ctx.get("user_id", "")
    tenant_id  = bot_ctx.get("tenant_id", "")
    project_id = bot_ctx.get("active_project_id", "")

    if not project_id:
        await client.send_message(chat_id, t("error.no_project", locale))
        return

    w = await _fetch_wallet(db, tenant_id, user_id, project_id)

    text = (
        f"💰 *{t('wallet.header', locale)}*\n"
        f"📌 {bot_ctx.get('project_name', '—')}\n\n"
        f"💎 {t('wallet.total', locale)}: *{w['total']} pts*\n"
        f"📅 {t('wallet.today', locale)}: *{w['today']} pts*\n"
        f"📆 {t('wallet.week', locale)}: *{w['week']} pts*\n"
        f"🏆 {t('wallet.rank', locale)}: *\\#{w['rank']}*"
    )
    kb = InlineKeyboards.from_rows([
        [
            InlineKeyboards.button(t("points_menu.history", locale),   "points:history:0"),
            InlineKeyboards.button(t("points_menu.breakdown", locale),  "points:breakdown"),
        ],
        InlineKeyboards.back_menu_row(locale),
    ])
    await client.send_message(chat_id, text, reply_markup=kb, parse_mode="MarkdownV2")


async def wallet_history_handler(update: dict, ctx: dict, page: int = 0) -> None:
    """A22Y1F2: Paginated points transaction history."""
    chat_id = ctx["chat_id"]
    client  = ctx["client"]
    locale  = ctx.get("locale", "bn")
    app     = ctx.get("app")
    db      = app.state.db if app else None
    redis   = app.state.redis if app else None

    bot_ctx = await BotContextService(redis, db).resolve(ctx["telegram_user_id"])
    if not bot_ctx:
        await client.send_message(chat_id, t("error.not_linked", locale))
        return

    locale     = bot_ctx.get("locale", "bn")
    user_id    = bot_ctx.get("user_id", "")
    tenant_id  = bot_ctx.get("tenant_id", "")
    project_id = bot_ctx.get("active_project_id", "")

    offset   = page * HISTORY_PAGE_SIZE
    entries  = []
    has_more = False

    try:
        async with db.acquire() as conn:
            await conn.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            rows = await conn.fetch(
                """
                SELECT tc.id, tc.points_awarded, t.title, tc.completed_at
                FROM task_completions tc
                JOIN tasks t ON t.id = tc.task_id
                WHERE tc.user_id=$1 AND tc.project_id=$2
                ORDER BY tc.completed_at DESC
                LIMIT $3 OFFSET $4
                """,
                user_id, project_id, HISTORY_PAGE_SIZE + 1, offset,
            )
            has_more = len(rows) > HISTORY_PAGE_SIZE
            for r in rows[:HISTORY_PAGE_SIZE]:
                entries.append({
                    "id":     str(r["id"]),
                    "points": r["points_awarded"],
                    "reason": r["title"],
                    "date":   r["completed_at"].strftime("%m/%d") if r["completed_at"] else "",
                })
    except Exception as exc:
        logger.error("history fetch error: %s", exc)

    if not entries and page == 0:
        text = f"💰 *{t('wallet.history_header', locale)}*\n\n{t('progress.no_data', locale)}"
    else:
        lines = [f"💰 *{t('wallet.history_header', locale)}*\n"]
        for e in entries:
            lines.append(f"• +{e['points']} pts — {e['reason'][:30]}  `{e['date']}`")
        text = "\n".join(lines)

    kb = KeyboardBuilders.points_history(entries, page, has_more, locale)
    await client.send_message(chat_id, text, reply_markup=kb, parse_mode="MarkdownV2")


async def wallet_breakdown_handler(update: dict, ctx: dict) -> None:
    """A22Y1F3: Points breakdown by task type."""
    chat_id = ctx["chat_id"]
    client  = ctx["client"]
    locale  = ctx.get("locale", "bn")
    app     = ctx.get("app")
    db      = app.state.db if app else None
    redis   = app.state.redis if app else None

    bot_ctx = await BotContextService(redis, db).resolve(ctx["telegram_user_id"])
    if not bot_ctx:
        await client.send_message(chat_id, t("error.not_linked", locale))
        return

    locale     = bot_ctx.get("locale", "bn")
    user_id    = bot_ctx.get("user_id", "")
    tenant_id  = bot_ctx.get("tenant_id", "")
    project_id = bot_ctx.get("active_project_id", "")

    breakdown: list[dict] = []
    try:
        async with db.acquire() as conn:
            await conn.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            rows = await conn.fetch(
                """
                SELECT t.task_type, COUNT(*)::int AS cnt,
                       COALESCE(SUM(tc.points_awarded),0)::int AS pts
                FROM task_completions tc
                JOIN tasks t ON t.id = tc.task_id
                WHERE tc.user_id=$1 AND tc.project_id=$2
                GROUP BY 1 ORDER BY pts DESC
                """,
                user_id, project_id,
            )
            breakdown = [dict(r) for r in rows]
    except Exception as exc:
        logger.error("breakdown fetch error: %s", exc)

    TYPE_EMOJI = {"twitter": "🐦", "discord": "💬", "onchain": "🔗", "form": "📝", "other": "📋"}
    lines = [f"📊 *{t('wallet.breakdown_header', locale)}*\n"]
    for row in breakdown:
        emoji = TYPE_EMOJI.get(row["task_type"], "📋")
        lines.append(f"{emoji} {row['task_type']}: *{row['pts']} pts* ({row['cnt']} tasks)")

    if not breakdown:
        lines.append(t("progress.no_data", locale))

    kb = InlineKeyboards.from_rows([InlineKeyboards.back_menu_row(locale)])
    await client.send_message(chat_id, "\n".join(lines), reply_markup=kb, parse_mode="MarkdownV2")


async def wallet_callback_handler(update: dict, ctx: dict) -> None:
    """A22Y1F4: Handle points:* callbacks."""
    cb     = ctx.get("callback_data", "")
    cq     = ctx.get("callback_query", {})
    client = ctx["client"]
    await client.answer_callback_query(cq.get("id", ""))

    parts = cb.split(":")
    if len(parts) < 2:
        return
    action = parts[1]

    if action == "history":
        page = int(parts[2]) if len(parts) > 2 else 0
        await wallet_history_handler(update, ctx, page=page)
    elif action == "breakdown":
        await wallet_breakdown_handler(update, ctx)
    elif action == "balance":
        await wallet_balance_handler(update, ctx)
