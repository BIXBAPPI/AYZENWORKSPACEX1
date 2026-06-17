---
name: Admin API bugs fixed
description: Known column name mismatches and SQLAlchemy transaction abort pattern in admin router
---

## Rules

1. **`error_logs` table uses `timestamp` not `created_at`** — the column that records when the log was created is named `timestamp`, not `created_at`.

2. **`tasks` table uses `assignee_id` not `assigned_to`** — foreign key to users is `assignee_id`.

3. **SQLAlchemy transaction abort** — when a query inside an async SQLAlchemy session raises an exception, the transaction is left in `aborted` state. Any subsequent queries in the same session will raise `InFailedSQLTransactionError`. Fix: call `await session.rollback()` inside the `except` block before continuing. Alternatively, restructure risky queries into separate `async with db()` sessions.

**Why:** These bugs caused `GET /api/v1/admin/stats` to return `internal_error` because the error_logs count query failed (wrong column name), left the tx aborted, and all subsequent queries in the same session also failed.

**How to apply:** Any time you add a new query to the admin stats endpoint or any endpoint that runs multiple queries in one session, wrap optional/risky queries with try/except + `await session.rollback()`.
