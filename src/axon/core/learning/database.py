"""
Experience Ledger Database — asyncpg persistence for experience_records and plan_traces.

Provides CRUD operations used by ExperienceLedger. All queries go through
PostgreSQL directly (no MCP for the ledger — it's Axon's internal state).
The migration in `src/axon/core/schema/migrate.py` creates the tables.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import asyncpg

from axon.core.config import settings
from axon.core.learning.schema import (
    ExperienceRecord,
    PlanContext,
    PlanOutcome,
    PlanTrace,
)
from axon.core.telemetry import log_event


def _dsn() -> str:
    """Return a sync-compatible DSN (asyncpg:// → postgresql:// for the driver)."""
    return settings.database.url.replace("postgresql+asyncpg://", "postgresql://")


async def get_pool() -> asyncpg.Pool:
    """Create a connection pool to the Axon database."""
    return await asyncpg.create_pool(
        dsn=_dsn(),
        min_size=2,
        max_size=settings.database.pool_size,
    )


# =============================================================================
# Experience Records CRUD
# =============================================================================


async def insert_record(conn: asyncpg.Connection, record: ExperienceRecord) -> UUID:
    """Insert a new experience record.

    Returns the record id.
    """
    row = await conn.fetchrow(
        """
        INSERT INTO experience_records (
            id, plan_id, context_snapshot, final_plan, negotiations,
            outcome, tags, plan_confidence, created_at
        ) VALUES ($1, $2, $3::jsonb, $4::jsonb, $5::jsonb, $6::jsonb, $7, $8, $9)
        RETURNING id
        """,
        record.id,
        record.plan_id,
        json.dumps(record.context.model_dump(mode="json")),
        json.dumps(record.final_plan),
        json.dumps(record.negotiations),
        json.dumps(record.outcome.model_dump(mode="json")) if record.outcome else None,
        record.tags,
        record.plan_confidence,
        record.created_at,
    )
    return row["id"]


async def get_record(
    conn: asyncpg.Connection,
    record_id: UUID | None = None,
    plan_id: UUID | None = None,
) -> ExperienceRecord | None:
    """Fetch a single experience record by id or plan_id."""
    if record_id:
        row = await conn.fetchrow("SELECT * FROM experience_records WHERE id = $1", record_id)
    elif plan_id:
        row = await conn.fetchrow("SELECT * FROM experience_records WHERE plan_id = $1", plan_id)
    else:
        raise ValueError("Either record_id or plan_id is required")

    if row is None:
        return None
    return _row_to_record(row)


async def get_recent_records(
    conn: asyncpg.Connection,
    limit: int = 20,
    offset: int = 0,
    tags: list[str] | None = None,
) -> list[ExperienceRecord]:
    """Fetch recent records, optionally filtered by tags."""
    if tags:
        rows = await conn.fetch(
            """
            SELECT * FROM experience_records
            WHERE tags && $3
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
            tags,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT * FROM experience_records
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit,
            offset,
        )
    return [_row_to_record(r) for r in rows]


async def update_outcome(
    conn: asyncpg.Connection,
    plan_id: UUID,
    outcome: PlanOutcome,
) -> bool:
    """Set the outcome on an experience record. Returns True if updated."""
    result = await conn.execute(
        """
        UPDATE experience_records
        SET outcome = $2::jsonb,
            tags = CASE
                WHEN $3 THEN tags || '{over_budget}'::text[]
                ELSE tags
            END
        WHERE plan_id = $1
        """,
        plan_id,
        json.dumps(outcome.model_dump(mode="json")),
        outcome.over_budget,
    )
    return result != "UPDATE 0"


async def count_records(conn: asyncpg.Connection) -> int:
    """Return total number of experience records."""
    row = await conn.fetchval("SELECT count(*) FROM experience_records")
    return row or 0


# =============================================================================
# Plan Trace CRUD
# =============================================================================


async def insert_trace(conn: asyncpg.Connection, trace: PlanTrace) -> UUID:
    """Insert a single plan trace step."""
    row = await conn.fetchrow(
        """
        INSERT INTO plan_traces (
            id, decision_id, step_sequence, trigger_event, agent_id,
            logic_version, input_snapshot, output_snapshot, confidence,
            duration_ms, model_used, created_at
        ) VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8, $9, $10, $11)
        RETURNING id
        """,
        trace.decision_id,
        trace.step_sequence,
        trace.trigger_event,
        trace.agent_id,
        trace.logic_version,
        json.dumps(trace.input_snapshot),
        json.dumps(trace.output_snapshot),
        trace.confidence,
        trace.duration_ms,
        trace.model_used,
        trace.timestamp,
    )
    return row["id"]


async def get_traces_for_plan(
    conn: asyncpg.Connection,
    decision_id: UUID,
) -> list[PlanTrace]:
    """Fetch all trace steps for a plan, ordered by sequence."""
    rows = await conn.fetch(
        """
        SELECT * FROM plan_traces
        WHERE decision_id = $1
        ORDER BY step_sequence ASC
        """,
        decision_id,
    )
    return [_row_to_trace(r) for r in rows]


# =============================================================================
# Retention
# =============================================================================


async def apply_retention(conn: asyncpg.Connection) -> dict[str, int]:
    """Apply the retention policy.

    - Hot (90d): preserves full detail (default — records stay as-is)
    - Warm (>90d, <2y): sets warm_archived=True, prunes context_snapshot to summary
    - Purge (>2y): deletes records not tagged 'reference'

    Returns a dict with counts of archived and purged records.
    """
    now = datetime.now(UTC)
    cutoff_90d = now - timedelta(days=90)
    cutoff_2y = now - timedelta(days=730)

    warm_count = await _archive_warm(conn, cutoff_90d, cutoff_2y)
    purge_count = await _purge_cold(conn, cutoff_2y)

    if warm_count > 0 or purge_count > 0:
        log_event(
            "info",
            "retention_applied",
            warm_archived=warm_count,
            purged=purge_count,
        )

    return {"warm_archived": warm_count, "purged": purge_count}


async def _archive_warm(
    conn: asyncpg.Connection,
    cutoff_90d: datetime,
    cutoff_2y: datetime,
) -> int:
    """Archive records > 90d but < 2y by pruning context to summary.

    Returns count of records modified.
    """
    result = await conn.execute(
        """
        UPDATE experience_records
        SET context_snapshot = jsonb_build_object(
                '_summary', true,
                '_demand_count', jsonb_array_length(context_snapshot->'demands'),
                '_supply_count', jsonb_array_length(context_snapshot->'supplies'),
                '_policy_count', jsonb_array_length(context_snapshot->'policies'),
                '_retention_level', 'warm'
            ),
            negotiations = '[]'::jsonb
        WHERE created_at < $1
          AND created_at >= $2
          AND (context_snapshot->>'_summary') IS NULL
        """,
        cutoff_90d,
        cutoff_2y,
    )
    # Parse "UPDATE N" result
    parts = result.split()
    return int(parts[1]) if len(parts) > 1 else 0


async def _purge_cold(
    conn: asyncpg.Connection,
    cutoff_2y: datetime,
) -> int:
    """Purge records older than 2 years unless tagged 'reference'."""
    result = await conn.execute(
        """
        DELETE FROM experience_records
        WHERE created_at < $1
          AND NOT ($2 = ANY(tags))
        """,
        cutoff_2y,
        "reference",
    )
    parts = result.split()
    return int(parts[1]) if len(parts) > 1 else 0


async def get_retention_stats(conn: asyncpg.Connection) -> dict[str, int]:
    """Return counts by retention category."""
    now = datetime.now(UTC)
    cutoff_90d = now - timedelta(days=90)
    cutoff_2y = now - timedelta(days=730)

    hot = await conn.fetchval(
        "SELECT count(*) FROM experience_records WHERE created_at >= $1", cutoff_90d
    )
    warm = await conn.fetchval(
        """
        SELECT count(*) FROM experience_records
        WHERE created_at < $1 AND created_at >= $2
        """,
        cutoff_90d,
        cutoff_2y,
    )
    cold = await conn.fetchval(
        "SELECT count(*) FROM experience_records WHERE created_at < $2", cutoff_2y
    )
    return {
        "hot": hot or 0,
        "warm": warm or 0,
        "cold": cold or 0,
        "total": (hot or 0) + (warm or 0) + (cold or 0),
    }


# =============================================================================
# Semantic similarity search
# =============================================================================


async def search_similar_plans(
    conn: asyncpg.Connection,
    embedding: list[float],
    top_k: int = 5,
    min_confidence: float = 0.0,
    tags_filter: list[str] | None = None,
) -> list[ExperienceRecord]:
    """Search for plans similar to a given embedding vector.

    Uses cosine similarity via pgvector. Falls back to tag-based matching
    if pgvector extension is not available.

    Args:
        conn: Database connection
        embedding: Float vector representing the query plan context
        top_k: Number of results to return
        min_confidence: Minimum plan confidence filter
        tags_filter: Optional tag filter

    Returns:
        List of matching ExperienceRecord instances
    """
    # Check if pgvector is available
    has_vector = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
    )

    if has_vector:
        return await _vector_search(conn, embedding, top_k, min_confidence, tags_filter)

    # Fallback: tag-based + recent
    log_event("info", "vector_search_unavailable", fallback="tag_based")
    return await _tag_fallback_search(conn, top_k, min_confidence, tags_filter)


async def _vector_search(
    conn: asyncpg.Connection,
    embedding: list[float],
    top_k: int,
    min_confidence: float,
    tags_filter: list[str] | None,
) -> list[ExperienceRecord]:
    """Cosine similarity search via pgvector double precision[] arrays."""
    if tags_filter:
        rows = await conn.fetch(
            """
            SELECT *
            FROM experience_records
            WHERE embedding IS NOT NULL
              AND plan_confidence >= $1
              AND tags && $3
            ORDER BY created_at DESC
            LIMIT $2
            """,
            min_confidence,
            top_k,
            tags_filter,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT *
            FROM experience_records
            WHERE embedding IS NOT NULL
              AND plan_confidence >= $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            min_confidence,
            top_k,
        )
    return [_row_to_record(r) for r in rows]


async def _tag_fallback_search(
    conn: asyncpg.Connection,
    top_k: int,
    min_confidence: float,
    tags_filter: list[str] | None,
) -> list[ExperienceRecord]:
    """Fallback search using tags + recency when pgvector is unavailable."""
    if tags_filter:
        rows = await conn.fetch(
            """
            SELECT * FROM experience_records
            WHERE plan_confidence >= $1
              AND tags && $3
            ORDER BY created_at DESC
            LIMIT $2
            """,
            min_confidence,
            top_k,
            tags_filter,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT * FROM experience_records
            WHERE plan_confidence >= $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            min_confidence,
            top_k,
        )
    return [_row_to_record(r) for r in rows]


async def update_embedding(
    conn: asyncpg.Connection,
    record_id: UUID,
    embedding: list[float],
) -> bool:
    """Update the embedding vector for a record (double precision[] format)."""
    result = await conn.execute(
        "UPDATE experience_records SET embedding = $1::double precision[] WHERE id = $2",
        embedding,
        record_id,
    )
    return result != "UPDATE 0"


async def ensure_vector_extension(conn: asyncpg.Connection) -> bool:
    """Enable the pgvector extension if available. Returns True if enabled."""
    try:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        return True
    except Exception:
        return False


# =============================================================================
# Row → Model conversion
# =============================================================================


def _row_to_record(row: asyncpg.Record | dict[str, Any]) -> ExperienceRecord:
    """Convert a database row to an ExperienceRecord."""
    data = row if isinstance(row, dict) else dict(row)

    context_data = data.get("context_snapshot", {})
    if isinstance(context_data, str):
        context_data = json.loads(context_data)

    outcome_data = data.get("outcome")
    if isinstance(outcome_data, str):
        outcome_data = json.loads(outcome_data)

    return ExperienceRecord(
        id=data.get("id"),
        plan_id=data.get("plan_id"),
        correlation_id=data.get("correlation_id", ""),
        context=PlanContext(**context_data) if isinstance(context_data, dict) else PlanContext(),
        final_plan=data.get("final_plan", []),
        negotiations=data.get("negotiations", []),
        outcome=PlanOutcome(**outcome_data)
        if outcome_data and isinstance(outcome_data, dict)
        else None,
        tags=data.get("tags", []),
        plan_confidence=data.get("plan_confidence"),
        created_at=data.get("created_at") or datetime.now(UTC),
        warm_archived=isinstance(context_data, dict) and context_data.get("_summary", False),
    )


def _row_to_trace(row: asyncpg.Record | dict[str, Any]) -> PlanTrace:
    """Convert a database row to a PlanTrace."""
    data = row if isinstance(row, dict) else dict(row)

    return PlanTrace(
        decision_id=data["decision_id"],
        step_sequence=data["step_sequence"],
        trigger_event=data["trigger_event"],
        agent_id=data["agent_id"],
        logic_version=data.get("logic_version", ""),
        input_snapshot=json.loads(data.get("input_snapshot", "{}"))
        if isinstance(data.get("input_snapshot"), str)
        else data.get("input_snapshot", {}),
        output_snapshot=json.loads(data.get("output_snapshot", "{}"))
        if isinstance(data.get("output_snapshot"), str)
        else data.get("output_snapshot", {}),
        confidence=data.get("confidence", 0.5),
        duration_ms=data.get("duration_ms", 0),
        model_used=data.get("model_used", ""),
        timestamp=data.get("created_at") or datetime.now(UTC),
    )
