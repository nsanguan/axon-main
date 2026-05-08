"""
mcp_servers.odoo.maintenance — Axon FastMCP server for Maintenance (SSE transport).

Exposes asset status, PM schedules, and breakdown events to the Axon reasoning
layer. Implement tools via Odoo XML-RPC against:
  maintenance.equipment, maintenance.request

Inter-departmental data flow:
  Breakdown detected → Maintenance Agent → AxonMaintenanceConstraint
  → Production Planning Agent (reschedule) → Sales Agent (notify delivery slip)

Tools:
  axon_get_breakdowns          — list active breakdown requests
  axon_get_pm_schedule         — list planned PM orders
  axon_get_asset_status        — get current status of assets / work centres
  axon_get_maintenance_summary — consolidated constraint set for planning
  axon_post_comment            — post AI reasoning to Chatter
  axon_create_activity         — create HITL mail.activity
  axon_check_activity_done     — poll activity completion
"""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "axon-maintenance",
    instructions=(
        "Maintenance adapter for Axon. "
        "Tools expose asset status, PM schedules, and breakdown events "
        "from the ERP into Axon's universal schema as AxonMaintenanceConstraint."
    ),
)


# ── Input models ──────────────────────────────────────────────────────────────

class GetBreakdownsInput(BaseModel):
    workcenter_id: int | None = Field(
        None, description="Filter by mrp.workcenter ID"
    )
    severity_filter: list[str] | None = Field(
        None,
        description="Filter by severity: 'low' | 'medium' | 'high' | 'critical'",
    )
    status_filter: list[str] | None = Field(
        None,
        description="Filter by status: 'open' | 'in_repair' (exclude 'resolved')",
    )
    limit: int = Field(50, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetPMScheduleInput(BaseModel):
    date_from: str | None = Field(
        None, description="PM scheduled start from (ISO date)"
    )
    date_to: str | None = Field(
        None, description="PM scheduled start to (ISO date)"
    )
    workcenter_id: int | None = Field(
        None, description="Filter by mrp.workcenter ID"
    )
    include_completed: bool = Field(
        False, description="Include already-completed PM orders"
    )
    limit: int = Field(50, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetAssetStatusInput(BaseModel):
    equipment_ids: list[int] | None = Field(
        None, description="Filter by maintenance.equipment IDs (None = all)"
    )
    status_filter: list[str] | None = Field(
        None,
        description="Filter by status: 'operational' | 'under_maintenance' | 'broken_down'",
    )
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetMaintenanceSummaryInput(BaseModel):
    date_from: str | None = Field(
        None, description="Constraint window start (ISO date)"
    )
    date_to: str | None = Field(
        None, description="Constraint window end (ISO date)"
    )
    ai_context: str = Field(
        description="Reason why the agent is requesting this summary — "
        "used to build the AxonMaintenanceConstraint for the production planner"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class MaintenancePostCommentInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'maintenance.request')")
    record_id: int = Field(description="Record ID to post the comment on")
    message: str = Field(description="AI reasoning message to post to Chatter")
    ai_context: str = Field(description="Reason why the agent is posting this comment")


class MaintenanceCreateActivityInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'maintenance.request')")
    record_id: int = Field(description="Record ID to attach the activity to")
    summary: str = Field(description="Activity title / summary")
    note: str = Field(description="Detailed note for the human reviewer")
    deadline_days: int = Field(2, description="Days from today until activity deadline")
    ai_context: str = Field(description="Reason why the agent is creating this activity")


class MaintenanceCheckActivityInput(BaseModel):
    activity_id: int = Field(description="mail.activity ID to poll")
    ai_context: str = Field(description="Reason why the agent is checking this activity")


# ── Tool definitions ──────────────────────────────────────────────────────────

@mcp.tool()
def axon_get_breakdowns(params: GetBreakdownsInput) -> list[dict]:
    """
    List active breakdown maintenance requests.
    Returns AxonBreakdown-compatible dicts.

    Implement via: maintenance.request (maintenance_type='corrective', stage_id not in done/cancelled).
    """
    raise NotImplementedError(
        "axon_get_breakdowns: implement in Phase 6 using AxonMaintenanceSkills"
    )


@mcp.tool()
def axon_get_pm_schedule(params: GetPMScheduleInput) -> list[dict]:
    """
    List planned Preventive Maintenance orders within the given date window.
    Returns AxonPMOrder-compatible dicts.

    Implement via: maintenance.request (maintenance_type='preventive', schedule_date).
    """
    raise NotImplementedError(
        "axon_get_pm_schedule: implement in Phase 6 using AxonMaintenanceSkills"
    )


@mcp.tool()
def axon_get_asset_status(params: GetAssetStatusInput) -> list[dict]:
    """
    Get current status of assets and linked work centres.
    Returns AxonAsset-compatible dicts.

    Implement via: maintenance.equipment + maintenance.request (active requests).
    """
    raise NotImplementedError(
        "axon_get_asset_status: implement in Phase 6 using AxonMaintenanceSkills"
    )


@mcp.tool()
def axon_get_maintenance_summary(params: GetMaintenanceSummaryInput) -> dict:
    """
    Return a consolidated AxonMaintenanceConstraint dict for the production planner.
    Combines all active breakdowns + upcoming PMs + blocked work centres.

    Implement via: aggregation of axon_get_breakdowns + axon_get_pm_schedule
    + mrp.workcenter capacity analysis.
    """
    raise NotImplementedError(
        "axon_get_maintenance_summary: implement in Phase 6 using AxonMaintenanceSkills"
    )


@mcp.tool()
def axon_post_comment(params: MaintenancePostCommentInput) -> dict:
    """Post AI reasoning to any ERP record's Chatter for audit trail."""
    raise NotImplementedError(
        "axon_post_comment: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_create_activity(params: MaintenanceCreateActivityInput) -> dict:
    """Create a mail.activity (HITL gate) on an ERP record for human review."""
    raise NotImplementedError(
        "axon_create_activity: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_check_activity_done(params: MaintenanceCheckActivityInput) -> dict:
    """Poll whether a mail.activity has been marked Done by a human."""
    raise NotImplementedError(
        "axon_check_activity_done: implement in Phase 6 using AxonCommunicationSkills"
    )


if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_maintenance_port)
