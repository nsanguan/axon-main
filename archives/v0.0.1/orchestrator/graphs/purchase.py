"""
Purchase Sub-graph — orchestrates the 3-agent Purchase Cluster.

Flow: buyer_node → manager_node → director_node
                                       │
                    ┌──────────────────┴──────────────────┐
                    │ hitl_pending                         │ confirmed / partial
                    ▼                                      ▼
           [purchase_hitl_checkpoint]            [purchase_complete]
                    │
                    └──→ resume after human approval → director_node (re-run)

This sub-graph is compiled as a CompiledGraph and called from the main
workflow's "purchase_cluster" node when the Supervisor detects a shortage.

State: AxonPurchaseState (separate from AxonState — merged back by main workflow)
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Annotated, Any

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from agents.purchase.buyer import AxonBuyerDecision, get_axon_buyer_agent
from agents.purchase.director import AxonDirectorDecision, get_axon_purchase_director_agent
from agents.purchase.manager import AxonManagerAnalysis, get_axon_purchase_manager_agent
from core.skills.communication_skills import AxonCommunicationSkills
from core.skills.impact_analysis_skill import AxonImpactAnalysisSkill
from core.skills.procurement_skills import AxonProcurementSkills

# ── Skill singletons ─────────────────────────────────────────────────────────
_procurement = AxonProcurementSkills()
_impact = AxonImpactAnalysisSkill()
_comms = AxonCommunicationSkills()


# ── Sub-graph state ──────────────────────────────────────────────────────────

class AxonPurchaseState(TypedDict):
    """State local to the Purchase sub-graph."""

    cycle_id: str
    """Planning cycle reference (passed in from AxonState)."""

    shortages: list[dict]
    """Shortage list from AxonPlanningDecision — each item has product_id, shortage_qty, demand_date."""

    buyer_decision: dict | None
    """Serialised AxonBuyerDecision — populated after buyer_node."""

    manager_analysis: dict | None
    """Serialised AxonManagerAnalysis — populated after manager_node."""

    director_decision: dict | None
    """Serialised AxonDirectorDecision — populated after director_node."""

    purchase_analysis_logs: Annotated[list[str], lambda a, b: a + b]
    """Append-only log of all reasoning entries from all 3 agents."""

    hitl_activity_ids: list[int]
    """Pending mail.activity IDs from Director's HITL gates."""

    human_approval_required: bool
    """True when Director created HITL activities; pauses the graph."""

    messages: Annotated[list[Any], add_messages]
    """Full message history for debugging."""


# ── Nodes ────────────────────────────────────────────────────────────────────

async def buyer_node(state: AxonPurchaseState) -> dict:
    """
    Buyer Agent: select vendors, create RFQs, return proposed_lines.
    The MCP tools (axon_get_vendor_lead_time, axon_create_rfq) are called
    by the agent via its connected MCP server.
    """
    shortages_json = json.dumps(state["shortages"], ensure_ascii=False)
    prompt = (
        f"Planning cycle: {state['cycle_id']}\n"
        f"Shortages to resolve:\n{shortages_json}\n\n"
        "For each shortage: find the best vendor, create an RFQ, and return "
        "AxonBuyerDecision with all proposed_lines including price_unit and lead_days."
    )

    result = await get_axon_buyer_agent().run(prompt)
    decision: AxonBuyerDecision = result.output

    log_entry = (
        f"[BUYER] cycle={state['cycle_id']} "
        f"action={decision.action} "
        f"rfqs={decision.rfq_ids} "
        f"covered={decision.shortages_covered} "
        f"uncovered={decision.shortages_uncovered} "
        f"| {decision.summary}"
    )

    return {
        "buyer_decision": decision.model_dump(),
        "purchase_analysis_logs": [log_entry],
        "messages": result.all_messages(),
    }


async def manager_node(state: AxonPurchaseState) -> dict:
    """
    Manager Agent: run impact analysis, post comments, return AxonManagerAnalysis.
    """
    buyer_decision = state.get("buyer_decision") or {}
    proposed_lines = buyer_decision.get("proposed_lines", [])

    if not proposed_lines:
        analysis = AxonManagerAnalysis(
            overall_classification="acceptable",
            total_cost_delta=0.0,
            overall_price_delta_pct=0.0,
            line_analyses=[],
            recommendation="confirm_all",
            hitl_required=False,
            summary="No proposed lines to analyse — nothing to purchase.",
            cycle_id=state["cycle_id"],
            purchase_analysis_log="[MANAGER] No lines from Buyer.",
        )
        return {
            "manager_analysis": analysis.model_dump(),
            "purchase_analysis_logs": [analysis.purchase_analysis_log],
        }

    # Build context for the Manager
    buyer_summary = json.dumps(buyer_decision, ensure_ascii=False, default=str)
    prompt = (
        f"Planning cycle: {state['cycle_id']}\n"
        f"Buyer Decision:\n{buyer_summary}\n\n"
        "Analyse the cost and lead-time impact of each proposed line against "
        "the Odoo baseline.  Use axon_analyse_rfq_impact for each RFQ.  "
        "Post your analysis to each RFQ's Chatter.  Return AxonManagerAnalysis."
    )

    result = await get_axon_purchase_manager_agent().run(prompt)
    analysis: AxonManagerAnalysis = result.output

    log_entry = (
        f"[MANAGER] cycle={state['cycle_id']} "
        f"classification={analysis.overall_classification} "
        f"price_delta={analysis.overall_price_delta_pct:.1f}% "
        f"cost_delta={analysis.total_cost_delta:.2f} "
        f"hitl_required={analysis.hitl_required} "
        f"recommendation={analysis.recommendation} "
        f"| {analysis.summary}"
    )

    return {
        "manager_analysis": analysis.model_dump(),
        "purchase_analysis_logs": [log_entry, analysis.purchase_analysis_log],
        "messages": result.all_messages(),
    }


async def director_node(state: AxonPurchaseState) -> dict:
    """
    Director Agent: confirm acceptable POs or create HITL activities for critical ones.
    """
    manager_analysis = state.get("manager_analysis") or {}
    buyer_decision = state.get("buyer_decision") or {}

    manager_json = json.dumps(manager_analysis, ensure_ascii=False, default=str)
    buyer_json = json.dumps(buyer_decision, ensure_ascii=False, default=str)

    prompt = (
        f"Planning cycle: {state['cycle_id']}\n"
        f"Buyer Decision:\n{buyer_json}\n\n"
        f"Manager Analysis:\n{manager_json}\n\n"
        "Make the final procurement decision.  "
        "Confirm acceptable POs via axon_confirm_po.  "
        "Create Odoo approval activities for critical ones via axon_create_activity.  "
        "Post your decision reasoning to Chatter via axon_post_comment.  "
        "Return AxonDirectorDecision."
    )

    result = await get_axon_purchase_director_agent().run(prompt)
    decision: AxonDirectorDecision = result.output

    log_entry = (
        f"[DIRECTOR] cycle={state['cycle_id']} "
        f"action={decision.action} "
        f"confirmed={decision.confirmed_po_ids} "
        f"hitl_activities={decision.hitl_activity_ids} "
        f"pending={decision.pending_po_ids} "
        f"| {decision.summary}"
    )

    return {
        "director_decision": decision.model_dump(),
        "hitl_activity_ids": decision.hitl_activity_ids,
        "human_approval_required": decision.action in ("hitl_pending", "partial_confirm")
        and bool(decision.hitl_activity_ids),
        "purchase_analysis_logs": [log_entry, decision.director_reasoning],
        "messages": result.all_messages(),
    }


def purchase_hitl_checkpoint(state: AxonPurchaseState) -> dict:
    """
    Pause node — the graph interrupts here when human_approval_required=True.
    LangGraph's interrupt() mechanism keeps state persisted until resumed.
    On resume, the workflow routes back to director_node for re-evaluation.
    """
    from langgraph.types import interrupt

    activity_ids = state.get("hitl_activity_ids", [])
    interrupt(
        {
            "reason": "Director approval required",
            "hitl_activity_ids": activity_ids,
            "cycle_id": state["cycle_id"],
            "instructions": (
                "Open Odoo, review the AI reasoning in Chatter, "
                "then mark the activity Done (approve) or Refused (reject)."
            ),
        }
    )
    return {}


def purchase_complete(state: AxonPurchaseState) -> dict:
    """Terminal node — no-op, signals clean completion."""
    return {}


# ── Routing ───────────────────────────────────────────────────────────────────

def route_after_director(state: AxonPurchaseState) -> str:
    """Route to HITL checkpoint or completion after Director runs."""
    if state.get("human_approval_required"):
        return "purchase_hitl_checkpoint"
    return "purchase_complete"


# ── Build sub-graph ───────────────────────────────────────────────────────────

def build_axon_purchase_subgraph() -> Any:
    """
    Compile and return the Purchase sub-graph.

    Usage in main workflow:
        purchase_sg = build_axon_purchase_subgraph()
        workflow.add_node("purchase_cluster", purchase_sg)
    """
    graph = StateGraph(AxonPurchaseState)

    graph.add_node("buyer_node", buyer_node)
    graph.add_node("manager_node", manager_node)
    graph.add_node("director_node", director_node)
    graph.add_node("purchase_hitl_checkpoint", purchase_hitl_checkpoint)
    graph.add_node("purchase_complete", purchase_complete)

    graph.add_edge(START, "buyer_node")
    graph.add_edge("buyer_node", "manager_node")
    graph.add_edge("manager_node", "director_node")
    graph.add_conditional_edges(
        "director_node",
        route_after_director,
        {
            "purchase_hitl_checkpoint": "purchase_hitl_checkpoint",
            "purchase_complete": "purchase_complete",
        },
    )
    # After human approves → re-run Director with same state
    graph.add_edge("purchase_hitl_checkpoint", "director_node")
    graph.add_edge("purchase_complete", END)

    return graph.compile()


# Module-level compiled sub-graph (import this into main workflow)
axon_purchase_subgraph = build_axon_purchase_subgraph()


async def run_purchase_cluster(
    shortages: list[dict],
    cycle_id: str,
) -> dict:
    """
    Entry point for the purchase cluster sub-graph.

    Invokes the compiled axon_purchase_subgraph with the given shortages and
    returns a dict containing buyer_decision, manager_analysis,
    director_decision, and purchase_analysis_logs — ready to be merged
    into AxonState by the main workflow node.
    """
    initial_state: AxonPurchaseState = {
        "cycle_id": cycle_id,
        "shortages": shortages,
        "buyer_decision": None,
        "manager_analysis": None,
        "director_decision": None,
        "purchase_analysis_logs": [],
        "hitl_activity_ids": [],
        "human_approval_required": False,
        "messages": [],
    }
    final_state = await axon_purchase_subgraph.ainvoke(initial_state)
    return {
        "buyer_decision": final_state.get("buyer_decision"),
        "manager_analysis": final_state.get("manager_analysis"),
        "director_decision": final_state.get("director_decision"),
        "purchase_analysis_logs": final_state.get("purchase_analysis_logs", []),
        "hitl_activity_ids": final_state.get("hitl_activity_ids", []),
        "human_approval_required": final_state.get("human_approval_required", False),
    }
