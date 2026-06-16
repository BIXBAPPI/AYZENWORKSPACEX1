---
name: Telegram bot fixes
description: Three bugs that prevented the Telegram bot from working in AYZEN
---

## Fixes applied

**1. Wrong webhook secret header**
Telegram sends `X-Telegram-Bot-Api-Secret-Token`, NOT `X-Internal-Webhook-Token`.
File: `apps/api/app/integrations/telegram/webhook.py`

**2. App context missing from dispatch**
`bot_router.dispatch(update)` → must be `bot_router.dispatch(update, app=request.app)`
And in `BotRouter._dispatch_inner`, add `"app": app` to the ctx dict.
All handlers do `app = ctx.get("app")` to access `app.state.db`.
Files: `webhook.py`, `router.py`

**3. Raw SQL without text() wrappers**
SQLAlchemy requires `text("SELECT ...")` for raw SQL strings.
Files: `apps/api/app/services/bot_state_service.py`, `apps/api/app/services/bot_user_service.py`

**Why:** These three bugs together caused every Telegram update to be either: (a) rejected by the security check, or (b) dispatched but crashing immediately because the DB session had no app context and SQL was passed as raw strings.

**How to apply:** Any new bot service that uses raw SQL must use `from sqlalchemy import text` and wrap all SQL strings. All handlers receive `app = ctx.get("app")` to access `app.state.db` and `app.state.redis`.
