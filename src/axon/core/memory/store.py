"""PostgresStore — LangGraph BaseStore backed by PostgreSQL.

Implements the full `BaseStore` interface for cross-thread long-term memory.
Items are stored in a `memory_store` table with namespace arrays and JSONB values.

Namespace paths are stored as `TEXT[]` arrays for efficient prefix matching.
Values are stored as JSONB for schema-less flexibility.

Usage:
    store = PostgresStore.from_pool(pool)
    await store.aput(("agent_insights", "production"), "bottleneck",
                     {"description": "Line 3 is the bottleneck", "date": "2026-05-08"})
    item = await store.aget(("agent_insights", "production"), "bottleneck")
    results = await store.asearch(("agent_insights",))
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

import asyncpg
from langgraph.store.base import (
    BaseStore,
    GetOp,
    Item,
    ListNamespacesOp,
    PutOp,
    SearchItem,
    SearchOp,
)

# Union of all accepted store operations
_Op = GetOp | SearchOp | PutOp | ListNamespacesOp
# Return type for batch/abatch methods
_BatchResult = Item | list[SearchItem] | list[tuple[str, ...]] | None

# SQL for the memory store table
CREATE_MEMORY_STORE_SQL = """
CREATE TABLE IF NOT EXISTS memory_store (
    namespace   TEXT[] NOT NULL,
    key         TEXT NOT NULL,
    value       JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (namespace, key)
);

CREATE INDEX IF NOT EXISTS idx_memory_store_namespace
    ON memory_store USING GIN (namespace);

CREATE INDEX IF NOT EXISTS idx_memory_store_key
    ON memory_store (key);

CREATE INDEX IF NOT EXISTS idx_memory_store_updated
    ON memory_store (updated_at DESC);
"""

MEMORY_STORE_DELETE_SQL = """
DELETE FROM memory_store WHERE namespace = $1::TEXT[] AND key = $2
"""

MEMORY_STORE_GET_SQL = """
SELECT namespace, key, value, created_at, updated_at
FROM memory_store
WHERE namespace = $1::TEXT[] AND key = $2
"""

MEMORY_STORE_UPSERT_SQL = """
INSERT INTO memory_store (namespace, key, value, created_at, updated_at)
VALUES ($1::TEXT[], $2, $3::JSONB, now(), now())
ON CONFLICT (namespace, key)
DO UPDATE SET value = EXCLUDED.value, updated_at = now()
"""

MEMORY_STORE_SEARCH_SQL = """
SELECT namespace, key, value, created_at, updated_at
FROM memory_store
WHERE namespace[:$1] = $2::TEXT[]
"""

MEMORY_STORE_FILTER_SQL = """
AND value @> $3::JSONB
"""

MEMORY_STORE_ORDER_LIMIT_SQL = """
ORDER BY updated_at DESC
LIMIT $4 OFFSET $5
"""

MEMORY_STORE_LIST_NS_SQL = """
SELECT DISTINCT namespace[:$1] AS ns
FROM memory_store
"""

MEMORY_STORE_LIST_NS_PREFIX_SQL = """
WHERE namespace[:$2] = $3::TEXT[]
"""

MEMORY_STORE_LIST_NS_SUFFIX_SQL = """
AND namespace @> ARRAY[$4]::TEXT[]
"""

MEMORY_STORE_LIST_NS_ORDER_SQL = """
ORDER BY ns
LIMIT $5 OFFSET $6
"""


def _row_to_item(row: asyncpg.Record) -> Item:
    """Convert a database row to a LangGraph Item."""
    value = row["value"]
    if isinstance(value, str):
        value = json.loads(value)
    return Item(
        namespace=tuple(row["namespace"]),
        key=row["key"],
        value=dict(value) if isinstance(value, dict) else {"data": value},
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_search_item(row: asyncpg.Record, score: float = 1.0) -> SearchItem:
    """Convert a database row to a LangGraph SearchItem."""
    value = row["value"]
    if isinstance(value, str):
        value = json.loads(value)
    return SearchItem(
        namespace=tuple(row["namespace"]),
        key=row["key"],
        value=dict(value) if isinstance(value, dict) else {"data": value},
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        score=score,
    )


class PostgresStore(BaseStore):
    """LangGraph BaseStore backed by PostgreSQL.

    Stores items in the `memory_store` table with namespace arrays and JSONB values.
    Supports namespace-prefix search, JSONB filter containment, and namespace listing.

    Args:
        pool: An asyncpg connection pool to reuse. If None, creates one from settings.
    """

    supports_ttl: bool = False

    def __init__(self, pool: asyncpg.Pool | None = None):
        super().__init__()
        self._pool = pool
        self._own_pool = pool is None

    @classmethod
    async def from_pool(cls, pool: asyncpg.Pool) -> PostgresStore:
        """Create a PostgresStore from an existing connection pool.

        Ensures the memory_store table exists.
        """
        store = cls(pool=pool)
        await store.setup()
        return store

    @classmethod
    async def from_conn_string(cls, conn_string: str) -> PostgresStore:
        """Create a PostgresStore from a database connection string.

        Creates its own connection pool. Call close() when done.
        """
        pool = await asyncpg.create_pool(
            conn_string.replace("postgresql+asyncpg://", "postgresql://"),
            min_size=1,
            max_size=5,
        )
        store = cls(pool=pool)
        await store.setup()
        return store

    async def setup(self) -> None:
        """Ensure the memory_store table and indexes exist."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute(CREATE_MEMORY_STORE_SQL)

    async def close(self) -> None:
        """Close the connection pool if we own it."""
        if self._own_pool and self._pool:
            await self._pool.close()
            self._pool = None

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            from axon.core.config import settings

            url = settings.database.url.replace("postgresql+asyncpg://", "postgresql://")
            self._pool = await asyncpg.create_pool(
                url,
                min_size=1,
                max_size=5,
                timeout=15,
            )
        return self._pool

    # =========================================================================
    # Batch — the only abstract method in BaseStore
    # =========================================================================

    def batch(self, ops: Iterable[_Op]) -> list[_BatchResult]:
        """Synchronous batch — not supported. Use abatch()."""
        raise RuntimeError(
            "PostgresStore only supports async operations. Use abatch()."
        )

    async def abatch(self, ops: Iterable[_Op]) -> list[_BatchResult]:
        """Execute multiple store operations asynchronously.

        Dispatches each operation to its handler based on type.
        """
        pool = await self._get_pool()
        results: list[_BatchResult] = []

        async with pool.acquire() as conn:
            for op in ops:
                if isinstance(op, GetOp):
                    results.append(await self._handle_get(conn, op))
                elif isinstance(op, PutOp):
                    results.append(await self._handle_put(conn, op))
                elif isinstance(op, SearchOp):
                    results.append(await self._handle_search(conn, op))
                elif isinstance(op, ListNamespacesOp):
                    results.append(await self._handle_list_namespaces(conn, op))
                else:
                    raise TypeError(f"Unsupported operation: {type(op).__name__}")

        return results

    # =========================================================================
    # Operation handlers
    # =========================================================================

    async def _handle_get(self, conn: asyncpg.Connection, op: GetOp) -> Item | None:
        """Handle a GetOp: retrieve a single item by namespace + key."""
        row = await conn.fetchrow(
            MEMORY_STORE_GET_SQL,
            list(op.namespace),
            op.key,
        )
        if row is None:
            return None
        return _row_to_item(row)

    async def _handle_put(
        self, conn: asyncpg.Connection, op: PutOp
    ) -> None:
        """Handle a PutOp: upsert an item.

        If value is None, delete the item instead.
        """
        if op.value is None:
            await conn.execute(
                MEMORY_STORE_DELETE_SQL,
                list(op.namespace),
                op.key,
            )
        else:
            await conn.execute(
                MEMORY_STORE_UPSERT_SQL,
                list(op.namespace),
                op.key,
                json.dumps(op.value),
            )

    async def _handle_search(
        self, conn: asyncpg.Connection, op: SearchOp
    ) -> list[SearchItem]:
        """Handle a SearchOp: search items by namespace prefix + optional filter."""
        namespace_depth = len(op.namespace_prefix)

        # Build query
        query = MEMORY_STORE_SEARCH_SQL
        params: list[Any] = [namespace_depth, list(op.namespace_prefix)]

        if op.filter:
            query += MEMORY_STORE_FILTER_SQL
            params.append(json.dumps(op.filter))

        query += MEMORY_STORE_ORDER_LIMIT_SQL
        params.extend([op.limit, op.offset])

        rows = await conn.fetch(query, *params)
        return [_row_to_search_item(r) for r in rows]

    async def _handle_list_namespaces(
        self, conn: asyncpg.Connection, op: ListNamespacesOp
    ) -> list[tuple[str, ...]]:
        """Handle a ListNamespacesOp: list distinct namespaces matching filters."""
        max_depth = op.max_depth or 10

        query = MEMORY_STORE_LIST_NS_SQL
        params: list[Any] = [max_depth]

        prefix = None
        suffix = None
        for mc in (op.match_conditions or ()):
            if mc.match_type == "prefix":
                prefix = mc.path
            elif mc.match_type == "suffix":
                suffix = mc.path

        if prefix:
            query += MEMORY_STORE_LIST_NS_PREFIX_SQL
            params.append(len(prefix))
            params.append(list(prefix))
        else:
            # Need at least a WHERE clause before suffix
            query += " WHERE 1=1 "

        if suffix:
            query += MEMORY_STORE_LIST_NS_SUFFIX_SQL
            params.append(list(suffix))

        query += MEMORY_STORE_LIST_NS_ORDER_SQL
        params.extend([op.limit, op.offset])

        rows = await conn.fetch(query, *params)
        return [tuple(row["ns"]) for row in rows if row["ns"]]
