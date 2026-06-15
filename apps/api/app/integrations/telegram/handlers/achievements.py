# ID: AX41      |  Local: A21Y1         |  Module: X21 (M18)
# Functions: A21Y1F1 A21Y1F2 A21Y1F3 A21Y1F4
# Processes: XN01 XN03
from __future__ import annotations

import logging

from apps.api.app.services.i18n_service import t
from apps.api.app.services.bot_context_service import BotContextService
from apps.api.app.services.rewards_service import RewardsService
from apps.api.app.integrations.telegram.keyboards.builders import KeyboardBuilders
from apps.api.app.integrations.telegram.keyboards.inline import InlineKeyboards

logger = logging.getLogger("ayzen.handlers.achievements")

# ── Badge metadata (server-side catalogue) ──────────────────────────────────
BADGE_CATALOGUE = [
    {"id": "first_task",     "name": "🥇 First Step",        "target": 1,   "unit": "completions"},
    {"id": "ten_tasks",      "name": "🔟 Task Master",        "target": 10,  "unit": "completions"},
    {"id": "fifty_tasks",    "name": "⚡ Power User",         "target": 50,  "unit": "completions"},
    {"id": "streak_3",       "name": "🔥 3-Day Streak",       "target": 3,   "unit": "streak_days"},
    {"id": "streak_7",       "name": "🔥🔥 Week Warrior",     "target": 7,   "unit": "streak_days"},
    {"id": "streak_30",      "name": "🏆 Monthly Legend",     "target": 30,  "unit": "streak_days"},
    {"id": "twitter_5",      "name": "🐦 Twitter Flyer",      "target": 5,   "unit": "twitter_tasks"},
    {"id": "discord_5",      "name": "💬 Discord Regular",    "target": 5,   "unit": "discord_tasks"},
    {"id": "onchain_3",      "name": "🔗 Chain Connector",    "target": 3,   "unit": "onchain_tasks"},
    {"id": "referral_1",     "name": "🤝 Recruiter",          "target": 1,   "unit": "referrals"},
    {"id": "referral_5",     "name": "🌟 Top Recruiter",      "target": 5,   "unit": "referrals"},
    {"id": "points_100",     "name": "💰 Century",            "target": 100, "unit": "points"},
    {"id": "points_1000",    "name": "💎 Diamond Earner",     "target": 1000,"unit": "points"},
]


async def _build_badge_state(db, tenant_id: str, user_id: str, project_id: str) -> list[dict]:
    """Attach progress and achieved flag to each badge in catalogue."""
    try:
        async with db.acquire() as conn:
            await conn.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")

            total = await conn.fetchval(
                "SELECT COUNT(*) FROM task_completions WHERE user_id=$1 AND project_id=$2",
                user_id, project_id,
            ) or 0
            points = await conn.fetchval(
                "SELECT COALESCE(SUM(points_awarded),0) FROM task_completions WHERE user_id=$1 AND project_id=$2",
                user_id, project_id,
            ) or 0
            # streak from user_settings
            streak = await conn.fetchval(
                "SELECT current_streak FROM user_settings WHERE user_id=$1", user_id,
            ) or 0
            by_type = await conn.fetch(
                "SELECT task_type, COUNT(*) AS cnt FROM task_completions tc "
                "JOIN tasks t ON t.id=tc.task_id "
                "WHERE tc.user_id=$1 AND tc.project_id=$2 GROUP BY 1",
                user_id, project_id,
            )
            type_counts = {r["task_type"]: r["cnt"] for r in by_type}
            referrals = await conn.fetchval(
                "SELECT COUNT(*) FROM referrals WHERE referrer_id=$1", user_id,
            ) or 0
    except Exception as exc:
        logger.error("badge state fetch error: %s", exc)
        return []

    progress_map = {
        "completions":   int(total),
        "streak_days":   int(streak),
        "twitter_tasks": int(type_counts.get("twitter", 0)),
        "discord_tasks": int(type_counts.get("discord", 0)),
        "onchain_tasks": int(type_counts.get("onchain", 0)),
        "referrals":     int(referrals),
        "points":        int(points),
    }

    result = []
    for badge in BADGE_CATALOGUE:
        prog = progress_map.get(badge["unit"], 0)
        result.append({
            **badge,
            "progress": prog,
            "achieved": prog >= badge["target"],
        })
    return result


async def achievements_handler(update: dict, ctx: dict) -> None:
    """A21Y1F1: Show badge gallery."""
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
    user_id    = bot_ctx.get("user_id", "")
    tenant_id  = bot_ctx.get("tenant_id", "")
    project_id = bot_ctx.get("active_project_id", "")

    if not project_id:
        await client.send_message(chat_id, t("error.no_project", locale))
        return

    badges  = await _build_badge_state(db, tenant_id, user_id, project_id)
    earned  = sum(1 for b in badges if b["achieved"])
    total   = len(badges)

    lines = [
        f"🏅 *{t('achievements.header', locale)}*",
        "",
        f"✅ {t('achievements.earned', locale)}: *{earned}/{total}*",
        "",
    ]
    for b in badges:
        if b["achieved"]:
            lines.append(f"✅ {b['name']}")
        else:
            pct = min(int(b["progress"] / max(b["target"], 1) * 100), 99)
            lines.append(f"🔒 {b['name']} ·  {b['progress']}/{b['target']}  ({pct}%)")

    kb = KeyboardBuilders.badge_list(badges, locale)
    await client.send_message(chat_id, "\n".join(lines), reply_markup=kb, parse_mode="MarkdownV2")


async def badge_callback_handler(update: dict, ctx: dict) -> None:
    """A21Y1F2: badge:detail:<id> and badge:share:<id>."""
    cb     = ctx.get("callback_data", "")
    cq     = ctx.get("callback_query", {})
    client = ctx["client"]
    chat_id = ctx["chat_id"]
    locale  = ctx.get("locale", "bn")

    await client.answer_callback_query(cq.get("id", ""))
    parts = cb.split(":")
    if len(parts) < 3:
        return
    action   = parts[1]
    badge_id = parts[2]

    badge = next((b for b in BADGE_CATALOGUE if b["id"] == badge_id), None)
    if not badge:
        return

    if action == "detail":
        text = (
            f"🏅 *{badge['name']}*\n\n"
            f"{t('achievements.target', locale)}: {badge['target']} {badge['unit']}"
        )
        kb = InlineKeyboards.badge_detail(badge_id, locale)
        await client.send_message(chat_id, text, reply_markup=kb, parse_mode="MarkdownV2")

    elif action == "share":
        share_text = t("achievements.share_text", locale, badge_name=badge["name"])
        await client.send_message(chat_id, share_text)


async def streak_handler(update: dict, ctx: dict) -> None:
    """A21Y1F3: Show streak info."""
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

    locale  = bot_ctx.get("locale", "bn")
    user_id = bot_ctx.get("user_id", "")

    streak = 0
    best   = 0
    try:
        async with db.acquire() as conn:
            await conn.execute(f"SET LOCAL app.current_tenant = '{bot_ctx.get('tenant_id', '')}'")
            row = await conn.fetchrow(
                "SELECT current_streak, best_streak FROM user_settings WHERE user_id=$1", user_id,
            )
            if row:
                streak = row["current_streak"] or 0
                best   = row["best_streak"] or 0
    except Exception as exc:
        logger.error("streak fetch error: %s", exc)

    bar = "🔥" * min(streak, 10)
    text = (
        f"🔥 *{t('streak.header', locale)}*\n\n"
        f"{t('streak.current', locale)}: *{streak}* {bar}\n"
        f"{t('streak.best', locale)}: *{best}*"
    )
    kb = InlineKeyboards.from_rows([InlineKeyboards.back_menu_row(locale)])
    await client.send_message(chat_id, text, reply_markup=kb, parse_mode="MarkdownV2")


async def milestones_handler(update: dict, ctx: dict) -> None:
    """A21Y1F4: Show milestone list."""
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

    badges = await _build_badge_state(db, tenant_id, user_id, project_id)
    milestone_badges = [b for b in badges if b["unit"] in ("completions", "points")]

    text = f"🎯 *{t('milestones.header', locale)}*\n"
    kb   = InlineKeyboards.milestones_list(milestone_badges, locale)
    await client.send_message(chat_id, text, reply_markup=kb, parse_mode="MarkdownV2")
