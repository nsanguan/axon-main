"""
AxonState — shared state for the main LangGraph workflow.

Includes purchase_analysis_logs (new field) to accumulate the
reasoning trail from the Purchase Cluster (Buyer → Manager → Director).
"""

from __future__ import annotations

from typing import Annotated, Any

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AxonState(TypedDict):
    # ── Cycle identity ────────────────────────────────────────────────────
    cycle_id: str
    """Unique planning cycle identifier, e.g. 'CYCLE-2026-05-07-001'."""

    # ── User strategy & executive directive ──────────────────────────────
    user_strategy: str
    """
    Free-text strategy & policy statement provided by the user/admin at cycle
    start.  Examples: 'Minimise cost this quarter', 'Service level > 98% for
    A-class SKUs', 'Rush replenishment for product IDs 42, 77, 103'.
    Defaults to empty string for automated cycles.
    """

    executive_directive: dict | None
    """
    Serialised AxonExecutiveDirective produced by the Executive Entry Agent.
    Guides Planning Manager thresholds and priority_products.
    """

    # ── ERP data snapshots ─────────────────────────────────────────────
    demand_stream: list[dict]
    """Active demand records (sale orders, forecasts, MPS) from the adapter layer."""

    pegging_ledger: list[dict]
    """Current pegging/allocation records from the adapter layer."""

    supply_stream: list[dict]
    """Available and incoming supply records from the adapter layer."""

    # ── Planning outputs ──────────────────────────────────────────────────
    shortages: list[dict]
    """
    Shortages detected by the Planning Manager.
    Each item: {product_id, product_name, demand_qty, available_qty,
                shortage_qty, demand_date, pegging_id}
    """

    planning_decision: dict | None
    """Serialised AxonPlanningDecision from the Planning Manager Agent."""

    # ── Purchase cluster outputs ──────────────────────────────────────────
    buyer_decision: dict | None
    """Serialised AxonBuyerDecision from the Buyer Agent."""

    manager_analysis: dict | None
    """Serialised AxonManagerAnalysis from the Purchase Manager Agent."""

    director_decision: dict | None
    """Serialised AxonDirectorDecision from the Purchase Director Agent."""

    purchase_analysis_logs: Annotated[list[str], lambda a, b: a + b]
    """
    Append-only audit log of reasoning entries from all 3 purchase agents.
    Each entry is a plain-text line posted to the ERP audit trail.
    """

    # ── Executive escalation ──────────────────────────────────────────────
    executive_summary: dict | None
    """Serialised AxonExecutiveSummary — populated only on low-confidence escalation."""

    # ── HITL / Human-in-the-Loop ──────────────────────────────────────────
    hitl_activity_ids: list[int]
    """Pending ERP activity/task IDs (approval requests waiting for a human)."""

    # ── Inter-departmental constraint propagation ─────────────────────────
    maintenance_constraints: list[dict]
    """
    AxonMaintenanceConstraint dicts from the Maintenance Agent.
    Non-empty triggers production re-scheduling and optional sales notification.
    """

    bom_changes: list[dict]
    """
    AxonBOMChange dicts from the PD (Product Development) Agent.
    Non-empty forces affected MOs to be re-planned before release.
    """

    ng_items: list[dict]
    """
    AxonNGItem dicts from the QC Inspection Agent.
    Each item will have stock_locked=True and rework_order_id set after QC node runs.
    """

    rework_orders: list[dict]
    """
    AxonReworkOrder dicts created by the QC Agent.
    Injected into the planning demand stream for the next MPS run.
    """

    production_schedule: dict | None
    """
    Serialised AxonMPS output from the Production Planning sub-graph.
    None until the production planning node has run.
    """

    # ── Compliance guardrail ──────────────────────────────────────────────
    compliance_decision: dict | None
    """
    Serialised AxonComplianceDecision from the QA Guardrail Agent.
    None until the qa_compliance_checkpoint node has evaluated the cycle actions.
    """

    # ── Finance guardrail ─────────────────────────────────────────────────
    budget_validation: dict | None
    """
    Serialised AxonBudgetValidation from the Budget Validator Agent.
    None until the finance_budget_checkpoint node has run.
    """

    # ── Logistics ────────────────────────────────────────────────────────
    shipments: list[dict]
    """
    AxonShipment dicts produced by the Distribution Agent.
    Populated after the logistics planning node runs.
    """

    hitl_activity_id: int | None
    """Most-recent single HITL activity ID — convenience alias used by workflow nodes."""

    hitl_approved: bool
    """True when the pending HITL activity has been marked Done by a human."""

    human_approval_required: bool
    """True when the workflow is paused at a HITL checkpoint."""

    # ── Workflow control ──────────────────────────────────────────────────
    status: str
    """Current workflow status: 'running' | 'hitl_pending' | 'complete' | 'error'."""

    error: str | None
    """Error message if the workflow encountered an unrecoverable error."""

    # ── Message history ───────────────────────────────────────────────────
    messages: Annotated[list[Any], add_messages]
    """Full agent message history across all nodes."""
