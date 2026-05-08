"""
mcp_servers.legacy_db.server — Legacy Database MCP Adapter (Placeholder).

Connects to any SQL database (MySQL, PostgreSQL, MSSQL, Oracle DB) via
SQLAlchemy and exposes demand/supply/allocation data as Axon-compatible
MCP tools.  Useful for companies without a modern ERP or as a bridge
to custom-built legacy systems.

Tools exposed (all prefixed axon_):
  axon_legacy_get_demand         — query demand from a SQL view / table
  axon_legacy_get_supply         — query open supply (POs, WOs) from SQL
  axon_legacy_get_on_hand        — query on-hand stock from SQL
  axon_legacy_write_allocation   — write pegging / allocation record to SQL
  axon_legacy_post_comment       — insert AI reasoning into an audit log table
  axon_legacy_create_activity    — insert a HITL approval task into SQL table
  axon_legacy_check_activity_done — poll HITL task completion from SQL table

Configuration (.env):
  LEGACY_DB_URL=postgresql+psycopg2://user:pass@host:5432/dbname
  LEGACY_DEMAND_TABLE=vw_demand_items       # view or table for demand
  LEGACY_SUPPLY_TABLE=vw_supply_items       # view or table for supply
  LEGACY_STOCK_TABLE=vw_on_hand             # view or table for stock
  LEGACY_ALLOCATION_TABLE=tbl_allocations   # table to write allocations
  LEGACY_AUDIT_TABLE=tbl_ai_audit           # table to write AI reasoning
  LEGACY_ACTIVITY_TABLE=tbl_hitl_tasks      # table for HITL approval tasks
  MCP_LEGACY_DB_PORT=8040

To activate:
  1. Set MCP_LEGACY_DB_URL=http://<host>:8040/sse in .env
  2. Set LEGACY_DB_URL and table names above
  3. Run: python mcp_servers/legacy_db/server.py

Transport: SSE (FastMCP)
"""

from __future__ import annotations

import os

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "axon-legacy-db",
    instructions=(
        "Legacy SQL database adapter for Axon. "
        "Maps custom SQL views/tables to Axon's universal demand/supply schema. "
        "Configure LEGACY_DB_URL, LEGACY_DEMAND_TABLE, LEGACY_SUPPLY_TABLE, "
        "LEGACY_STOCK_TABLE, LEGACY_ALLOCATION_TABLE in .env."
    ),
)


# ── Input / output models ─────────────────────────────────────────────────────


class LegacyDemandQuery(BaseModel):
    date_from: str = Field(description="Demand date from (YYYY-MM-DD)")
    date_to: str = Field(description="Demand date to (YYYY-MM-DD)")
    product_code: str | None = Field(None, description="Optional product/SKU filter")
    warehouse: str | None = Field(None, description="Optional warehouse/location filter")
    limit: int = Field(500, description="Max records to return")


class LegacySupplyQuery(BaseModel):
    date_from: str | None = Field(None, description="Expected date from (YYYY-MM-DD)")
    product_code: str | None = Field(None, description="Optional product/SKU filter")
    supply_types: list[str] = Field(
        default_factory=lambda: ["PO", "WO"],
        description="Supply types to include (values depend on LEGACY_SUPPLY_TABLE schema)",
    )
    limit: int = Field(500, description="Max records to return")


class LegacyOnHandQuery(BaseModel):
    product_code: str = Field(description="Product/SKU code")
    warehouse: str | None = Field(None, description="Optional warehouse/location filter")


class LegacyAllocationInput(BaseModel):
    demand_ref: str = Field(description="Source demand reference (primary key or business key)")
    supply_ref: str = Field(description="Source supply reference (primary key or business key)")
    product_code: str = Field(description="Product/SKU code")
    allocated_qty: float = Field(description="Quantity to allocate")
    status: str = Field("firm", description="Allocation status (draft/firm/released)")
    ai_context: str = Field(description="AI reasoning context for audit trail")


class LegacyCommentInput(BaseModel):
    entity_type: str = Field(description="Entity type / table name this note refers to")
    record_ref: str = Field(description="Record reference (primary key or business key)")
    note_text: str = Field(description="AI reasoning text to write to the audit log")
    cycle_id: str | None = Field(None, description="Planning cycle identifier")
    confidence: float | None = Field(None, description="AI confidence score 0-1")


class LegacyActivityInput(BaseModel):
    subject: str = Field(description="HITL approval task subject")
    description: str = Field(description="Task description / instruction for human approver")
    record_ref: str = Field(description="Business record reference this task relates to")
    assigned_to: str = Field(description="Username or role to assign task to")
    deadline: str = Field(description="Task deadline (YYYY-MM-DD)")
    ai_context: str = Field(description="AI reasoning context")


class LegacyActivityStatusQuery(BaseModel):
    task_id: int = Field(description="HITL task ID from axon_legacy_create_activity")


# ── Tools ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def axon_legacy_get_demand(query: LegacyDemandQuery) -> list[dict]:
    """
    [TODO] Query demand from a legacy SQL view/table.

    Implementation guide:
      - Read LEGACY_DB_URL, LEGACY_DEMAND_TABLE from env
      - Use SQLAlchemy:
          engine = create_engine(os.getenv('LEGACY_DB_URL'))
          rows = engine.execute(
              f"SELECT * FROM {DEMAND_TABLE} WHERE demand_date BETWEEN :f AND :t",
              f=query.date_from, t=query.date_to
          )
      - Map columns to AxonDemandItem field names:
          product_code → product_id, required_qty → demand_qty,
          need_date → demand_date, status → DemandStatus value
      - Return list of dicts

    Expected LEGACY_DEMAND_TABLE schema (minimum):
      product_code VARCHAR, demand_qty NUMERIC, demand_date DATE,
      source_type VARCHAR, source_ref VARCHAR, status VARCHAR
    """
    raise NotImplementedError(
        "Legacy DB demand adapter not implemented. "
        "Set LEGACY_DB_URL and LEGACY_DEMAND_TABLE, then query via SQLAlchemy."
    )


@mcp.tool()
def axon_legacy_get_supply(query: LegacySupplyQuery) -> list[dict]:
    """
    [TODO] Query open supply (POs, WOs, etc.) from a legacy SQL view/table.

    Implementation guide:
      - Query LEGACY_SUPPLY_TABLE with filters
      - Map columns to AxonSupplyItem field names:
          product_code → product_id, open_qty → supply_qty,
          available_qty, expected_date → supply_date, order_type → source_type
      - Return list of dicts

    Expected LEGACY_SUPPLY_TABLE schema (minimum):
      product_code VARCHAR, supply_qty NUMERIC, available_qty NUMERIC,
      supply_date DATE, source_type VARCHAR, source_ref VARCHAR
    """
    raise NotImplementedError(
        "Legacy DB supply adapter not implemented. "
        "Set LEGACY_DB_URL and LEGACY_SUPPLY_TABLE, then query via SQLAlchemy."
    )


@mcp.tool()
def axon_legacy_get_on_hand(query: LegacyOnHandQuery) -> float:
    """
    [TODO] Query on-hand stock from a legacy SQL view/table.

    Implementation guide:
      - Query LEGACY_STOCK_TABLE for current stock level
      - Aggregate by product_code + optional warehouse
      - Return total on-hand quantity as float

    Expected LEGACY_STOCK_TABLE schema (minimum):
      product_code VARCHAR, warehouse VARCHAR, on_hand_qty NUMERIC
    """
    raise NotImplementedError(
        "Legacy DB stock adapter not implemented. "
        "Set LEGACY_DB_URL and LEGACY_STOCK_TABLE, then query via SQLAlchemy."
    )


@mcp.tool()
def axon_legacy_write_allocation(input: LegacyAllocationInput) -> int:
    """
    [TODO] Write an allocation (pegging) record to the legacy database.

    Implementation guide:
      - INSERT into LEGACY_ALLOCATION_TABLE:
          demand_ref, supply_ref, product_code, allocated_qty, status,
          ai_context, created_at = NOW()
      - Return the new record's primary key (int)

    Expected LEGACY_ALLOCATION_TABLE schema (minimum):
      id SERIAL PRIMARY KEY, demand_ref VARCHAR, supply_ref VARCHAR,
      product_code VARCHAR, allocated_qty NUMERIC, status VARCHAR,
      ai_context TEXT, created_at TIMESTAMP
    """
    raise NotImplementedError(
        "Legacy DB allocation writer not implemented. "
        "Create LEGACY_ALLOCATION_TABLE and INSERT via SQLAlchemy."
    )


@mcp.tool()
def axon_legacy_post_comment(input: LegacyCommentInput) -> int:
    """
    [TODO] Write AI reasoning to a legacy audit log table.

    Implementation guide:
      - INSERT into LEGACY_AUDIT_TABLE:
          entity_type, record_ref, note_text, cycle_id, confidence,
          created_at = NOW(), created_by = 'axon-ai'
      - Return the new audit record ID

    Expected LEGACY_AUDIT_TABLE schema (minimum):
      id SERIAL PRIMARY KEY, entity_type VARCHAR, record_ref VARCHAR,
      note_text TEXT, cycle_id VARCHAR, confidence NUMERIC,
      created_at TIMESTAMP, created_by VARCHAR
    """
    raise NotImplementedError(
        "Legacy DB audit log adapter not implemented. "
        "Create LEGACY_AUDIT_TABLE and INSERT via SQLAlchemy."
    )


@mcp.tool()
def axon_legacy_create_activity(input: LegacyActivityInput) -> int:
    """
    [TODO] Create a HITL approval task in the legacy database.

    Implementation guide:
      - INSERT into LEGACY_ACTIVITY_TABLE:
          subject, description, record_ref, assigned_to, deadline,
          ai_context, status='pending', created_at=NOW()
      - Return the new task ID (int)
      - Optionally trigger an email/notification to assigned_to

    Expected LEGACY_ACTIVITY_TABLE schema (minimum):
      id SERIAL PRIMARY KEY, subject VARCHAR, description TEXT,
      record_ref VARCHAR, assigned_to VARCHAR, deadline DATE,
      ai_context TEXT, status VARCHAR, created_at TIMESTAMP,
      completed_at TIMESTAMP, completed_by VARCHAR
    """
    raise NotImplementedError(
        "Legacy DB HITL activity adapter not implemented. "
        "Create LEGACY_ACTIVITY_TABLE and INSERT via SQLAlchemy."
    )


@mcp.tool()
def axon_legacy_check_activity_done(query: LegacyActivityStatusQuery) -> dict:
    """
    [TODO] Poll a legacy HITL task to check whether it has been approved.

    Implementation guide:
      - SELECT status, completed_by, completed_at
        FROM LEGACY_ACTIVITY_TABLE WHERE id = :task_id
      - Return {done: bool, status, completed_by, completed_at}
    """
    raise NotImplementedError(
        "Legacy DB activity status adapter not implemented. "
        "Query LEGACY_ACTIVITY_TABLE WHERE id = task_id via SQLAlchemy."
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("MCP_LEGACY_DB_PORT", "8040"))
    mcp.run(transport="sse", port=port)
