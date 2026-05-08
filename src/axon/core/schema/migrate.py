"""
Axon Schema Migration — Phase 1
Creates all tables for planning data, agent proposals, negotiations, and experience ledger.

Usage: .venv/bin/python3 src/axon/core/schema/migrate.py
"""

from __future__ import annotations

import asyncio

import asyncpg

from axon.core.config import settings

SCHEMA_SQL = """
-- =============================================================================
-- Domain tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS demands (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_system     TEXT NOT NULL,
    item_type       TEXT NOT NULL,
    item_native_id  TEXT NOT NULL,
    item_name       TEXT,
    quantity        NUMERIC(18,4) NOT NULL,
    period_start    TIMESTAMPTZ NOT NULL,
    period_end      TIMESTAMPTZ NOT NULL,
    period_granularity TEXT DEFAULT 'day',
    source          TEXT NOT NULL,  -- forecast, sales_order, safety_stock
    confidence      FLOAT NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    priority        INTEGER DEFAULT 0,
    customer_id     UUID,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS supplies (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_system     TEXT NOT NULL,
    item_type       TEXT NOT NULL,
    item_native_id  TEXT NOT NULL,
    item_name       TEXT,
    quantity        NUMERIC(18,4) NOT NULL,
    period_start    TIMESTAMPTZ NOT NULL,
    period_end      TIMESTAMPTZ NOT NULL,
    period_granularity TEXT DEFAULT 'day',
    source          TEXT NOT NULL,  -- on_hand, wip, purchase_order, planned
    location_system  TEXT,
    location_type    TEXT,
    location_native_id TEXT,
    location_name    TEXT,
    lead_time_days  INTEGER DEFAULT 0,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS allocations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demand_id       UUID NOT NULL REFERENCES demands(id),
    supply_id       UUID NOT NULL REFERENCES supplies(id),
    allocated_quantity NUMERIC(18,4) NOT NULL,
    status          TEXT DEFAULT 'proposed',  -- proposed, approved, rejected, executed
    violation_alert BOOLEAN DEFAULT FALSE,
    violation_severity TEXT,  -- low, medium, high, critical
    is_locked       BOOLEAN DEFAULT FALSE,
    agent_action    TEXT,      -- none, negotiating, escalated, resolved
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_allocations_demand ON allocations(demand_id);
CREATE INDEX IF NOT EXISTS idx_allocations_supply ON allocations(supply_id);

-- =============================================================================
-- Negotiation tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS agent_proposals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        TEXT NOT NULL,  -- sales, production, procurement, etc.
    round_number    INTEGER NOT NULL,
    utility_score   FLOAT,
    justification   TEXT,
    status          TEXT DEFAULT 'proposed',  -- proposed, accepted, rejected, amended
    amendments      JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS proposal_allocations (
    proposal_id     UUID NOT NULL REFERENCES agent_proposals(id) ON DELETE CASCADE,
    allocation_id   UUID NOT NULL REFERENCES allocations(id),
    PRIMARY KEY (proposal_id, allocation_id)
);

CREATE TABLE IF NOT EXISTS negotiation_rounds (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_number    INTEGER NOT NULL,
    global_utility  FLOAT,
    resolved        BOOLEAN DEFAULT FALSE,
    resolution      TEXT,
    started_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_rounds_number ON negotiation_rounds(round_number);

-- =============================================================================
-- Experience Ledger tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS experience_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id         UUID NOT NULL UNIQUE,
    correlation_id  TEXT DEFAULT '',
    context_snapshot JSONB NOT NULL DEFAULT '{}',  -- Demand/Supply/Policy at plan time
    final_plan      JSONB NOT NULL DEFAULT '[]',   -- list of allocations
    negotiations    JSONB DEFAULT '[]',             -- list of round summaries
    outcome         JSONB,                          -- populated after execution
    tags            TEXT[] DEFAULT '{}',
    plan_confidence FLOAT,
    embedding       VECTOR(16),                     -- pgvector for similarity search
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS plan_traces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id     UUID NOT NULL REFERENCES experience_records(id),
    step_sequence   INTEGER NOT NULL,
    trigger_event   TEXT NOT NULL,
    agent_id        TEXT NOT NULL,
    logic_version   TEXT,
    input_snapshot  JSONB DEFAULT '{}',
    output_snapshot JSONB DEFAULT '{}',
    confidence      FLOAT NOT NULL DEFAULT 0.0 CHECK (confidence >= 0 AND confidence <= 1),
    duration_ms     INTEGER DEFAULT 0,
    model_used      TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_traces_decision ON plan_traces(decision_id, step_sequence);

-- =============================================================================
-- Agent & Tool registry
-- =============================================================================

CREATE TABLE IF NOT EXISTS tool_registry (
    id              SERIAL PRIMARY KEY,
    tool_name       TEXT NOT NULL UNIQUE,
    server_name     TEXT NOT NULL,
    direction       TEXT NOT NULL DEFAULT 'READ',  -- READ or WRITE
    description     TEXT,
    enabled         BOOLEAN DEFAULT TRUE,
    last_seen       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_tool_assignments (
    agent_id        TEXT NOT NULL,
    tool_name       TEXT NOT NULL REFERENCES tool_registry(tool_name) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, tool_name)
);
"""


async def migrate():
    url = settings.database.url.replace("postgresql+asyncpg://", "postgresql://")
    print("Connecting to database...")
    conn = await asyncpg.connect(url, timeout=15)

    print("Running schema migration...")
    await conn.execute(SCHEMA_SQL)

    # Verify
    tables = await conn.fetch("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    print(f"\nTables created ({len(tables)}):")
    for t in tables:
        print(f"  ✓ {t['table_name']}")

    await conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
