"""
mcp_servers.odoo.qc — Axon FastMCP server for Quality Control (SSE transport).

Exposes inspection results, NG item detection, stock locking, and rework order
creation to the Axon reasoning layer. Implement tools via Odoo XML-RPC against:
  quality.check, quality.alert, stock.quant, mrp.production

Inter-departmental data flow:
  QC detects NG → lock stock in Warehouse → create rework demand → Planning re-plans

Tools:
  axon_get_inspections      — list quality inspections
  axon_get_ng_items         — list failed / NG inspection results
  axon_lock_stock           — lock stock.quant for quarantine
  axon_create_rework_order  — create a rework/replacement production demand
  axon_get_rework_status    — check status of an open rework order
  axon_post_comment         — post AI reasoning to Chatter
  axon_create_activity      — create HITL mail.activity
  axon_check_activity_done  — poll activity completion
"""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "axon-qc",
    instructions=(
        "Quality Control adapter for Axon. "
        "Tools expose inspection results, NG item management, stock locking, "
        "and rework demand creation from the ERP into Axon's universal schema."
    ),
)


# ── Input models ──────────────────────────────────────────────────────────────

class GetInspectionsInput(BaseModel):
    product_id: int | None = Field(
        None, description="Filter by product.product ID"
    )
    status_filter: list[str] | None = Field(
        None,
        description="Filter by status: 'pending' | 'in_progress' | 'passed' | 'failed'",
    )
    date_from: str | None = Field(
        None, description="Inspection date from (ISO date)"
    )
    limit: int = Field(50, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetNGItemsInput(BaseModel):
    product_id: int | None = Field(
        None, description="Filter by product.product ID"
    )
    resolved: bool = Field(
        False, description="If False, only return unresolved NG items"
    )
    severity_filter: list[str] | None = Field(
        None, description="Filter by severity: 'minor' | 'major' | 'critical'"
    )
    limit: int = Field(50, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class LockStockInput(BaseModel):
    stock_quant_id: int = Field(
        description="stock.quant ID to lock / quarantine"
    )
    reason: str = Field(
        description="Plain-language reason for locking the stock (e.g. 'NG detected by QC inspection QC/2026/001')"
    )
    ai_context: str = Field(
        description="QC Agent reasoning for this stock lock decision"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class CreateReworkOrderInput(BaseModel):
    ng_item_ref: str = Field(
        description="Reference of the NG item triggering the rework (e.g. NG record ID or inspection ref)"
    )
    product_id: int = Field(description="product.product ID of the NG item")
    qty_rework: float = Field(description="Quantity to rework or replace")
    rework_type: str = Field(
        description="Handling method: 'rework' | 'scrap' | 'return_to_vendor' | 'conditional_release'"
    )
    required_by: str = Field(
        description="Date by which reworked/replacement stock is needed (ISO date YYYY-MM-DD)"
    )
    ai_context: str = Field(
        description="QC Agent reasoning for this rework decision"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class GetReworkStatusInput(BaseModel):
    rework_production_id: int = Field(
        description="mrp.production ID of the rework order"
    )
    ai_context: str = Field(description="Reason why the agent is checking rework status")


class QCPostCommentInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'quality.check')")
    record_id: int = Field(description="Record ID to post the comment on")
    message: str = Field(description="AI reasoning message to post to Chatter")
    ai_context: str = Field(description="Reason why the agent is posting this comment")


class QCCreateActivityInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'quality.check')")
    record_id: int = Field(description="Record ID to attach the activity to")
    summary: str = Field(description="Activity title / summary")
    note: str = Field(description="Detailed note for the human reviewer")
    deadline_days: int = Field(1, description="Days from today until activity deadline")
    ai_context: str = Field(description="Reason why the agent is creating this activity")


class QCCheckActivityInput(BaseModel):
    activity_id: int = Field(description="mail.activity ID to poll")
    ai_context: str = Field(description="Reason why the agent is checking this activity")


# ── Tool definitions ──────────────────────────────────────────────────────────

@mcp.tool()
def axon_get_inspections(params: GetInspectionsInput) -> list[dict]:
    """
    List quality inspections from the ERP.
    Returns AxonInspection-compatible dicts.

    Implement via: quality.check search_read().
    """
    raise NotImplementedError(
        "axon_get_inspections: implement in Phase 6 using AxonQCSkills"
    )


@mcp.tool()
def axon_get_ng_items(params: GetNGItemsInput) -> list[dict]:
    """
    List failed (NG) inspection results.
    Returns AxonNGItem-compatible dicts.

    Implement via: quality.check (quality_state='fail') + quality.alert.
    """
    raise NotImplementedError(
        "axon_get_ng_items: implement in Phase 6 using AxonQCSkills"
    )


@mcp.tool()
def axon_lock_stock(params: LockStockInput) -> dict:
    """
    Lock a stock.quant for quarantine after NG detection.
    Posts Chatter note to the affected stock record.
    Returns confirmation dict with quant_id and lock status.

    Implement via: stock.quant write({'reserved_quantity': 0}) +
    move to Quality Control location or set lot blocked=True.
    """
    raise NotImplementedError(
        "axon_lock_stock: implement in Phase 6 using AxonQCSkills"
    )


@mcp.tool()
def axon_create_rework_order(params: CreateReworkOrderInput) -> dict:
    """
    Create a rework production order or scrap record for NG stock.
    Injects a new demand item into the planning stream.
    Returns AxonReworkOrder-compatible dict.

    Implement via:
      - rework:    mrp.production create() with origin referencing NG
      - scrap:     stock.scrap create()
      - vendor:    stock.picking (return) create()
    """
    raise NotImplementedError(
        "axon_create_rework_order: implement in Phase 6 using AxonQCSkills"
    )


@mcp.tool()
def axon_get_rework_status(params: GetReworkStatusInput) -> dict:
    """
    Check the status of an open rework production order.
    Returns AxonProductionOrder-compatible dict for the rework MO.

    Implement via: mrp.production read().
    """
    raise NotImplementedError(
        "axon_get_rework_status: implement in Phase 6 using AxonQCSkills"
    )


@mcp.tool()
def axon_post_comment(params: QCPostCommentInput) -> dict:
    """Post AI reasoning to any ERP record's Chatter for audit trail."""
    raise NotImplementedError(
        "axon_post_comment: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_create_activity(params: QCCreateActivityInput) -> dict:
    """Create a mail.activity (HITL gate) on an ERP record for human review."""
    raise NotImplementedError(
        "axon_create_activity: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_check_activity_done(params: QCCheckActivityInput) -> dict:
    """Poll whether a mail.activity has been marked Done by a human."""
    raise NotImplementedError(
        "axon_check_activity_done: implement in Phase 6 using AxonCommunicationSkills"
    )


if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_qc_port)
