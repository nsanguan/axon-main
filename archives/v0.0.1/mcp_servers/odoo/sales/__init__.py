"""
mcp_servers.odoo.sales — Axon FastMCP server for Sales & Marketing (SSE transport).

Exposes demand forecasting, ATP checks, and confirmed order reads to the
Axon reasoning layer. Implement tools via Odoo XML-RPC against:
  sale.order, sale.order.line, product.product, crm.lead

Tools:
  axon_get_demand_forecast    — read forecast demand lines
  axon_atp_check              — available-to-promise check per product/date
  axon_get_confirmed_orders   — read confirmed sale orders
  axon_post_comment           — post AI reasoning to Chatter
  axon_create_activity        — create HITL mail.activity
  axon_check_activity_done    — poll activity completion
"""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "axon-sales",
    instructions=(
        "Sales & Marketing adapter for Axon. "
        "Tools expose demand forecasting, ATP confirmation, and confirmed order data "
        "from the ERP into Axon's universal schema."
    ),
)


# ── Input models ──────────────────────────────────────────────────────────────

class GetDemandForecastInput(BaseModel):
    product_ids: list[int] | None = Field(
        None,
        description="Filter by product.product IDs (None = all products)",
    )
    date_from: str | None = Field(
        None, description="Forecast period start (ISO date YYYY-MM-DD)"
    )
    date_to: str | None = Field(
        None, description="Forecast period end (ISO date YYYY-MM-DD)"
    )
    limit: int = Field(100, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class ATPCheckInput(BaseModel):
    product_id: int = Field(description="product.product ID to check")
    requested_qty: float = Field(description="Quantity the customer is requesting")
    requested_date: str = Field(
        description="Customer's requested delivery date (ISO date YYYY-MM-DD)"
    )
    customer_id: int | None = Field(
        None, description="res.partner ID of the customer (optional, for priority rules)"
    )
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetConfirmedOrdersInput(BaseModel):
    product_ids: list[int] | None = Field(
        None, description="Filter by product.product IDs"
    )
    date_from: str | None = Field(
        None, description="Commitment date from (ISO date)"
    )
    date_to: str | None = Field(
        None, description="Commitment date to (ISO date)"
    )
    customer_id: int | None = Field(
        None, description="Filter by res.partner ID"
    )
    limit: int = Field(100, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class SalesPostCommentInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'sale.order')")
    record_id: int = Field(description="Record ID to post the comment on")
    message: str = Field(description="AI reasoning message to post to Chatter")
    ai_context: str = Field(description="Reason why the agent is posting this comment")


class SalesCreateActivityInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'sale.order')")
    record_id: int = Field(description="Record ID to attach the activity to")
    summary: str = Field(description="Activity title / summary shown to the user")
    note: str = Field(description="Detailed note explaining what action is required")
    deadline_days: int = Field(
        2, description="Days from today until the activity deadline"
    )
    ai_context: str = Field(description="Reason why the agent is creating this HITL activity")


class SalesCheckActivityInput(BaseModel):
    activity_id: int = Field(description="mail.activity ID to poll")
    ai_context: str = Field(description="Reason why the agent is checking this activity")


# ── Tool definitions ──────────────────────────────────────────────────────────

@mcp.tool()
def axon_get_demand_forecast(params: GetDemandForecastInput) -> list[dict]:
    """
    Read demand forecast lines from the ERP.
    Returns a list of forecast records with product, quantity, and date fields.
    Each record maps to AxonDemandItem (source_type=FORECAST).

    Implement via: sale.forecast or crm.lead (Odoo CRM pipeline) / custom forecast model.
    """
    raise NotImplementedError(
        "axon_get_demand_forecast: implement in Phase 6 using AxonSalesSkills"
    )


@mcp.tool()
def axon_atp_check(params: ATPCheckInput) -> dict:
    """
    Perform an Available-to-Promise (ATP) check for a specific product and date.
    Returns AxonATPResult-compatible dict with available_qty, promised_date, can_fulfill.

    Implement via: stock.quant (on-hand) + stock.move (incoming) + sale.order.line (demand).
    """
    raise NotImplementedError(
        "axon_atp_check: implement in Phase 6 using AxonSalesSkills"
    )


@mcp.tool()
def axon_get_confirmed_orders(params: GetConfirmedOrdersInput) -> list[dict]:
    """
    Read confirmed sale orders from the ERP.
    Returns sale.order lines in AxonDemandItem-compatible format.

    Implement via: sale.order (state='sale') + sale.order.line.
    """
    raise NotImplementedError(
        "axon_get_confirmed_orders: implement in Phase 6 using AxonSalesSkills"
    )


@mcp.tool()
def axon_post_comment(params: SalesPostCommentInput) -> dict:
    """Post AI reasoning to any ERP record's Chatter for audit trail."""
    raise NotImplementedError(
        "axon_post_comment: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_create_activity(params: SalesCreateActivityInput) -> dict:
    """Create a mail.activity (HITL gate) on an ERP record for human review."""
    raise NotImplementedError(
        "axon_create_activity: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_check_activity_done(params: SalesCheckActivityInput) -> dict:
    """Poll whether a mail.activity has been marked Done by a human."""
    raise NotImplementedError(
        "axon_check_activity_done: implement in Phase 6 using AxonCommunicationSkills"
    )


if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_sales_port)
