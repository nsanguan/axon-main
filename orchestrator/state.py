"""
ASCPState — shared state for the main LangGraph workflow.

Includes purchase_analysis_logs (new field) to accumulate the
reasoning trail from the Purchase Cluster (Buyer → Manager → Director).
"""

from __future__ import annotations

from typing import Annotated, Any

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class ASCPState(TypedDict):
    # ── Cycle identity ────────────────────────────────────────────────────
    cycle_id: str
    """Unique planning cycle identifier, e.g. 'CYCLE-2026-05-07-001'."""

    # ── Odoo data snapshots ───────────────────────────────────────────────
    demand_stream: list[dict]
    """Current era.ascp.demand.stream records."""

    pegging_ledger: list[dict]
    """Current era.ascp.pegging.ledger records."""

    supply_stream: list[dict]
    """Current era.ascp.supply.stream records."""

    # ── Planning outputs ──────────────────────────────────────────────────
    shortages: list[dict]
    """
    Shortages detected by the Planning Manager.
    Each item: {product_id, product_name, demand_qty, available_qty,
                shortage_qty, demand_date, pegging_id}
    """

    planning_decision: dict | None
    """Serialised PlanningDecision from the Planning Manager Agent."""

    # ── Purchase cluster outputs ──────────────────────────────────────────
    buyer_decision: dict | None
    """Serialised BuyerDecision from the Buyer Agent."""

    manager_analysis: dict | None
    """Serialised ManagerAnalysis from the Purchase Manager Agent."""

    director_decision: dict | None
    """Serialised DirectorDecision from the Purchase Director Agent."""

    purchase_analysis_logs: Annotated[list[str], lambda a, b: a + b]
    """
    Append-only audit log of reasoning entries from all 3 purchase agents.
    Each entry is a plain-text line posted to Chatter via ascp_post_comment.
    """

    # ── Executive escalation ──────────────────────────────────────────────
    executive_summary: dict | None
    """Serialised ExecutiveSummary — populated only on low-confidence escalation."""

    # ── HITL / Human-in-the-Loop ──────────────────────────────────────────
    hitl_activity_ids: list[int]
    """Pending Odoo mail.activity IDs (from both Planning and Purchase clusters)."""

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
