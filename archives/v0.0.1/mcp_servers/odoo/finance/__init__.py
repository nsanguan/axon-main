"""
mcp_servers.odoo.finance — Axon FastMCP server for Finance & Accounting (SSE transport).

Exposes cost records, budget validation, cash flow forecasting, and product
costing to the Axon reasoning layer. Implement tools via Odoo XML-RPC against:
  account.analytic.line, account.budget.line, account.move, product.product

Finance Agent roles:
  1. Costing Agent     — tracks cost impact of procurement & production decisions
  2. Budget Validator  — vetoes decisions that exceed approved budgets (guardrail)
  3. Cash Flow Agent   — forecasts cash flow over the planning horizon

Tools:
  axon_get_cost_records      — read cost postings for a cycle/period
  axon_validate_budget       — check if a proposed cost fits within budget
  axon_get_cash_flow_forecast — generate cash flow forecast
  axon_get_product_cost      — get standard or average cost of a product
  axon_get_budget_status     — read current budget utilisation
  axon_post_comment          — post AI reasoning to Chatter
  axon_create_activity       — create HITL mail.activity (CFO review)
  axon_check_activity_done   — poll activity completion
"""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "axon-finance",
    instructions=(
        "Finance & Accounting adapter for Axon. "
        "Tools expose cost tracking, budget validation, and cash flow forecasting "
        "from the ERP into Axon's universal schema."
    ),
)


# ── Input models ──────────────────────────────────────────────────────────────

class GetCostRecordsInput(BaseModel):
    cycle_id: str | None = Field(
        None, description="Filter by planning cycle reference"
    )
    date_from: str | None = Field(
        None, description="Cost period start (ISO date)"
    )
    date_to: str | None = Field(
        None, description="Cost period end (ISO date)"
    )
    analytic_account: str | None = Field(
        None, description="Analytic account code / cost centre filter"
    )
    category: str | None = Field(
        None,
        description="Cost category: 'material' | 'labour' | 'overhead' | 'logistics' | 'rework' | 'scrap'",
    )
    limit: int = Field(100, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class ValidateBudgetInput(BaseModel):
    action_type: str = Field(
        description="Action being validated: 'confirm_po' | 'launch_production' | 'book_logistics'"
    )
    action_ref: str = Field(
        description="Reference of the entity being validated (e.g. 'PO/2026/0042')"
    )
    proposed_cost: float = Field(description="Total cost of the proposed action")
    currency: str = Field("USD", description="ISO 4217 currency code")
    department: str = Field(
        description="Department initiating the action (e.g. 'procurement')"
    )
    ai_context: str = Field(
        description="Agent reasoning for why this action is being proposed"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class GetCashFlowForecastInput(BaseModel):
    forecast_from: str = Field(
        description="Forecast start date (ISO date YYYY-MM-DD)"
    )
    forecast_to: str = Field(
        description="Forecast end date (ISO date YYYY-MM-DD)"
    )
    include_purchase_orders: bool = Field(
        True, description="Include planned PO outflows"
    )
    include_sale_orders: bool = Field(
        True, description="Include expected SO inflows"
    )
    ai_context: str = Field(description="Reason why the agent is requesting this forecast")
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class GetProductCostInput(BaseModel):
    product_id: int = Field(description="product.product ID")
    cost_method: str = Field(
        "standard",
        description="Cost method: 'standard' | 'average' | 'fifo'",
    )
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class GetBudgetStatusInput(BaseModel):
    department: str | None = Field(
        None, description="Filter by department name"
    )
    fiscal_year: str | None = Field(
        None, description="Fiscal year (e.g. '2026')"
    )
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class FinancePostCommentInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'purchase.order')")
    record_id: int = Field(description="Record ID to post the comment on")
    message: str = Field(description="AI reasoning message to post to Chatter")
    ai_context: str = Field(description="Reason why the agent is posting this comment")


class FinanceCreateActivityInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'purchase.order')")
    record_id: int = Field(description="Record ID to attach the activity to")
    summary: str = Field(description="Activity title (e.g. 'CFO Budget Approval Required')")
    note: str = Field(description="Detailed note including proposed cost vs budget")
    deadline_days: int = Field(2, description="Days from today until CFO review deadline")
    ai_context: str = Field(description="Reason why CFO review is required")


class FinanceCheckActivityInput(BaseModel):
    activity_id: int = Field(description="mail.activity ID to poll")
    ai_context: str = Field(description="Reason why the agent is checking this activity")


# ── Tool definitions ──────────────────────────────────────────────────────────

@mcp.tool()
def axon_get_cost_records(params: GetCostRecordsInput) -> list[dict]:
    """
    Read cost postings for a planning cycle or date period.
    Returns AxonCostLine-compatible dicts.

    Implement via: account.analytic.line search_read().
    """
    raise NotImplementedError(
        "axon_get_cost_records: implement in Phase 6 using AxonFinanceSkills"
    )


@mcp.tool()
def axon_validate_budget(params: ValidateBudgetInput) -> dict:
    """
    Check whether a proposed cost fits within the approved budget.
    Returns AxonBudgetValidation-compatible dict.

    If outcome='needs_cfo_review', the orchestrator fires a LangGraph interrupt.

    Implement via: account.budget.line read() + comparison logic.
    """
    raise NotImplementedError(
        "axon_validate_budget: implement in Phase 6 using AxonFinanceSkills"
    )


@mcp.tool()
def axon_get_cash_flow_forecast(params: GetCashFlowForecastInput) -> dict:
    """
    Generate a cash flow forecast for the planning horizon.
    Returns AxonCashFlowForecast-compatible dict.

    Implement via: account.move (sale invoices) + purchase.order (outflows)
    + payroll estimates.
    """
    raise NotImplementedError(
        "axon_get_cash_flow_forecast: implement in Phase 6 using AxonFinanceSkills"
    )


@mcp.tool()
def axon_get_product_cost(params: GetProductCostInput) -> dict:
    """
    Get the standard, average, or FIFO cost of a product.
    Returns dict with product_id, cost, currency, cost_method.

    Implement via: product.product read(['standard_price']) or
    stock.valuation.layer for FIFO/average.
    """
    raise NotImplementedError(
        "axon_get_product_cost: implement in Phase 6 using AxonFinanceSkills"
    )


@mcp.tool()
def axon_get_budget_status(params: GetBudgetStatusInput) -> list[dict]:
    """
    Read current budget utilisation per department / fiscal year.
    Returns AxonBudget-compatible dicts.

    Implement via: account.budget.line search_read().
    """
    raise NotImplementedError(
        "axon_get_budget_status: implement in Phase 6 using AxonFinanceSkills"
    )


@mcp.tool()
def axon_post_comment(params: FinancePostCommentInput) -> dict:
    """Post AI reasoning to any ERP record's Chatter for audit trail."""
    raise NotImplementedError(
        "axon_post_comment: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_create_activity(params: FinanceCreateActivityInput) -> dict:
    """Create a mail.activity for CFO / Finance Manager budget approval (HITL gate)."""
    raise NotImplementedError(
        "axon_create_activity: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_check_activity_done(params: FinanceCheckActivityInput) -> dict:
    """Poll whether a CFO review mail.activity has been marked Done."""
    raise NotImplementedError(
        "axon_check_activity_done: implement in Phase 6 using AxonCommunicationSkills"
    )


if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_finance_port)
