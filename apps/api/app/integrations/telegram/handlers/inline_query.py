# ID: AX65      |  Local: A42Y1         |  Module: X46 (M45)
# Functions: A42Y1F1 A42Y1F2
# Processes: XN01 XN02
from __future__ import annotations

import logging

logger = logging.getLogger("ayzen.handlers.inline_query")


async def inline_query_handler(update: dict, ctx: dict) -> None:
    """
    A42Y1F1: Handle inline queries for task quick-lookup.
    Allows users to search tasks inline from any chat.
    """
    inline_query = update.get("inline_query", {})
    if not inline_query:
        return

    query_id = inline_query.get("id")
    query_text = inline_query.get("query", "").strip()
    telegram_user_id = ctx.get("telegram_user_id")
    app = ctx.get("app")

    if not query_id or not telegram_user_id:
        return

    db = app.state.db if app else None
    redis = app.state.redis if app else None
    client = ctx["client"]

    results = []

    if query_text and len(query_text) >= 2:
        try:
            from apps.api.app.services.bot_context_service import BotContextService
            bot_ctx = await BotContextService(redis, db).resolve(telegram_user_id)

            if bot_ctx and bot_ctx.get("project_id"):
                async with db() as session:
                    await session.execute(f"SET LOCAL app.current_tenant = '{bot_ctx['tenant_id']}'")
                    result = await session.execute(
                        """
                        SELECT id, title, task_type, points_per_account
                        FROM tasks
                        WHERE project_id = :pid
                          AND archived_at IS NULL
                          AND title ILIKE :q
                        LIMIT 10
                        """,
                        {"pid": str(bot_ctx["project_id"]), "q": f"%{query_text}%"},
                    )
                    tasks = result.fetchall()

                    for task in tasks:
                        results.append({
                            "type": "article",
                            "id": str(task.id),
                            "title": task.title,
                            "description": f"{task.task_type} · {task.points_per_account} pts",
                            "input_message_content": {
                                "message_text": f"/task {task.id}",
                            },
                        })
        except Exception as exc:
            logger.warning("Inline query error: %s", exc)

    # Answer inline query (even empty — required within 10s)
    await client._request("answerInlineQuery", {
        "inline_query_id": query_id,
        "results": results,
        "cache_time": 30,
    })
