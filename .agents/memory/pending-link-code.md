---
name: pending_link_code on users table
description: Where Telegram account-link codes are stored and how they expire
---

## Rule

Telegram link codes (used to connect a Telegram account to an AYZEN user) are stored directly on the `users` table:
- `pending_link_code TEXT UNIQUE` — the random code (urlsafe base64, ~8 chars)
- `pending_link_expires TIMESTAMPTZ` — expiry (24h from generation for admin-generated, 10m for user self-generated)

The `bot_user_service.validate_and_link()` method reads `pending_link_code` from `users` and clears it after successful linking.

The admin endpoint `GET /api/v1/admin/telegram-link-code/{user_id}` reads/writes this column directly.

**Why:** Earlier designs stored link codes in `user_bot_state.link_code` — that column does NOT exist. The correct location is `users.pending_link_code` as written by `bot_user_service.generate_link_code()`.

**How to apply:** Do not query `user_bot_state` for link codes; always use `users.pending_link_code`.
