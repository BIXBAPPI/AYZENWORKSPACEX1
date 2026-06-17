---
name: V4 admin seed
description: How and where the admin user is seeded for AYZEN V4
---

## Admin credentials
- Email: bibappix420@gmail.com
- Password: 12345678@Ba1
- Role: owner, email_verified: true

## Seeding
- Seeded via psql (asyncpg not available outside .venv for inline scripts)
- No activation code required (first user or already exists)
- If user already exists, update password_hash + role via psql UPDATE

**Why:** bcrypt hash must be generated with .venv/bin/python3 -c "import bcrypt;..." then passed to psql, because psql cannot call bcrypt directly.

**How to apply:** Run `psql "$DATABASE_URL"` to check/update admin if password is forgotten or role needs reset.
