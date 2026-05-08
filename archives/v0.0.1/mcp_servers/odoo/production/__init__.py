"""
mcp_servers.odoo.production — Axon FastMCP server for Production Planning (SSE transport).

Exposes MPS, work orders, work centres, sequencing, and rescheduling to the
Axon reasoning layer. Implement tools via Odoo XML-RPC against:
  mrp.production, mrp.workcenter, mrp.workorder, mrp.bom

Tools:
  axon_get_mps               — read current Master Production Schedule
  axon_get_work_orders       — list work orders (in-process jobs)
  axon_get_work_centres      — list work centres and their status
  axon_get_sequencing        — read current shop-floor sequencing
  axon_reschedule_production — update production order dates/sequence
  axon_create_production_order — create a new mrp.production
  axon_post_comment          — post AI reasoning to Chatter
  axon_create_activity       — create HITL mail.activity
  axon_check_activity_done   — poll activity completion
"""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "axon-production",
    instructions=(
        "Production Planning adapter for Axon. "
        "Tools expose MPS, work orders, work centres, and sequencing data "
        "from the ERP into Axon's universal schema."
    ),
)


# ── Input models ──────────────────────────────────────────────────────────────

class GetMPSInput(BaseModel):
    date_from: str | None = Field(
        None, description="MPS horizon start (ISO date YYYY-MM-DD)"
    )
    date_to: str | None = Field(
        None, description="MPS horizon end (ISO date YYYY-MM-DD)"
    )
    product_ids: list[int] | None = Field(
        None, description="Filter by product.product IDs"
    )
    limit: int = Field(100, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetWorkOrdersInput(BaseModel):
    production_order_id: int | None = Field(
        None, description="Filter by mrp.production ID"
    )
    workcenter_id: int | None = Field(
        None, description="Filter by mrp.workcenter ID"
    )
    state_filter: list[str] | None = Field(
        None,
        description="Filter by state: 'pending' | 'ready' | 'progress' | 'done' | 'cancel'",
    )
    limit: int = Field(100, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetWorkCentresInput(BaseModel):
    active_only: bool = Field(True, description="Only return active work centres")
    include_blocked: bool = Field(
        True, description="Include work centres blocked by maintenance"
    )
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetSequencingInput(BaseModel):
    workcenter_id: int | None = Field(
        None, description="Filter by mrp.workcenter ID"
    )
    date_from: str | None = Field(
        None, description="Schedule date from (ISO date)"
    )
    date_to: str | None = Field(
        None, description="Schedule date to (ISO date)"
    )
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class RescheduleProductionInput(BaseModel):
    production_order_id: int = Field(
        description="mrp.production ID to reschedule"
    )
    new_scheduled_start: str = Field(
        description="New planned start date (ISO date YYYY-MM-DD)"
    )
    new_scheduled_end: str = Field(
        description="New planned end date (ISO date YYYY-MM-DD)"
    )
    reschedule_reason: str = Field(
        description="Plain-language reason for rescheduling (e.g. 'Machine X breakdown')"
    )
    ai_context: str = Field(
        description="Agent reasoning for this reschedule decision"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class CreateProductionOrderInput(BaseModel):
    product_id: int = Field(description="product.product ID to manufacture")
    qty_planned: float = Field(description="Quantity to produce")
    scheduled_start: str = Field(
        description="Planned start date (ISO date YYYY-MM-DD)"
    )
    bom_id: int | None = Field(
        None, description="mrp.bom ID to use (auto-select if None)"
    )
    demand_ref: str | None = Field(
        None, description="Source demand reference (e.g. 'SO/2026/0042')"
    )
    ai_context: str = Field(
        description="Agent reasoning for creating this production order"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class ProductionPostCommentInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'mrp.production')")
    record_id: int = Field(description="Record ID to post the comment on")
    message: str = Field(description="AI reasoning message to post to Chatter")
    ai_context: str = Field(description="Reason why the agent is posting this comment")


class ProductionCreateActivityInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'mrp.production')")
    record_id: int = Field(description="Record ID to attach the activity to")
    summary: str = Field(description="Activity title / summary")
    note: str = Field(description="Detailed note for the human reviewer")
    deadline_days: int = Field(2, description="Days from today until activity deadline")
    ai_context: str = Field(description="Reason why the agent is creating this activity")


class ProductionCheckActivityInput(BaseModel):
    activity_id: int = Field(description="mail.activity ID to poll")
    ai_context: str = Field(description="Reason why the agent is checking this activity")


# ── Tool definitions ──────────────────────────────────────────────────────────

@mcp.tool()
def axon_get_mps(params: GetMPSInput) -> list[dict]:
    """
    Read the current Master Production Schedule.
    Returns AxonProductionOrder-compatible dicts.

    Implement via: mrp.production (state in ('draft','confirmed','progress')).
    """
    raise NotImplementedError(
        "axon_get_mps: implement in Phase 6 using AxonProductionSkills"
    )


@mcp.tool()
def axon_get_work_orders(params: GetWorkOrdersInput) -> list[dict]:
    """
    List work orders (in-process jobs on shop floor).
    Returns AxonRoutingStep-compatible dicts.

    Implement via: mrp.workorder.
    """
    raise NotImplementedError(
        "axon_get_work_orders: implement in Phase 6 using AxonProductionSkills"
    )


@mcp.tool()
def axon_get_work_centres(params: GetWorkCentresInput) -> list[dict]:
    """
    List work centres and their current status (operational / blocked).
    Returns AxonWorkCenter-compatible dicts.

    Implement via: mrp.workcenter + maintenance.request to detect blocks.
    """
    raise NotImplementedError(
        "axon_get_work_centres: implement in Phase 6 using AxonProductionSkills"
    )


@mcp.tool()
def axon_get_sequencing(params: GetSequencingInput) -> list[dict]:
    """
    Read the current shop-floor sequencing (job queue per work centre).
    Returns AxonSequencingEntry-compatible dicts ordered by sequence_rank.

    Implement via: mrp.workorder (ordered by date_planned_start).
    """
    raise NotImplementedError(
        "axon_get_sequencing: implement in Phase 6 using AxonProductionSkills"
    )


@mcp.tool()
def axon_reschedule_production(params: RescheduleProductionInput) -> dict:
    """
    Update a production order's planned dates and auto-post Chatter reasoning.
    Returns updated AxonProductionOrder-compatible dict.

    Implement via: mrp.production write({date_planned_start, date_planned_finished}).
    """
    raise NotImplementedError(
        "axon_reschedule_production: implement in Phase 6 using AxonProductionSkills"
    )


@mcp.tool()
def axon_create_production_order(params: CreateProductionOrderInput) -> dict:
    """
    Create a new mrp.production and auto-post Chatter reasoning.
    Returns the created AxonProductionOrder-compatible dict.

    Implement via: mrp.production create() + action_confirm().
    """
    raise NotImplementedError(
        "axon_create_production_order: implement in Phase 6 using AxonProductionSkills"
    )


@mcp.tool()
def axon_post_comment(params: ProductionPostCommentInput) -> dict:
    """Post AI reasoning to any ERP record's Chatter for audit trail."""
    raise NotImplementedError(
        "axon_post_comment: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_create_activity(params: ProductionCreateActivityInput) -> dict:
    """Create a mail.activity (HITL gate) on an ERP record for human review."""
    raise NotImplementedError(
        "axon_create_activity: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_check_activity_done(params: ProductionCheckActivityInput) -> dict:
    """Poll whether a mail.activity has been marked Done by a human."""
    raise NotImplementedError(
        "axon_check_activity_done: implement in Phase 6 using AxonCommunicationSkills"
    )


if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_production_port)
