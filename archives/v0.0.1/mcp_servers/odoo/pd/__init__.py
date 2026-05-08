"""
mcp_servers.odoo.pd — Axon FastMCP server for Product Development (SSE transport).

Exposes BOM management, BOM change events, and routing information to the
Axon reasoning layer. Implement tools via Odoo XML-RPC against:
  mrp.bom, mrp.bom.line, mrp.routing.workcenter

Inter-departmental data flow:
  PD Agent detects BOM change → notifies Production Planning Agent → reschedule

Tools:
  axon_get_bom               — read Bill of Materials records
  axon_get_bom_changes       — read recent BOM change events
  axon_get_routing           — read production routing steps
  axon_notify_bom_updated    — signal that a BOM was updated (triggers reschedule)
  axon_post_comment          — post AI reasoning to Chatter
  axon_create_activity       — create HITL mail.activity
  axon_check_activity_done   — poll activity completion
"""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "axon-pd",
    instructions=(
        "Product Development adapter for Axon. "
        "Tools expose BOM management, BOM change events, and routing data "
        "from the ERP into Axon's universal schema."
    ),
)


# ── Input models ──────────────────────────────────────────────────────────────

class GetBOMInput(BaseModel):
    product_id: int | None = Field(
        None, description="Filter by finished product.product ID"
    )
    bom_id: int | None = Field(
        None, description="Fetch a specific mrp.bom ID"
    )
    active_only: bool = Field(True, description="Only return active BOMs")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetBOMChangesInput(BaseModel):
    product_id: int | None = Field(
        None, description="Filter by affected product.product ID"
    )
    changed_since: str | None = Field(
        None,
        description="Return changes after this ISO datetime (YYYY-MM-DDTHH:MM:SS)",
    )
    limit: int = Field(50, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetRoutingInput(BaseModel):
    bom_id: int | None = Field(
        None, description="Filter by mrp.bom ID"
    )
    workcenter_id: int | None = Field(
        None, description="Filter by mrp.workcenter ID"
    )
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class NotifyBOMUpdatedInput(BaseModel):
    bom_id: int = Field(description="mrp.bom ID that was updated")
    change_description: str = Field(
        description="Plain-language description of what changed in the BOM"
    )
    affected_mo_ids: list[int] = Field(
        default_factory=list,
        description="mrp.production IDs that must be re-planned due to this change",
    )
    requires_replan: bool = Field(
        True, description="Whether the production schedule must be re-computed"
    )
    ai_context: str = Field(
        description="PD Agent reasoning explaining the impact of this BOM change"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class PDPostCommentInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'mrp.bom')")
    record_id: int = Field(description="Record ID to post the comment on")
    message: str = Field(description="AI reasoning message to post to Chatter")
    ai_context: str = Field(description="Reason why the agent is posting this comment")


class PDCreateActivityInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'mrp.bom')")
    record_id: int = Field(description="Record ID to attach the activity to")
    summary: str = Field(description="Activity title / summary")
    note: str = Field(description="Detailed note for the human reviewer")
    deadline_days: int = Field(2, description="Days from today until activity deadline")
    ai_context: str = Field(description="Reason why the agent is creating this activity")


class PDCheckActivityInput(BaseModel):
    activity_id: int = Field(description="mail.activity ID to poll")
    ai_context: str = Field(description="Reason why the agent is checking this activity")


# ── Tool definitions ──────────────────────────────────────────────────────────

@mcp.tool()
def axon_get_bom(params: GetBOMInput) -> list[dict]:
    """
    Read Bill of Materials records.
    Returns AxonBOMLine-compatible dicts nested under bom_lines.

    Implement via: mrp.bom + mrp.bom.line.
    """
    raise NotImplementedError(
        "axon_get_bom: implement in Phase 6 using AxonPDSkills"
    )


@mcp.tool()
def axon_get_bom_changes(params: GetBOMChangesInput) -> list[dict]:
    """
    Read recent BOM change events.
    Returns AxonBOMChange-compatible dicts.

    Implement via: mrp.bom write_date filter + mail.message (chatter history)
    or a custom era.bom.change.log model.
    """
    raise NotImplementedError(
        "axon_get_bom_changes: implement in Phase 6 using AxonPDSkills"
    )


@mcp.tool()
def axon_get_routing(params: GetRoutingInput) -> list[dict]:
    """
    Read production routing steps (operations per BOM).
    Returns AxonRoutingStep-compatible dicts.

    Implement via: mrp.routing.workcenter.
    """
    raise NotImplementedError(
        "axon_get_routing: implement in Phase 6 using AxonPDSkills"
    )


@mcp.tool()
def axon_notify_bom_updated(params: NotifyBOMUpdatedInput) -> dict:
    """
    Signal that a BOM was updated and record the change for the Planning Agent.
    Posts Chatter note to affected production orders.
    Returns a summary dict with change_id and affected_mo_count.

    Implement via: mail.message.post on mrp.bom + mrp.production records.
    """
    raise NotImplementedError(
        "axon_notify_bom_updated: implement in Phase 6 using AxonPDSkills"
    )


@mcp.tool()
def axon_post_comment(params: PDPostCommentInput) -> dict:
    """Post AI reasoning to any ERP record's Chatter for audit trail."""
    raise NotImplementedError(
        "axon_post_comment: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_create_activity(params: PDCreateActivityInput) -> dict:
    """Create a mail.activity (HITL gate) on an ERP record for human review."""
    raise NotImplementedError(
        "axon_create_activity: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_check_activity_done(params: PDCheckActivityInput) -> dict:
    """Poll whether a mail.activity has been marked Done by a human."""
    raise NotImplementedError(
        "axon_check_activity_done: implement in Phase 6 using AxonCommunicationSkills"
    )


if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_pd_port)
