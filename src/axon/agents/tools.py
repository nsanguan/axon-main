"""
MCP tool definitions per domain agent — Phase 5 expanded catalog.

Each of the 10 agents registers a set of MCP tools it is authorized to call.
Tools are defined as functions with typed signatures and docstrings that
serve as the LLM-facing tool description.

Direction semantics:
  - READ: query-only, no side effects. Never requires HITL.
  - WRITE: ERP-side mutation (create PO, update schedule, log decision).
           HITL gating enforced by WriteGate for high-impact operations.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolSpec:
    """Specification for an MCP tool available to an agent."""

    name: str
    description: str
    server: str  # e.g. "oracle_ebs", "sap", "external_rag"
    direction: str = "READ"  # READ (query-only) or WRITE (ERP mutation, HITL-gated)
    agent_ids: list[str] = field(default_factory=list)  # which agents can use it
    hitl_condition: str | None = None  # e.g. "amount > $10k", "shift >= 7 days"


# ---------------------------------------------------------------------------
# Complete tool catalog — all 44 tools across 10 agents
# ---------------------------------------------------------------------------

TOOL_CATALOG: list[ToolSpec] = [
    # ── Sales (5 READ tools) — via mcp_agent_store (inventory/demand) ─
    ToolSpec(
        name="get_available_to_promise",
        description="Return ATP (Available to Promise) quantity for an item across a date range.",
        server="mcp_agent_store",
        direction="READ",
        agent_ids=["sales"],
    ),
    ToolSpec(
        name="get_inventory_levels",
        description="Return on-hand, reserved, and available inventory for items at a location.",
        server="mcp_agent_store",
        direction="READ",
        agent_ids=["sales", "production", "warehouse"],
    ),
    ToolSpec(
        name="get_sales_orders",
        description="List open sales orders with item, quantity, customer, date, and priority.",
        server="mcp_agent_store",
        direction="READ",
        agent_ids=["sales"],
    ),
    ToolSpec(
        name="get_demand_forecast",
        description=(
            "Return statistical or manual forecast for items by period with confidence level."
        ),
        server="mcp_agent_store",
        direction="READ",
        agent_ids=["sales"],
    ),
    ToolSpec(
        name="get_shipments",
        description=(
            "List planned and in-transit shipments with origin, destination, items, and ETA."
        ),
        server="mcp_agent_store",
        direction="READ",
        agent_ids=["sales", "logistics", "warehouse"],
    ),
    # ── Production (5 READ + 1 WRITE) ──────────────────────────────
    ToolSpec(
        name="list_wip_jobs",
        description="List all WIP jobs with status, start/end dates, quantity, and routing.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["production", "maintenance", "qc"],
    ),
    ToolSpec(
        name="get_bom",
        description="Return the bill of materials (components + quantities) for an item.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["production", "pd"],
    ),
    ToolSpec(
        name="get_work_center_capacity",
        description="Return available capacity (hours) per work center per period.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["production"],
    ),
    ToolSpec(
        name="get_routing",
        description="Return the manufacturing routing (operations sequence) for an item.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["production"],
    ),
    ToolSpec(
        name="reschedule_wip_job",
        description="Update start/end dates of a WIP job. HITL required if shift >= 7 days.",
        server="oracle_ebs",
        direction="WRITE",
        agent_ids=["production"],
        hitl_condition="shift >= 7 days",
    ),
    # ── Procurement (5 READ + 1 WRITE) — via mcp_agent_buyer (purchasing) ─
    ToolSpec(
        name="get_suppliers",
        description="Return approved supplier list for an item with lead times, pricing, and MOQ.",
        server="mcp_agent_buyer",
        direction="READ",
        agent_ids=["procurement"],
    ),
    ToolSpec(
        name="get_item_costs",
        description="Return standard and last actual cost for items.",
        server="mcp_agent_buyer",
        direction="READ",
        agent_ids=["procurement", "finance"],
    ),
    ToolSpec(
        name="get_purchase_orders",
        description="List open POs with item, quantity, supplier, due date, and status.",
        server="mcp_agent_buyer",
        direction="READ",
        agent_ids=["procurement"],
    ),
    ToolSpec(
        name="get_supplier_performance",
        description=(
            "Return on-time delivery %, quality score, and lead time variance per supplier."
        ),
        server="mcp_agent_buyer",
        direction="READ",
        agent_ids=["procurement"],
    ),
    ToolSpec(
        name="create_purchase_requisition",
        description="Create a purchase requisition. HITL required if amount > threshold.",
        server="mcp_agent_buyer",
        direction="WRITE",
        agent_ids=["procurement"],
        hitl_condition="amount > $10k",
    ),
    # ── Warehouse (4 READ) — via mcp_agent_store (inventory/warehouse) ─
    ToolSpec(
        name="get_inventory_levels",
        description="Return on-hand, reserved, and available inventory per item × location.",
        server="mcp_agent_store",
        direction="READ",
        agent_ids=["warehouse", "sales", "production"],
    ),
    ToolSpec(
        name="get_safety_stock",
        description="Return safety stock targets per item × location.",
        server="mcp_agent_store",
        direction="READ",
        agent_ids=["warehouse"],
    ),
    ToolSpec(
        name="get_storage_capacity",
        description="Return total and available storage capacity (pallet/volume) per warehouse.",
        server="mcp_agent_store",
        direction="READ",
        agent_ids=["warehouse"],
    ),
    ToolSpec(
        name="get_inventory_aging",
        description="Return inventory aging breakdown (FIFO layers) for items.",
        server="mcp_agent_store",
        direction="READ",
        agent_ids=["warehouse"],
    ),
    # ── Logistics (4 READ + 1 WRITE) — via mcp_agent_store (shipments) ─
    ToolSpec(
        name="get_shipments",
        description=(
            "List planned and in-transit shipments with origin, destination, items, and ETA."
        ),
        server="mcp_agent_store",
        direction="READ",
        agent_ids=["logistics", "sales", "warehouse"],
    ),
    ToolSpec(
        name="get_carrier_rates",
        description="Return carrier rate cards by lane, weight, and service level.",
        server="mcp_agent_store",
        direction="READ",
        agent_ids=["logistics"],
    ),
    ToolSpec(
        name="get_transit_times",
        description="Return standard transit time (days) per lane and service level.",
        server="mcp_agent_store",
        direction="READ",
        agent_ids=["logistics"],
    ),
    ToolSpec(
        name="get_delivery_constraints",
        description=(
            "Return customer delivery windows, dock constraints, and appointment requirements."
        ),
        server="mcp_agent_store",
        direction="READ",
        agent_ids=["logistics"],
    ),
    ToolSpec(
        name="create_shipment",
        description="Create a shipment record. HITL required for expedited shipments.",
        server="mcp_agent_store",
        direction="WRITE",
        agent_ids=["logistics"],
        hitl_condition="expedited shipment",
    ),
    # ── Finance (4 READ) ───────────────────────────────────────────
    ToolSpec(
        name="get_item_costs",
        description="Return standard, actual, and target costs per item.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["finance", "procurement"],
    ),
    ToolSpec(
        name="get_budget",
        description="Return budget allocation per department/cost center per period.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["finance"],
    ),
    ToolSpec(
        name="get_gl_accounts",
        description=(
            "Return chart of accounts relevant to supply chain (COGS, inventory, variance)."
        ),
        server="oracle_ebs",
        direction="READ",
        agent_ids=["finance"],
    ),
    ToolSpec(
        name="get_profitability",
        description="Return margin analysis per item/customer/channel.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["finance"],
    ),
    # ── QA (4 READ) ────────────────────────────────────────────────
    ToolSpec(
        name="get_sop",
        description="Retrieve the relevant Standard Operating Procedure for a process code.",
        server="external_rag",
        direction="READ",
        agent_ids=["qa", "qc", "pd", "maintenance"],
    ),
    ToolSpec(
        name="check_compliance",
        description="Verify a proposed plan or change against regulatory constraints and SOPs.",
        server="external_rag",
        direction="READ",
        agent_ids=["qa", "qc"],
    ),
    ToolSpec(
        name="get_audit_history",
        description="Return recent audit findings relevant to a process or item.",
        server="external_rag",
        direction="READ",
        agent_ids=["qa"],
    ),
    ToolSpec(
        name="get_regulatory_requirements",
        description="Return applicable regulations (FDA, ISO, GMP) for a product category.",
        server="external_rag",
        direction="READ",
        agent_ids=["qa"],
    ),
    # ── QC (4 READ + 1 WRITE) — inspection tools stay on oracle_ebs ─
    ToolSpec(
        name="get_inspection_plan",
        description="Return inspection plan (sampling, criteria) for an item/lot.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["qc"],
    ),
    ToolSpec(
        name="get_defect_history",
        description="Return defect rate and Pareto by item, operation, and period.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["qc"],
    ),
    ToolSpec(
        name="list_wip_jobs",
        description="List WIP jobs needing inspection hold or rework.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["qc", "production", "maintenance"],
    ),
    ToolSpec(
        name="get_sop",
        description="Retrieve QC procedures and acceptance criteria.",
        server="external_rag",
        direction="READ",
        agent_ids=["qc", "qa", "pd", "maintenance"],
    ),
    ToolSpec(
        name="create_inspection_lot",
        description="Create an inspection lot for a received batch. No HITL required.",
        server="oracle_ebs",
        direction="WRITE",
        agent_ids=["qc"],
        hitl_condition="none — batch inspection, no HITL",
    ),
    # ── PD (4 READ) ────────────────────────────────────────────────
    ToolSpec(
        name="get_bom",
        description="Return current and pending BOM revisions for an item.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["pd", "production"],
    ),
    ToolSpec(
        name="get_engineering_changes",
        description="List ECOs (Engineering Change Orders) with status and effective dates.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["pd"],
    ),
    ToolSpec(
        name="get_item_master",
        description="Return item attributes: make/buy, lead time, lifecycle phase, revision.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["pd"],
    ),
    ToolSpec(
        name="get_sop",
        description="Retrieve NPI (New Product Introduction) and ECO procedures.",
        server="external_rag",
        direction="READ",
        agent_ids=["pd", "qa", "qc", "maintenance"],
    ),
    # ── Maintenance (5 READ + 1 WRITE) ─────────────────────────────
    ToolSpec(
        name="get_asset_health",
        description="Return current health score, MTBF, and next scheduled maintenance per asset.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["maintenance"],
    ),
    ToolSpec(
        name="list_wip_jobs",
        description="List WIP jobs to identify production dependencies on assets.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["maintenance", "production", "qc"],
    ),
    ToolSpec(
        name="get_maintenance_schedule",
        description="Return preventive and predictive maintenance schedule per asset.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["maintenance"],
    ),
    ToolSpec(
        name="get_sop",
        description="Retrieve maintenance procedures and safety protocols.",
        server="external_rag",
        direction="READ",
        agent_ids=["maintenance", "qa", "qc", "pd"],
    ),
    ToolSpec(
        name="get_downtime_history",
        description="Return downtime events with duration, cause, and affected capacity.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["maintenance"],
    ),
    ToolSpec(
        name="update_work_center_status",
        description="Update work center status (available, maintenance, down). No HITL required.",
        server="oracle_ebs",
        direction="WRITE",
        agent_ids=["maintenance"],
        hitl_condition="none — status update, no HITL",
    ),
]


def get_tools_for_agent(agent_id: str) -> list[ToolSpec]:
    """Return all tool specs available to a given agent."""
    return [t for t in TOOL_CATALOG if agent_id in t.agent_ids]
