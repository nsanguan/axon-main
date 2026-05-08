"""
core.schema.finance — Universal Finance & Cost Management Models.

ERP-agnostic representation of cost records, budgets, cash flow forecasts,
and budget validations. Agents reason about these models; MCP adapters
translate from Odoo account.analytic.line / account.budget.line /
account.move, SAP CO, Oracle GL, etc.

Finance Agent roles:
    1. Costing Agent     — tracks cost impact of procurement & production decisions
    2. Budget Validator  — vetoes decisions that exceed approved budgets (guardrail)
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AxonCostCategory(str, Enum):
    MATERIAL = "material"
    LABOUR = "labour"
    OVERHEAD = "overhead"
    LOGISTICS = "logistics"
    REWORK = "rework"
    SCRAP = "scrap"
    OTHER = "other"


class AxonBudgetStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    EXCEEDED = "exceeded"
    EXHAUSTED = "exhausted"


class AxonBudgetValidationOutcome(str, Enum):
    APPROVED = "approved"
    WARNING = "warning"       # within budget but approaching limit
    REJECTED = "rejected"     # exceeds budget
    NEEDS_CFO_REVIEW = "needs_cfo_review"  # large deviation → human approval


class AxonCashFlowStatus(str, Enum):
    SURPLUS = "surplus"
    BALANCED = "balanced"
    DEFICIT = "deficit"
    CRITICAL_DEFICIT = "critical_deficit"


# ── Cost Tracking ─────────────────────────────────────────────────────────────

class AxonCostLine(BaseModel):
    """A single cost entry (e.g. one purchase order line, one labour posting)."""

    id: str = Field(description="ERP-agnostic cost line identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    description: str = Field(description="Cost description")
    category: AxonCostCategory = Field(description="Cost category")
    amount: float = Field(description="Cost amount in local currency")
    currency: str = Field("USD", description="ISO 4217 currency code")
    cost_date: date = Field(description="Date this cost was incurred or will be incurred")
    product_id: str | None = Field(None, description="Related product (if applicable)")
    product_name: str | None = Field(None, description="Product display name")
    source_ref: str | None = Field(
        None, description="Source document reference (e.g. 'PO/2026/0042')"
    )
    analytic_account: str | None = Field(
        None, description="Analytic account code / cost centre"
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class AxonCostRecord(BaseModel):
    """
    Aggregated cost record for a planning cycle — output of the Costing Agent.
    """

    cycle_id: str = Field(description="Planning cycle reference")
    period_start: date = Field(description="Cost period start")
    period_end: date = Field(description="Cost period end")

    lines: list[AxonCostLine] = Field(
        default_factory=list, description="Individual cost entries"
    )

    total_material_cost: float = Field(0.0, description="Total material costs")
    total_labour_cost: float = Field(0.0, description="Total labour costs")
    total_overhead_cost: float = Field(0.0, description="Total overhead costs")
    total_logistics_cost: float = Field(0.0, description="Total logistics costs")
    total_rework_cost: float = Field(0.0, description="Total rework / scrap costs")
    total_cost: float = Field(0.0, description="Grand total cost")
    currency: str = Field("USD", description="ISO 4217 currency code")

    cost_vs_budget_pct: float | None = Field(
        None,
        description="Total cost as percentage of approved budget (None if no budget set)",
    )
    ai_context: str = Field(description="Costing Agent reasoning for this record")
    confidence: float = Field(1.0, description="Agent confidence (0.0–1.0)")
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Budget Management ─────────────────────────────────────────────────────────

class AxonBudgetLine(BaseModel):
    """A single line in a budget (per cost category / department)."""

    id: str = Field(description="ERP-agnostic budget line identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    category: AxonCostCategory = Field(description="Cost category this line covers")
    department: str = Field(description="Department owning this budget line")
    planned_amount: float = Field(description="Approved budget amount")
    consumed_amount: float = Field(0.0, description="Amount already consumed")
    currency: str = Field("USD", description="ISO 4217 currency code")

    @property
    def remaining_amount(self) -> float:
        return max(0.0, self.planned_amount - self.consumed_amount)

    @property
    def utilisation_pct(self) -> float:
        if self.planned_amount == 0:
            return 100.0
        return (self.consumed_amount / self.planned_amount) * 100.0


class AxonBudget(BaseModel):
    """A budget record for a department / project / period."""

    id: str = Field(description="ERP-agnostic budget identifier")
    erp_id: int | None = Field(None, description="Native ERP record ID")
    name: str = Field(description="Budget name / reference")
    department: str = Field(description="Owning department")
    fiscal_year: str = Field(description="Fiscal year (e.g. '2026')")
    period_start: date = Field(description="Budget period start")
    period_end: date = Field(description="Budget period end")
    status: AxonBudgetStatus = Field(AxonBudgetStatus.APPROVED)
    total_budget: float = Field(description="Total approved budget amount")
    consumed: float = Field(0.0, description="Amount consumed to date")
    currency: str = Field("USD", description="ISO 4217 currency code")
    lines: list[AxonBudgetLine] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def remaining(self) -> float:
        return max(0.0, self.total_budget - self.consumed)

    @property
    def utilisation_pct(self) -> float:
        if self.total_budget == 0:
            return 100.0
        return (self.consumed / self.total_budget) * 100.0


class AxonBudgetValidation(BaseModel):
    """
    Output of the Budget Validator Agent.

    Acts as a Finance guardrail — evaluated before any high-cost action
    (PO confirmation, production launch, logistics booking) is committed.

    If outcome == NEEDS_CFO_REVIEW, the orchestrator fires a LangGraph
    interrupt checkpoint for human (CFO/Finance Manager) sign-off.
    """

    cycle_id: str = Field(description="Planning cycle reference")
    validated_at: datetime = Field(description="When the validation was performed")

    action_type: str = Field(
        description="Action being validated (e.g. 'confirm_po', 'launch_production')"
    )
    action_ref: str = Field(description="Reference of the entity being validated")
    proposed_cost: float = Field(description="Total cost of the proposed action")
    budget_available: float = Field(description="Remaining budget at time of check")
    currency: str = Field("USD", description="ISO 4217 currency code")

    outcome: AxonBudgetValidationOutcome = Field(description="Validation verdict")
    overspend_amount: float = Field(
        0.0, description="Amount by which proposed cost exceeds budget (0 if within budget)"
    )
    overspend_pct: float = Field(
        0.0, description="Overspend as percentage of budget (0 if within budget)"
    )

    requires_cfo_review: bool = Field(
        False,
        description="True when overspend exceeds approval threshold → LangGraph interrupt",
    )
    cfo_review_activity_id: int | None = Field(
        None,
        description="ERP HITL activity ID created for CFO review (if requires_cfo_review=True)",
    )

    recommendation: str = Field(
        description=(
            "Finance recommendation: 'approve' | 'approve_with_warning' | "
            "'reject' | 'escalate_to_cfo'"
        )
    )
    ai_context: str = Field(description="Budget Validator Agent reasoning")
    confidence: float = Field(1.0, description="Agent confidence (0.0–1.0)")
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Cash Flow ─────────────────────────────────────────────────────────────────

class AxonCashFlowEntry(BaseModel):
    """A single inflow or outflow entry in the cash flow forecast."""

    entry_date: date = Field(description="Date of cash movement")
    amount: float = Field(
        description="Cash amount (positive = inflow, negative = outflow)"
    )
    description: str = Field(description="Source description")
    category: AxonCostCategory = Field(description="Related cost category")
    source_ref: str | None = Field(None, description="Source document reference")


class AxonCashFlowForecast(BaseModel):
    """
    Cash flow forecast for the planning horizon — output of the Finance Agent.
    """

    cycle_id: str = Field(description="Planning cycle reference")
    forecast_from: date = Field(description="Forecast start date")
    forecast_to: date = Field(description="Forecast end date")
    currency: str = Field("USD", description="ISO 4217 currency code")

    entries: list[AxonCashFlowEntry] = Field(
        default_factory=list, description="Forecast entries"
    )
    total_inflow: float = Field(0.0, description="Total projected inflows")
    total_outflow: float = Field(0.0, description="Total projected outflows")
    net_cash_flow: float = Field(0.0, description="Net cash flow (inflow - outflow)")
    opening_balance: float = Field(0.0, description="Cash balance at forecast start")
    closing_balance: float = Field(0.0, description="Projected cash balance at forecast end")

    status: AxonCashFlowStatus = Field(description="Overall cash flow health")
    critical_dates: list[str] = Field(
        default_factory=list,
        description="ISO dates where cash balance drops below critical threshold",
    )

    ai_context: str = Field(description="Finance Agent reasoning for this forecast")
    confidence: float = Field(1.0, description="Agent confidence (0.0–1.0)")
    generated_at: datetime = Field(description="When this forecast was generated")
    metadata: dict[str, Any] = Field(default_factory=dict)
