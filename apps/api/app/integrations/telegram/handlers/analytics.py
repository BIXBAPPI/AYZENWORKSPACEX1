# ID: AX40      |  Local: A20Y1         |  Module: X20 (M18)
# Functions: A20Y1F1 A20Y1F2 A20Y1F3 A20Y1F4
# Processes: XN01 XN03
from __future__ import annotations

import datetime
import logging

from apps.api.app.services.i18n_service import t
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards
from apps.api.app.integrations.telegram.keyboards.builders import KeyboardBuilders

logger = logging.getLogger("ayzen.handlers.analytics")

_PERIOD_DAYS = {"today": 1, "week": 7, "month": 30, "all_time": 3650}


def _fmt_bar(value: int, max_val: int, width: int = 10) -> str:
    """Render a simple text progress bar."""
    if max_val == 0:
        return "░" * width
    filled = round(value / max_val * width)
    return "█" * filled + "░" * (width - filled)


async def _fetch_stats(db, tenant_id: str, project_id: str, period: str) -> dict:
    """Query task_completions aggregates for the given period."""
    days = _PERIOD_DAYS.get(period, 7)
    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    try:
        async with db.acquire() as conn:
            await conn.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
            rows = await conn.fetch(
                """
                SELECT
                    COUNT(*)::int                          AS total_completions,
                    COALESCE(SUM(points_awarded), 0)::int AS total_points,
                    COUNT(DISTINCT user_id)::int           AS active_members,
                    COUNT(DISTINCT task_id)::int           AS unique_tasks
                FROM task_completions
                WHERE project_id = $1 AND completed_at >= $2
                """,
                project_id, since,
            )
            row = rows[0] if rows else {}
            # Daily breakdown (last 7 days max)
            daily = await conn.fetch(
                """
                SELECT DATE(completed_at) AS day, COUNT(*)::int AS cnt
                FROM task_completions
                WHERE project_id = $1 AND completed_at >= $2
                GROUP BY 1 ORDER BY 1
                """,
                project_id, since,
            )
            return {
                "total_completions": row.get("total_completions", 0),
                "total_points": row.get("total_points", 0),
                "active_members": row.get("active_members", 0),
                "unique_tasks": row.get("unique_tasks", 0),
                "daily": [{"day": str(r["day"]), "cnt": r["cnt"]} for r in daily],
            }
    except Exception as exc:
        logger.error("analytics fetch error: %s", exc)
        return {}


def _render_analytics(stats: dict, period: str, project_name: str, locale: str) -> str:
    """Render analytics message text."""
    tc   = stats.get("total_completions", 0)
    pts  = stats.get("total_points", 0)
    mem  = stats.get("active_members", 0)
    utsk = stats.get("unique_tasks", 0)
    daily: list[dict] = stats.get("daily", [])

    period_label = {
        "today": t("analytics_menu.today", locale),
        "week":  t("analytics_menu.week", locale),
        "month": t("analytics_menu.month", locale),
        "all_time": t("analytics_menu.all_time", locale),
    }.get(period, period)

    lines = [
        f"📊 *{t('analytics.header', locale)}*",
        f"📌 {project_name}  ·  {period_label}",
        "",
        f"✅ {t('analytics.completions', locale)}: *{tc}*",
        f"💰 {t('analytics.points', locale)}: *{pts}*",
        f"👥 {t('analytics.active_members', locale)}: *{mem}*",
        f"📋 {t('analytics.unique_tasks', locale)}: *{utsk}*",
    ]

    if daily and period in ("week", "month"):
        max_cnt = max((d["cnt"] for d in daily), default=1)
        lines.append("")
        lines.append(f"📅 *{t('analytics.daily_chart', locale)}*")
        for entry in daily[-7:]:
            day_str = entry["day"][-5:]  # MM-DD
            bar = _fmt_bar(entry["cnt"], max_cnt, width=8)
            lines.append(f"`{day_str}` {bar} {entry['cnt']}")

    return "\n".join(lines)


async def analytics_handler(update: dict, ctx: dict, period: str = "week") -> None:
    """A20Y1F1: Show analytics for the current project."""
    chat_id = ctx["chat_id"]
    client  = ctx["client"]
    locale  = ctx.get("locale", "bn")
    app     = ctx.get("app")
    db      = app.state.db if app else None
    redis   = app.state.redis if app else None
    tg_uid  = ctx["telegram_user_id"]

    bot_ctx = await BotContextService(redis, db).resolve(tg_uid)
    if not bot_ctx:
        await client.send_message(chat_id, t("error.not_linked", locale))
        return

    locale     = bot_ctx.get("locale", "bn")
    project_id = bot_ctx.get("active_project_id")
    if not project_id:
        await client.send_message(chat_id, t("error.no_project", locale))
        return

    tenant_id    = bot_ctx.get("tenant_id", "")
    project_name = bot_ctx.get("project_name", "—")

    stats = await _fetch_stats(db, tenant_id, project_id, period)
    text  = _render_analytics(stats, period, project_name, locale)
    kb    = InlineKeyboards.analytics_period_tabs(period, locale)

    await client.send_message(chat_id, text, reply_markup=kb, parse_mode="MarkdownV2")


async def analytics_today_handler(update: dict, ctx: dict) -> None:
    """A20Y1F2: Today's analytics."""
    await analytics_handler(update, ctx, period="today")


async def analytics_week_handler(update: dict, ctx: dict) -> None:
    """A20Y1F3: Weekly analytics."""
    await analytics_handler(update, ctx, period="week")


async def analytics_month_handler(update: dict, ctx: dict) -> None:
    """A20Y1F4: Monthly analytics."""
    await analytics_handler(update, ctx, period="month")


async def analytics_callback_handler(update: dict, ctx: dict) -> None:
    """Handle analytics:period:<p> and analytics:export:<p> callbacks."""
    cb      = ctx.get("callback_data", "")
    cq      = ctx.get("callback_query", {})
    client  = ctx["client"]
    chat_id = ctx["chat_id"]

    await client.answer_callback_query(cq.get("id", ""))

    parts = cb.split(":")
    if len(parts) < 3:
        return

    action = parts[1]

    if action == "period":
        period = parts[2] if len(parts) > 2 else "week"
        await analytics_handler(update, ctx, period=period)

    elif action == "export":
        period = parts[2] if len(parts) > 2 else "week"
        locale = ctx.get("locale", "bn")
        await client.send_message(chat_id, t("export.preparing", locale))
        # Delegate to export service (async, sends file when ready)
        from apps.api.app.services.export_service import ExportService
        app = ctx.get("app")
        db  = app.state.db if app else None
        bot_ctx = await BotContextService(app.state.redis if app else None, db).resolve(ctx["telegram_user_id"])
        if bot_ctx:
            svc = ExportService(db)
            await svc.export_analytics_csv(
                tenant_id=bot_ctx.get("tenant_id", ""),
                project_id=bot_ctx.get("active_project_id", ""),
                period=period,
                chat_id=chat_id,
                client=client,
                locale=locale,
            )

    elif action == "refresh":
        period = parts[2] if len(parts) > 2 else "week"
        await analytics_handler(update, ctx, period=period)
