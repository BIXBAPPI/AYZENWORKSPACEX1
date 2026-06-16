---
name: pgbouncer asyncpg fix
description: How to configure SQLAlchemy asyncpg engine to work with Supabase pgbouncer transaction mode
---

## Rule
When connecting to Supabase (or any pgbouncer in transaction mode) via asyncpg + SQLAlchemy:

```python
from sqlalchemy.pool import NullPool
from uuid import uuid4

engine = create_async_engine(
    database_url,
    poolclass=NullPool,
    echo=False,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    },
)
```

**Why:** pgbouncer transaction mode doesn't support named prepared statements. Multiple concurrent asyncpg connections create `__asyncpg_stmt_N__` with sequential N — pgbouncer routes different frontend connections to the same backend, causing "prepared statement already exists" errors. UUID names make collisions impossible. NullPool prevents SQLAlchemy-level connection reuse. statement_cache_size=0 and prepared_statement_cache_size=0 disable caching.

**How to apply:** Set these on the `create_async_engine` call in `apps/api/main.py`. Do NOT use pool_size/max_overflow with NullPool.
