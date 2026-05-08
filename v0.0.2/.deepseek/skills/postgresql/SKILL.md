---
name: postgresql
description: PostgreSQL 18 database design, queries, migrations, and administration. Use when working with PostgreSQL 18 schemas, writing SQL migrations, optimizing queries, managing asyncpg connections, or troubleshooting database issues. Covers PostgreSQL 18 features, asyncpg patterns, and common DBA tasks.
---

# PostgreSQL 18

## Quick start — asyncpg

```python
import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect(
        "postgresql://user:pass@host:5432/dbname",
        timeout=10,
    )
    rows = await conn.fetch("SELECT * FROM users WHERE active = $1", True)
    await conn.close()

asyncio.run(main())
```

## Connection (Axon project)

```python
from axon.core.config import settings

# settings.database.url returns "postgresql+asyncpg://..."
# Strip the +asyncpg prefix for direct asyncpg connect:
url = settings.database.url.replace("postgresql+asyncpg://", "postgresql://")
conn = await asyncpg.connect(url, timeout=15)
```

## PostgreSQL 18 features

### JSONB enhancements
- `jsonb_query()` — XPath-like JSON path queries
- `jsonb_transform()` — bulk transform JSONB arrays
- Improved GIN indexing for JSONB with `jsonb_path_ops`

### Performance
- Parallel query improvements for `SELECT DISTINCT`
- Incremental sort for window functions
- Better JIT compilation for repeated queries

### DDL
- `CREATE TABLE ... (LIKE parent INCLUDING ALL)` now includes generated columns
- `ALTER TABLE ... DETACH PARTITION CONCURRENTLY` — non-blocking partition detach

## Common patterns

### Migration (idempotent)

```sql
CREATE TABLE IF NOT EXISTS items (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name     TEXT NOT NULL,
    meta     JSONB DEFAULT '{}',
    created  TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_items_meta ON items USING gin (meta jsonb_path_ops);
```

### Upsert

```sql
INSERT INTO items (id, name, meta) VALUES ($1, $2, $3)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    meta = EXCLUDED.meta;
```

### Batch insert

```python
await conn.executemany(
    "INSERT INTO items (name, meta) VALUES ($1, $2)",
    [("A", '{}'), ("B", '{}')],
)
```

### JSONB query

```sql
-- Check if JSONB field contains a key=value
SELECT * FROM demands WHERE metadata @> '{"customer": "Boeing"}';

-- Extract a specific field
SELECT metadata->>'order_ref' AS order_ref FROM demands;

-- Update a nested field
UPDATE supplies SET metadata = jsonb_set(metadata, '{quality}', '"B"');
```

### Date / timestamptz

```sql
-- Always use TIMESTAMPTZ for audit columns
-- Query by date range
SELECT * FROM demands
WHERE period_start >= '2026-06-01'
  AND period_end   <= '2026-06-30';

-- Current timestamp
SELECT now();           -- with timezone
SELECT now() AT TIME ZONE 'UTC';
```

## Axon schema patterns

### Domain tables use UUID PKs
```sql
CREATE TABLE demands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ...
);
```

### JSONB for flexible metadata
Demand, Supply, Allocation tables use `metadata JSONB` for ERP-specific attributes (lot numbers, quality grades, shade codes) without schema changes.

### Check constraints for data integrity
```sql
confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1)
violation_severity TEXT CHECK (violation_severity IN ('low','medium','high','critical'))
```

### Foreign keys for referential integrity
```sql
allocations.demand_id → demands(id)
allocations.supply_id → supplies(id)
plan_traces.decision_id → experience_records(id)
```

## Common pitfalls

- **UUIDs must be valid hex** — `s1000000-...` is invalid (s not in 0-9,a-f). Use `gen_random_uuid()` or valid hex strings.
- **asyncpg uses `$1`, not `%s`** — different from psycopg2
- **TIMESTAMPTZ, not TIMESTAMP** — always store with timezone for multi-region planning
- **JSONB `@>` containment** — `data @> '{"key":"val"}'` requires exact match including type; `'{"count":1}'` won't match `'{"count":"1"}'`
- **Don't use `SERIAL` for new tables** — prefer `UUID` or `BIGINT GENERATED ALWAYS AS IDENTITY`
- **Connection pooling** — use `asyncpg.create_pool()` for multi-connection scenarios, not single `connect()`

## References

- Axon DB: `postgresql://axon:***@202.71.1.13:5435/axon` (PostgreSQL 18.3)
- Axon migration: `src/axon/core/schema/migrate.py`
- Axon seed data: `src/axon/core/schema/seed.py`
- Config: `AXON_DATABASE__URL` in `.env`
