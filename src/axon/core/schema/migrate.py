"""
Axon Schema Migration — Purpose-Specific Schemas

Creates 6 schemas with tables organized by purpose:

  axon_brain   — orchestrator state, memory, logging, experience ledger
  axon_agents  — agent proposals, negotiation rounds
  axon_plan    — planning domain data (demands, supplies, allocations)
  axon_mcp     — MCP tool registry
  axon_process — process/workflow definitions (future)
  axon_admin   — admin configuration (future)

Usage: .venv/bin/python3 src/axon/core/schema/migrate.py
"""

from __future__ import annotations

import asyncio

import asyncpg

from axon.core.config import settings

# =============================================================================
# Per-schema DDL
# =============================================================================

BRAIN_SQL = """
-- Orchestrator checkpoint tables (LangGraph short-term memory)
CREATE TABLE IF NOT EXISTS checkpoint_migrations ( v INTEGER PRIMARY KEY );

CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL, parent_checkpoint_id TEXT,
    type TEXT, checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL, version TEXT NOT NULL, type TEXT NOT NULL,
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);

CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL, checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL, task_id TEXT NOT NULL,
    idx INTEGER NOT NULL, channel TEXT NOT NULL,
    type TEXT, blob BYTEA NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);

ALTER TABLE checkpoint_writes ADD COLUMN IF NOT EXISTS task_path TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_checkpoints_thread ON checkpoints(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_blobs_thread ON checkpoint_blobs(thread_id);
CREATE INDEX IF NOT EXISTS idx_checkpoint_writes_thread ON checkpoint_writes(thread_id);

-- Long-term memory store (PostgresStore)
CREATE TABLE IF NOT EXISTS memory_store (
    namespace TEXT[] NOT NULL, key TEXT NOT NULL,
    value JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (namespace, key)
);
CREATE INDEX IF NOT EXISTS idx_memory_store_namespace ON memory_store USING GIN (namespace);
CREATE INDEX IF NOT EXISTS idx_memory_store_key ON memory_store (key);
CREATE INDEX IF NOT EXISTS idx_memory_store_updated ON memory_store (updated_at DESC);

-- Orchestrator execution log
CREATE TABLE IF NOT EXISTS orchestrator_logs (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL, node_name VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL, event_data JSONB,
    state_before JSONB, state_after JSONB, error_message TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT orchestrator_logs_pkey PRIMARY KEY (id)
);
CREATE INDEX IF NOT EXISTS idx_orchestrator_logs_run_id ON orchestrator_logs (run_id);
CREATE INDEX IF NOT EXISTS idx_orchestrator_logs_node_event ON orchestrator_logs (node_name, event_type);
CREATE INDEX IF NOT EXISTS idx_orchestrator_logs_created_at ON orchestrator_logs (created_at DESC);

-- Experience ledger
CREATE TABLE IF NOT EXISTS experience_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL UNIQUE,
    context_snapshot JSONB NOT NULL DEFAULT '{}',
    final_plan JSONB NOT NULL DEFAULT '[]',
    negotiations JSONB DEFAULT '[]', outcome JSONB,
    tags TEXT[] DEFAULT '{}', plan_confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE experience_records ADD COLUMN IF NOT EXISTS correlation_id TEXT DEFAULT '';
ALTER TABLE experience_records ADD COLUMN IF NOT EXISTS warm_archived BOOLEAN DEFAULT FALSE;
ALTER TABLE experience_records ADD COLUMN IF NOT EXISTS embedding double precision[];

CREATE TABLE IF NOT EXISTS plan_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id UUID NOT NULL REFERENCES experience_records(id),
    step_sequence INTEGER NOT NULL, trigger_event TEXT NOT NULL,
    agent_id TEXT NOT NULL, logic_version TEXT,
    input_snapshot JSONB DEFAULT '{}', output_snapshot JSONB DEFAULT '{}',
    confidence FLOAT NOT NULL DEFAULT 0.0 CHECK (confidence >= 0 AND confidence <= 1),
    duration_ms INTEGER DEFAULT 0, model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_traces_decision ON plan_traces(decision_id, step_sequence);

-- NOTIFY function for log stream
CREATE OR REPLACE FUNCTION orchestrator_log_notify()
RETURNS trigger AS $$
BEGIN
    PERFORM pg_notify('orchestrator_log_channel',
        json_build_object('id', NEW.id, 'run_id', NEW.run_id,
            'node_name', NEW.node_name, 'event_type', NEW.event_type,
            'duration_ms', NEW.duration_ms, 'created_at', NEW.created_at)::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS orchestrator_logs_notify_trigger ON orchestrator_logs;
CREATE TRIGGER orchestrator_logs_notify_trigger
    AFTER INSERT ON orchestrator_logs
    FOR EACH ROW EXECUTE FUNCTION orchestrator_log_notify();
"""

AGENTS_SQL = """
CREATE TABLE IF NOT EXISTS agent_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL, round_number INTEGER NOT NULL,
    utility_score FLOAT, justification TEXT,
    status TEXT DEFAULT 'proposed', amendments JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS proposal_allocations (
    proposal_id UUID NOT NULL REFERENCES agent_proposals(id) ON DELETE CASCADE,
    allocation_id UUID NOT NULL,
    PRIMARY KEY (proposal_id, allocation_id)
);

CREATE TABLE IF NOT EXISTS negotiation_rounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    round_number INTEGER NOT NULL, global_utility FLOAT,
    resolved BOOLEAN DEFAULT FALSE, resolution TEXT,
    started_at TIMESTAMPTZ DEFAULT now(), completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_rounds_number ON negotiation_rounds(round_number);
"""

PLAN_SQL = """
CREATE TABLE IF NOT EXISTS demands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_system TEXT NOT NULL, item_type TEXT NOT NULL,
    item_native_id TEXT NOT NULL, item_name TEXT,
    quantity NUMERIC(18,4) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL, period_end TIMESTAMPTZ NOT NULL,
    period_granularity TEXT DEFAULT 'day', source TEXT NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    priority INTEGER DEFAULT 0, customer_id UUID,
    customer_system TEXT, customer_type TEXT, customer_name TEXT,
    metadata JSONB DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS supplies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_system TEXT NOT NULL, item_type TEXT NOT NULL,
    item_native_id TEXT NOT NULL, item_name TEXT,
    quantity NUMERIC(18,4) NOT NULL,
    period_start TIMESTAMPTZ NOT NULL, period_end TIMESTAMPTZ NOT NULL,
    period_granularity TEXT DEFAULT 'day', source TEXT NOT NULL,
    location_system TEXT, location_type TEXT,
    location_native_id TEXT, location_name TEXT,
    lead_time_days INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demand_id UUID NOT NULL REFERENCES demands(id),
    supply_id UUID NOT NULL REFERENCES supplies(id),
    allocated_quantity NUMERIC(18,4) NOT NULL,
    status TEXT DEFAULT 'proposed', violation_alert BOOLEAN DEFAULT FALSE,
    violation_severity TEXT, is_locked BOOLEAN DEFAULT FALSE,
    agent_action TEXT, allocated_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_allocations_demand ON allocations(demand_id);
CREATE INDEX IF NOT EXISTS idx_allocations_supply ON allocations(supply_id);
"""

MCP_SQL = """
CREATE TABLE IF NOT EXISTS tool_registry (
    id SERIAL PRIMARY KEY,
    tool_name TEXT NOT NULL UNIQUE, server_name TEXT NOT NULL,
    direction TEXT NOT NULL DEFAULT 'READ', description TEXT,
    enabled BOOLEAN DEFAULT TRUE, last_seen TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_tool_assignments (
    agent_id TEXT NOT NULL, tool_name TEXT NOT NULL
        REFERENCES tool_registry(tool_name) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, tool_name)
);
"""

# Schemas with no tables yet (placeholder)
PROCESS_SQL = """
-- Reserved for future process/workflow definitions
SELECT 1;
"""

ADMIN_SQL = """
-- Reserved for future admin configuration
SELECT 1;
"""

BOARD_SQL = """
-- Control Tower / Dashboard — persistent state for the Axon board
CREATE SCHEMA IF NOT EXISTS axon_board;

-- HITL + system configuration (single row, id always = 1)
CREATE TABLE IF NOT EXISTS system_config (
    id                       INTEGER PRIMARY KEY DEFAULT 1,
    vip_priority_threshold   INTEGER        NOT NULL DEFAULT 80,
    hitl_delay_days          INTEGER        NOT NULL DEFAULT 7,
    hitl_cost_threshold      NUMERIC(18,2)  NOT NULL DEFAULT 50000.00,
    hitl_first_n_cycles      INTEGER        NOT NULL DEFAULT 5,
    auto_approve_confidence  FLOAT          NOT NULL DEFAULT 0.5,
    max_negotiation_rounds   INTEGER        NOT NULL DEFAULT 5,
    updated_at               TIMESTAMPTZ    NOT NULL DEFAULT now()
);

-- Business weights (single row, upserted on every PUT /api/weights)
CREATE TABLE IF NOT EXISTS business_weights (
    id             INTEGER      PRIMARY KEY DEFAULT 1,
    cost           FLOAT        NOT NULL DEFAULT 0.3,
    delivery       FLOAT        NOT NULL DEFAULT 0.3,
    quality        FLOAT        NOT NULL DEFAULT 0.2,
    sustainability FLOAT        NOT NULL DEFAULT 0.1,
    flexibility    FLOAT        NOT NULL DEFAULT 0.1,
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_by     TEXT         NOT NULL DEFAULT 'system'
);

-- HITL approval queue (persistent mirror of in-memory notification bus)
CREATE TABLE IF NOT EXISTS hitl_queue (
    plan_id            UUID         PRIMARY KEY,
    context_summary    TEXT         NOT NULL DEFAULT '',
    deadlock           BOOLEAN      NOT NULL DEFAULT FALSE,
    demand_count       INTEGER      NOT NULL DEFAULT 0,
    supply_count       INTEGER      NOT NULL DEFAULT 0,
    agent_proposals    INTEGER      NOT NULL DEFAULT 0,
    negotiation_rounds INTEGER      NOT NULL DEFAULT 0,
    global_utility     FLOAT,
    requires_approval  BOOLEAN      NOT NULL DEFAULT TRUE,
    reason             TEXT,
    raw_context        JSONB        NOT NULL DEFAULT '{}',
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Approval decision audit trail
CREATE TABLE IF NOT EXISTS approval_audit (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id     UUID         NOT NULL,
    approved    BOOLEAN      NOT NULL,
    note        TEXT         NOT NULL DEFAULT '',
    decided_by  TEXT         NOT NULL DEFAULT 'planning_manager',
    decided_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_plan    ON approval_audit(plan_id);
CREATE INDEX IF NOT EXISTS idx_audit_decided ON approval_audit(decided_at DESC);

-- Board KPI snapshots (captured on demand or via cron)
CREATE TABLE IF NOT EXISTS board_kpis (
    id                  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    total_plans         INTEGER      NOT NULL DEFAULT 0,
    pending_approvals   INTEGER      NOT NULL DEFAULT 0,
    approved_24h        INTEGER      NOT NULL DEFAULT 0,
    rejected_24h        INTEGER      NOT NULL DEFAULT 0,
    avg_confidence      FLOAT,
    degradation_level   TEXT         NOT NULL DEFAULT 'FULL',
    healthy_server_count INTEGER     NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_kpis_snapshot ON board_kpis(snapshot_at DESC);

-- System event / activity feed
CREATE TABLE IF NOT EXISTS board_events (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type  TEXT         NOT NULL,
    actor       TEXT         NOT NULL DEFAULT 'system',
    plan_id     UUID,
    detail      JSONB        NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_events_type    ON board_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_created ON board_events(created_at DESC);
"""


async def migrate():
    url = settings.database.url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url, timeout=15)

    schemas = {
        "axon_brain": BRAIN_SQL,
        "axon_agents": AGENTS_SQL,
        "axon_plan": PLAN_SQL,
        "axon_mcp": MCP_SQL,
        "axon_process": PROCESS_SQL,
        "axon_admin": ADMIN_SQL,
        "axon_board": BOARD_SQL,
    }

    for schema_name, ddl in schemas.items():
        print(f"  Migrating {schema_name}...")
        prefixed = f"SET search_path TO {schema_name};\n\n{ddl}"
        await conn.execute(prefixed)

    # Verify
    print("\nVerification:")
    for schema_name in schemas:
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = $1 AND table_type = 'BASE TABLE' "
            "ORDER BY table_name",
            schema_name,
        )
        if tables:
            print(f"\n  {schema_name} ({len(tables)} tables):")
            for t in tables:
                print(f"    ✓ {t['table_name']}")

    await conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
