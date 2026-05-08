"""
Main LangGraph workflow — Axon ASCP Planning Cycle.

Flowchart (matches design TD):

[START] -> [executive_entry] -> [sync_demand] -> [sync_supply]
        -> [planning_manager] -> {supervisor_route}
            shortage -> [purchase_cluster] -> [update_pegging]
            hitl -> [hitl_checkpoint] -> [update_pegging]
            low_conf -> [executive_escalation] -> [update_pegging]
            allocate -> [update_pegging]
        [update_pegging] -> [notify] -> [END]
"""

from __future__ import annotations

import json
import uuid
from datetime import date
from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

from agents.supervisor import supervisor_route
from core.skills.communication_skills import AxonCommunicationSkills
from core.skills.planning_skills import AxonPlanningSkills
from core.skills.procurement_skills import AxonProcurementSkills
from core.skills.inventory_skills import AxonInventorySkills
from orchestrator.graphs.production import ProdState, axon_production_subgraph
from orchestrator.graphs.purchase import AxonPurchaseState, axon_purchase_subgraph
from orchestrator.graphs.qc import QCState, axon_qc_subgraph
from orchestrator.state import AxonState

# Skill singletons
_planning = AxonPlanningSkills()
_comms = AxonCommunicationSkills()
_procurement = AxonProcurementSkills()
_inventory = AxonInventorySkills()


def _new_cycle_id() -> str:
    today = date.today().isoformat()
    return f"CYCLE-{today}-{uuid.uuid4().hex[:6].upper()}"


async def executive_entry_node(state: AxonState) -> dict:
    """Executive Entry Node: interprets user strategy at cycle start."""
    from agents.executive import get_axon_executive_entry_agent, AxonExecutiveDirective

    cycle_id = state.get("cycle_id") or _new_cycle_id()
    user_strategy = (
        state.get("user_strategy")
        or "Balanced planning cycle — maintain service level while controlling cost."
    )

    prompt = (
        "Planning cycle: " + cycle_id + "\n"
        "User strategy & policy:\n" + user_strategy + "\n\n"
        "Use axon_get_ledger and axon_check_shortage to understand the current "
        "state, then produce an AxonExecutiveDirective with thresholds and "
        "priority products for this cycle."
    )

    result = await get_axon_executive_entry_agent().run(prompt)
    directive: AxonExecutiveDirective = result.output

    return {
        "cycle_id": cycle_id,
        "executive_directive": directive.model_dump(),
        "messages": result.all_messages(),
    }


async def sync_demand_node(state: AxonState) -> dict:
    """Pull confirmed sale orders into the demand buffer via the planning adapter."""
    cycle_id = state.get("cycle_id") or _new_cycle_id()
    _planning.sync_demand_from_so(
        ai_context=f"Planning cycle {cycle_id}: syncing demand from confirmed SOs",
        cycle_id=cycle_id,
    )
    demand_stream = _planning.get_demand_stream(
        state_filter=["open", "pegged"],
        limit=500,
    )
    return {"cycle_id": cycle_id, "demand_stream": demand_stream}


async def sync_supply_node(state: AxonState) -> dict:
    """Snapshot supply and pegging ledger for the current cycle."""
    supply_stream = _planning.get_supply_stream(limit=500)
    pegging_ledger = _planning.get_ledger(
        status_filter=["draft", "firm", "partial"],
        limit=500,
    )
    return {"supply_stream": supply_stream, "pegging_ledger": pegging_ledger}


async def planning_manager_node(state: AxonState) -> dict:
    """Planning Manager Agent: analyses demand vs supply, detects shortages."""
    from agents.planning import get_axon_planning_agent, AxonPlanningDecision

    directive = state.get("executive_directive") or {}
    demand_json = json.dumps(state.get("demand_stream", [])[:50], ensure_ascii=False, default=str)
    ledger_json = json.dumps(state.get("pegging_ledger", [])[:50], ensure_ascii=False, default=str)

    directive_context = ""
    if directive:
        directive_context = (
            "Executive directive:\n"
            "  objective: " + str(directive.get("cycle_objective", "balance")) + "\n"
            "  priority_products: " + str(directive.get("priority_products", [])) + "\n"
            "  cost_tolerance_pct: " + str(directive.get("cost_tolerance_pct", 10)) + "\n"
            "  lead_tolerance_days: " + str(directive.get("lead_tolerance_days", 14)) + "\n\n"
        )

    prompt = (
        "Planning cycle: " + state["cycle_id"] + "\n"
        + directive_context
        + "Demand stream (first 50):\n" + demand_json + "\n\n"
        + "Pegging ledger (first 50):\n" + ledger_json + "\n\n"
        "Analyse demand vs supply, detect shortages, and return AxonPlanningDecision."
    )

    result = await get_axon_planning_agent().run(prompt)
    decision: AxonPlanningDecision = result.output

    return {
        "planning_decision": decision.model_dump(),
        "shortages": [s.model_dump() for s in decision.shortages],
        "hitl_activity_ids": decision.hitl_activity_ids,
        "messages": result.all_messages(),
    }


async def purchase_cluster_node(state: AxonState) -> dict:
    """Runs the compiled Purchase sub-graph and merges results back into AxonState."""
    purchase_input: AxonPurchaseState = {
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

    final_state: AxonPurchaseState = await axon_purchase_subgraph.ainvoke(purchase_input)

    return {
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


def hitl_checkpoint_node(state: AxonState) -> dict:
    """Pause for Planning-level HITL (e.g. date-slip exception)."""
    interrupt(
        {
            "reason": "Planning Manager requested human approval",
            "hitl_activity_ids": state.get("hitl_activity_ids", []),
            "cycle_id": state["cycle_id"],
        }
    )
    return {}


async def executive_escalation_node(state: AxonState) -> dict:
    """Executive Escalation Node: called when Planning Manager confidence < 0.7."""
    from agents.executive import get_axon_executive_agent, AxonExecutiveSummary

    context = json.dumps(
        {
            "planning_decision": state.get("planning_decision"),
            "shortages": state.get("shortages", []),
            "executive_directive": state.get("executive_directive"),
            "cycle_id": state["cycle_id"],
        },
        ensure_ascii=False,
        default=str,
    )
    prompt = (
        "Low-confidence planning decision for cycle " + state["cycle_id"] + ". "
        "Context:\n" + context + "\n\n"
        "Review and provide an AxonExecutiveSummary with recommended actions."
    )
    result = await get_axon_executive_agent().run(prompt)
    summary: AxonExecutiveSummary = result.output
    return {
        "executive_summary": summary.model_dump(),
        "messages": result.all_messages(),
    }


async def update_pegging_node(state: AxonState) -> dict:
    """Write AxonPlanningDecision allocations back to the ERP."""
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


async def notify_node(state: AxonState) -> dict:
    """Post a cycle-completion summary to the ERP audit trail."""
    cycle_id = state["cycle_id"]
    purchase_logs = state.get("purchase_analysis_logs", [])
    director_decision = state.get("director_decision") or {}

    lines = [f"Planning cycle {cycle_id} complete."]
    planning_decision = state.get("planning_decision") or {}
    lines.append(f"Planning action: {planning_decision.get('action', 'n/a')}")
    lines.append(f"Shortages found: {len(state.get('shortages', []))}")

    if director_decision:
        lines.append(
            f"Purchase outcome: {director_decision.get('action', 'n/a')} "
            f"(confirmed POs: {director_decision.get('confirmed_po_ids', [])})",
        )

    if purchase_logs:
        lines.append("Purchase analysis log:")
        lines.extend(f"  {log}" for log in purchase_logs[-5:])

    summary_text = "\n".join(lines)

    ledger = state.get("pegging_ledger", [])
    for record in ledger[:10]:
        record_id = record.get("id")
        if record_id:
            _planning.log_cycle_summary(
                record_id=record_id,
                cycle_id=cycle_id,
                summary_text=summary_text,
            )
    return {}


async def sync_constraints_node(state: AxonState) -> dict:
    """Poll Maintenance MCP for active breakdowns/PM constraints."""
    from agents.maintenance.breakdown_response import get_axon_breakdown_agent
    from core.schema.maintenance import AxonMaintenanceConstraint

    cycle_id = state.get("cycle_id", "")
    prompt = (
        f"Planning cycle: {cycle_id}\n\n"
        "Check for any active breakdowns or upcoming PM orders that will block "
        "work centre capacity. Return an AxonMaintenanceConstraint."
    )
    result = await get_axon_breakdown_agent().run(prompt)
    constraint: AxonMaintenanceConstraint = result.output
    constraints = [constraint.model_dump()] if constraint.requires_reschedule else []
    return {
        "maintenance_constraints": constraints,
        "messages": result.all_messages(),
    }


async def sync_bom_changes_node(state: AxonState) -> dict:
    """Poll PD MCP for BOM changes since the last planning cycle."""
    from agents.pd.bom_impact import get_axon_bom_impact_agent
    from core.schema.production import AxonBOMChange

    cycle_id = state.get("cycle_id", "")
    prompt = (
        f"Planning cycle: {cycle_id}\n\n"
        "Detect any BOM changes since the last planning cycle. "
        "Return an AxonBOMChange with requires_replan and affected_mo_ids."
    )
    result = await get_axon_bom_impact_agent().run(prompt)
    change: AxonBOMChange = result.output
    changes = [change.model_dump()] if change.requires_replan else []
    return {
        "bom_changes": changes,
        "messages": result.all_messages(),
    }


async def sync_qc_node(state: AxonState) -> dict:
    """Run QC sub-graph: detect NG items, lock stock, inject rework demand."""
    qc_input: QCState = {
        "cycle_id": state["cycle_id"],
        "ng_items": [],
        "rework_orders": [],
        "messages": [],
    }
    final_state: QCState = await axon_qc_subgraph.ainvoke(qc_input)
    return {
        "ng_items": final_state.get("ng_items", []),
        "rework_orders": final_state.get("rework_orders", []),
        "messages": final_state.get("messages", []),
    }


async def production_planning_node(state: AxonState) -> dict:
    """Run the Production Planning sub-graph (MPS + optional reschedule)."""
    prod_input: ProdState = {
        "cycle_id": state["cycle_id"],
        "maintenance_constraints": state.get("maintenance_constraints", []),
        "bom_changes": state.get("bom_changes", []),
        "production_schedule": None,
        "needs_reschedule": False,
        "messages": [],
    }
    final_state: ProdState = await axon_production_subgraph.ainvoke(prod_input)
    return {
        "production_schedule": final_state.get("production_schedule"),
        "messages": final_state.get("messages", []),
    }


def qa_compliance_checkpoint_node(state: AxonState) -> dict:
    """QA compliance guardrail — interrupts if a violation requires human review."""
    compliance = state.get("compliance_decision") or {}
    if compliance.get("requires_human_review"):
        interrupt(
            {
                "reason": "QA compliance violation requires human review",
                "compliance_decision": compliance,
                "human_review_activity_id": compliance.get("human_review_activity_id"),
                "cycle_id": state["cycle_id"],
            }
        )
    return {}


def finance_budget_checkpoint_node(state: AxonState) -> dict:
    """Finance budget guardrail — interrupts if CFO review is required."""
    budget = state.get("budget_validation") or {}
    if budget.get("requires_cfo_review"):
        interrupt(
            {
                "reason": "Budget validation requires CFO review",
                "budget_validation": budget,
                "cfo_review_activity_id": budget.get("cfo_review_activity_id"),
                "cycle_id": state["cycle_id"],
            }
        )
    return {}


def build_axon_workflow() -> Any:
    graph = StateGraph(AxonState)

    graph.add_node("executive_entry", executive_entry_node)
    graph.add_node("sync_demand", sync_demand_node)
    graph.add_node("sync_supply", sync_supply_node)
    graph.add_node("sync_constraints", sync_constraints_node)
    graph.add_node("sync_bom_changes", sync_bom_changes_node)
    graph.add_node("sync_qc", sync_qc_node)
    graph.add_node("production_planning", production_planning_node)
    graph.add_node("qa_compliance_checkpoint", qa_compliance_checkpoint_node)
    graph.add_node("finance_budget_checkpoint", finance_budget_checkpoint_node)
    graph.add_node("planning_manager", planning_manager_node)
    graph.add_node("purchase_cluster", purchase_cluster_node)
    graph.add_node("hitl_checkpoint", hitl_checkpoint_node)
    graph.add_node("executive_escalation", executive_escalation_node)
    graph.add_node("update_pegging", update_pegging_node)
    graph.add_node("notify", notify_node)

    graph.add_edge(START, "executive_entry")
    graph.add_edge("executive_entry", "sync_demand")
    graph.add_edge("sync_demand", "sync_supply")
    # Constraint polling runs in parallel-ish sequence before planning
    graph.add_edge("sync_supply", "sync_constraints")
    graph.add_edge("sync_constraints", "sync_bom_changes")
    graph.add_edge("sync_bom_changes", "sync_qc")
    graph.add_edge("sync_qc", "production_planning")
    graph.add_edge("production_planning", "planning_manager")

    graph.add_conditional_edges(
        "planning_manager",
        supervisor_route,
        {
            "purchase_cluster": "purchase_cluster",
            "hitl_checkpoint": "hitl_checkpoint",
            "executive_escalation": "executive_escalation",
            "qa_compliance_checkpoint": "qa_compliance_checkpoint",
        },
    )

    graph.add_edge("purchase_cluster", "qa_compliance_checkpoint")
    graph.add_edge("hitl_checkpoint", "qa_compliance_checkpoint")
    graph.add_edge("executive_escalation", "qa_compliance_checkpoint")
    graph.add_edge("qa_compliance_checkpoint", "finance_budget_checkpoint")
    graph.add_edge("finance_budget_checkpoint", "update_pegging")
    graph.add_edge("update_pegging", "notify")
    graph.add_edge("notify", END)

    return graph.compile()


# Module-level compiled workflow
axon_workflow = build_axon_workflow()
