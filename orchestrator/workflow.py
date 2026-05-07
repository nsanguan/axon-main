"""
Main LangGraph workflow — ASCP Planning Cycle.

Flow (Pattern C — Supervisor routing):

[START]
  │
  ▼
[sync_demand] ──→ [sync_supply]
                       │
                       ▼
            [planning_manager_node]
                       │
                       ▼
               [supervisor_node]  ← deterministic router
                 │        │        │
       shortage  │  hitl  │  low   │  allocate
                 │  req.  │  conf. │
                 ▼        ▼        ▼
      [purchase_cluster] [hitl_  [executive_
           (sub-graph)   checkpt]    node]
              │             │          │
              │      ┌──────┘          │
              └──────┴─────────────────┘
                          │
                          ▼
                  [update_pegging]
                          │
                          ▼
                       [notify]
                          │
                          ▼
                        [END]

The purchase_cluster node embeds the compiled Purchase sub-graph
(orchestrator/purchase_workflow.py) and merges PurchaseState back
into ASCPState after it completes.
"""

from __future__ import annotations

import json
import uuid
from datetime import date
from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

from agents.purchase.buyer_agent import BuyerDecision
from core.skills.communication_skills import CommunicationSkills
from core.skills.planning_skills import PlanningSkills
from core.skills.procurement_skills import ProcurementSkills
from core.skills.inventory_skills import InventorySkills
from orchestrator.purchase_workflow import PurchaseState, purchase_subgraph
from orchestrator.state import ASCPState

# ── Skill singletons ─────────────────────────────────────────────────────────
_planning = PlanningSkills()
_comms = CommunicationSkills()
_procurement = ProcurementSkills()
_inventory = InventorySkills()


# ── Helper ────────────────────────────────────────────────────────────────────

def _new_cycle_id() -> str:
    today = date.today().isoformat()
    return f"CYCLE-{today}-{uuid.uuid4().hex[:6].upper()}"


# ── Nodes ─────────────────────────────────────────────────────────────────────

async def sync_demand_node(state: ASCPState) -> dict:
    """Pull confirmed SOs → upsert era.ascp.demand.stream."""
    cycle_id = state.get("cycle_id") or _new_cycle_id()
    result = _planning.sync_demand_from_so(
        ai_context=f"Planning cycle {cycle_id}: syncing demand from confirmed SOs",
        cycle_id=cycle_id,
    )
    demand_stream = _planning.client.search_read(
        "era.ascp.demand.stream",
        [("state", "in", ["open", "pegged"])],
        ["id", "name", "product_id", "demand_qty", "confirmed_qty", "demand_date", "state"],
        limit=500,
    )
    return {"cycle_id": cycle_id, "demand_stream": demand_stream}


async def sync_supply_node(state: ASCPState) -> dict:
    """Snapshot era.ascp.supply.stream for the current cycle."""
    supply_stream = _planning.client.search_read(
        "era.ascp.supply.stream",
        [("state", "in", ["open", "allocated", "partial"])],
        ["id", "name", "product_id", "supply_qty", "available_qty", "supply_date", "state"],
        limit=500,
    )
    pegging_ledger = _planning.client.search_read(
        "era.ascp.pegging.ledger",
        [("status", "in", ["draft", "firm", "partial"])],
        ["id", "name", "product_id", "allocated_qty", "status", "demand_date", "plan_date"],
        limit=500,
    )
    return {"supply_stream": supply_stream, "pegging_ledger": pegging_ledger}


async def planning_manager_node(state: ASCPState) -> dict:
    """
    Planning Manager Agent (stub — wired to mcp-ascp-planning in Phase 3).
    Returns a planning_decision dict.  For now delegates directly to skills.
    """
    from agents.planning_manager import get_planning_manager_agent, PlanningDecision

    demand_json = json.dumps(state.get("demand_stream", [])[:50], ensure_ascii=False, default=str)
    ledger_json = json.dumps(state.get("pegging_ledger", [])[:50], ensure_ascii=False, default=str)
    prompt = (
        f"Planning cycle: {state['cycle_id']}\n"
        f"Demand stream (first 50):\n{demand_json}\n\n"
        f"Pegging ledger (first 50):\n{ledger_json}\n\n"
        "Analyse demand vs supply, detect shortages, and return PlanningDecision."
    )

    result = await get_planning_manager_agent().run(prompt)
    decision: PlanningDecision = result.output

    return {
        "planning_decision": decision.model_dump(),
        "shortages": [s.model_dump() for s in decision.shortages],
        "hitl_activity_ids": decision.hitl_activity_ids,
        "messages": result.all_messages(),
    }


def supervisor_node(state: ASCPState) -> str:
    """
    Deterministic router — reads ASCPState, returns next node name.
    No LLM involved.
    """
    decision = state.get("planning_decision") or {}
    action = decision.get("action", "no_action")
    confidence = decision.get("confidence", 1.0)

    if action == "shortage" and state.get("shortages"):
        return "purchase_cluster"

    if action == "hitl_required":
        return "hitl_checkpoint"

    if confidence < 0.7:
        return "executive_node"

    return "update_pegging"


async def purchase_cluster_node(state: ASCPState) -> dict:
    """
    Runs the compiled Purchase sub-graph and merges results back into ASCPState.
    """
    purchase_input: PurchaseState = {
        "cycle_id": state["cycle_id"],
        "shortages": state.get("shortages", []),
        "buyer_decision": None,
        "manager_analysis": None,
        "director_decision": None,
        "purchase_analysis_logs": [],
        "hitl_activity_ids": [],
        "human_approval_required": False,
        "messages": [],
    }

    final_state: PurchaseState = await purchase_subgraph.ainvoke(purchase_input)

    # Merge purchase sub-graph outputs back into main state
    merged: dict = {
        "buyer_decision": final_state.get("buyer_decision"),
        "manager_analysis": final_state.get("manager_analysis"),
        "director_decision": final_state.get("director_decision"),
        "purchase_analysis_logs": final_state.get("purchase_analysis_logs", []),
        "hitl_activity_ids": (
            state.get("hitl_activity_ids", [])
            + final_state.get("hitl_activity_ids", [])
        ),
        "human_approval_required": final_state.get("human_approval_required", False),
        "messages": final_state.get("messages", []),
    }
    return merged


def hitl_checkpoint_node(state: ASCPState) -> dict:
    """Pause for Planning-level HITL (e.g. date slip exception)."""
    interrupt(
        {
            "reason": "Planning Manager requested human approval",
            "hitl_activity_ids": state.get("hitl_activity_ids", []),
            "cycle_id": state["cycle_id"],
        }
    )
    return {}


async def executive_node(state: ASCPState) -> dict:
    """Executive Agent — escalation path for low-confidence decisions."""
    from agents.executive_agent import get_executive_agent, ExecutiveSummary

    context = json.dumps(
        {
            "planning_decision": state.get("planning_decision"),
            "shortages": state.get("shortages", []),
            "cycle_id": state["cycle_id"],
        },
        ensure_ascii=False,
        default=str,
    )
    prompt = (
        f"Low-confidence planning decision for cycle {state['cycle_id']}.\n"
        f"Context:\n{context}\n\n"
        "Review and provide an ExecutiveSummary with recommended actions."
    )
    result = await get_executive_agent().run(prompt)
    summary: ExecutiveSummary = result.output
    return {
        "executive_summary": summary.model_dump(),
        "messages": result.all_messages(),
    }


async def update_pegging_node(state: ASCPState) -> dict:
    """Write PlanningDecision allocations to era.ascp.pegging.ledger."""
    decision = state.get("planning_decision") or {}
    updates = decision.get("pegging_updates", [])
    cycle_id = state["cycle_id"]

    for upd in updates:
        _planning.update_allocation(
            pegging_id=upd["pegging_id"],
            allocated_qty=upd["allocated_qty"],
            status=upd.get("status", "firm"),
            ai_context=f"Cycle {cycle_id}: auto-allocation by Planning Manager",
            cycle_id=cycle_id,
        )

    return {}


async def notify_node(state: ASCPState) -> dict:
    """Post a cycle summary to key Odoo records via ascp_post_comment."""
    cycle_id = state["cycle_id"]
    purchase_logs = state.get("purchase_analysis_logs", [])
    director_decision = state.get("director_decision") or {}

    # Build one narrative summary
    lines = [f"Planning cycle {cycle_id} complete."]

    planning_decision = state.get("planning_decision") or {}
    lines.append(f"Planning action: {planning_decision.get('action', 'n/a')}")
    lines.append(f"Shortages found: {len(state.get('shortages', []))}")

    if director_decision:
        lines.append(
            f"Purchase outcome: {director_decision.get('action', 'n/a')} "
            f"(confirmed POs: {director_decision.get('confirmed_po_ids', [])})"
        )

    if purchase_logs:
        lines.append("Purchase analysis log:")
        lines.extend(f"  {log}" for log in purchase_logs[-5:])  # last 5 entries

    summary_text = "\n".join(lines)

    # Post to all affected pegging ledger records
    ledger = state.get("pegging_ledger", [])
    posted_ids: list[int] = []
    for record in ledger[:10]:  # cap at 10 to avoid flooding
        record_id = record.get("id")
        if record_id:
            _comms.post_ai_reasoning(
                model="era.ascp.pegging.ledger",
                record_id=record_id,
                action_taken=f"Cycle {cycle_id} completed",
                ai_context=summary_text,
                cycle_id=cycle_id,
            )
            posted_ids.append(record_id)

    return {}


# ── Build main graph ──────────────────────────────────────────────────────────

def build_workflow() -> Any:
    """Compile and return the main ASCP workflow graph."""
    graph = StateGraph(ASCPState)

    # Register nodes
    graph.add_node("sync_demand", sync_demand_node)
    graph.add_node("sync_supply", sync_supply_node)
    graph.add_node("planning_manager", planning_manager_node)
    graph.add_node("supervisor", supervisor_node)       # pure router — not async
    graph.add_node("purchase_cluster", purchase_cluster_node)
    graph.add_node("hitl_checkpoint", hitl_checkpoint_node)
    graph.add_node("executive_node", executive_node)
    graph.add_node("update_pegging", update_pegging_node)
    graph.add_node("notify", notify_node)

    # Fixed edges
    graph.add_edge(START, "sync_demand")
    graph.add_edge("sync_demand", "sync_supply")
    graph.add_edge("sync_supply", "planning_manager")
    graph.add_edge("planning_manager", "supervisor")

    # Supervisor conditional routing
    graph.add_conditional_edges(
        "supervisor",
        supervisor_node,
        {
            "purchase_cluster": "purchase_cluster",
            "hitl_checkpoint": "hitl_checkpoint",
            "executive_node": "executive_node",
            "update_pegging": "update_pegging",
        },
    )

    # All paths converge at update_pegging → notify → END
    graph.add_edge("purchase_cluster", "update_pegging")
    graph.add_edge("hitl_checkpoint", "update_pegging")   # resumes here after HITL
    graph.add_edge("executive_node", "update_pegging")
    graph.add_edge("update_pegging", "notify")
    graph.add_edge("notify", END)

    return graph.compile()


# Module-level compiled workflow (import and use this)
ascp_workflow = build_workflow()
