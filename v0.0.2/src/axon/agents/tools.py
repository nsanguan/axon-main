"""MCP tool definitions per domain agent.

Each of the 10 agents registers a set of MCP tools it is authorized to call.
Tools are defined as functions with typed signatures and docstrings that
serve as the LLM-facing tool description.
"""

from dataclasses import dataclass, field


@dataclass
class ToolSpec:
    """Specification for an MCP tool available to an agent."""

    name: str
    description: str
    server: str  # e.g. "oracle_ebs", "sap", "external_rag"
    direction: str = "READ"  # READ (query-only, no HITL) or WRITE (ERP mutation, HITL-gated)
    agent_ids: list[str] = field(default_factory=list)  # which agents can use it


# ---------------------------------------------------------------------------
# Tool catalog — populated in Phase 2–3 as connectors come online
# ---------------------------------------------------------------------------

TOOL_CATALOG: list[ToolSpec] = [
    # Sales
    ToolSpec(
        name="get_available_to_promise",
        description="Return ATP (Available to Promise) quantity for an item and date range.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["sales"],
    ),
    # Production
    ToolSpec(
        name="list_wip_jobs",
        description="List all WIP (Work in Process) jobs with status, quantity, and schedule.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["production", "maintenance"],
    ),
    # Procurement
    ToolSpec(
        name="get_suppliers",
        description="Return approved supplier list for a given item with lead times and pricing.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["procurement"],
    ),
    # Warehouse
    ToolSpec(
        name="get_inventory_levels",
        description="Return on-hand and reserved inventory for items at a given location.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["warehouse", "sales", "production"],
    ),
    # Finance
    ToolSpec(
        name="get_item_costs",
        description="Return standard and actual cost for items.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["finance", "procurement"],
    ),
    # QA / QC / PD
    ToolSpec(
        name="get_sop",
        description="Retrieve the relevant Standard Operating Procedure for a process.",
        server="external_rag",
        direction="READ",
        agent_ids=["qa", "qc", "pd", "maintenance"],
    ),
    ToolSpec(
        name="check_compliance",
        description="Verify a plan or change against regulatory and SOP constraints.",
        server="external_rag",
        direction="READ",
        agent_ids=["qa", "qc"],
    ),
    # Logistics
    ToolSpec(
        name="get_shipments",
        description="List planned and in-transit shipments with origin, destination, items, and ETA.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["logistics", "sales", "warehouse"],
    ),
    ToolSpec(
        name="get_carrier_rates",
        description="Return carrier rate cards by lane, weight, and service level.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["logistics"],
    ),
    ToolSpec(
        name="get_transit_times",
        description="Return standard transit time (days) per lane and service level.",
        server="oracle_ebs",
        direction="READ",
        agent_ids=["logistics"],
    ),
    # Production — WRITE
    ToolSpec(
        name="reschedule_wip_job",
        description="Update start/end dates of a WIP job. Requires HITL if shift ≥ 7 days.",
        server="oracle_ebs",
        direction="WRITE",
        agent_ids=["production"],
    ),
    # Procurement — WRITE
    ToolSpec(
        name="create_purchase_requisition",
        description="Create a purchase requisition. Requires HITL if amount > threshold.",
        server="oracle_ebs",
        direction="WRITE",
        agent_ids=["procurement"],
    ),
    # Maintenance — WRITE
    ToolSpec(
        name="update_work_center_status",
        description="Update work center status (available, maintenance, down). No HITL required.",
        server="oracle_ebs",
        direction="WRITE",
        agent_ids=["maintenance"],
    ),
]


def get_tools_for_agent(agent_id: str) -> list[ToolSpec]:
    """Return all tool specs available to a given agent."""
    return [t for t in TOOL_CATALOG if agent_id in t.agent_ids]
