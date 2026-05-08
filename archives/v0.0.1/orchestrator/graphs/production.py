"""
orchestrator.graphs.production — Production Planning sub-graph.

Flowchart:
  [START] -> [sync_constraints] -> [bom_impact] -> [mps] -> {needs_reschedule?}
      yes -> [reschedule] -> [END]
      no  -> [END]

The sub-graph reads maintenance_constraints and bom_changes from the parent
AxonState (passed in as ProdState), runs the MPS Agent, and if rescheduling
is needed runs the Reschedule Agent.
"""

from __future__ import annotations

import json
from typing import Any

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict


class ProdState(TypedDict):
    cycle_id: str
    maintenance_constraints: list[dict]
    bom_changes: list[dict]
    production_schedule: dict | None
    needs_reschedule: bool
    messages: list


async def mps_node(state: ProdState) -> dict:
    """Run the MPS Agent to generate/update the Master Production Schedule."""
    from agents.production.mps import get_axon_mps_agent
    from core.schema.production import AxonMPS

    maintenance_json = json.dumps(state.get("maintenance_constraints", []), default=str)
    bom_json = json.dumps(state.get("bom_changes", []), default=str)
    cycle_id = state["cycle_id"]

    prompt = (
        f"Planning cycle: {cycle_id}\n"
        f"Maintenance constraints: {maintenance_json}\n"
        f"BOM changes: {bom_json}\n\n"
        "Generate or update the Master Production Schedule (MPS). "
        "Respect all maintenance-blocked work centres and BOM change impacts."
    )

    result = await get_axon_mps_agent().run(prompt)
    schedule: AxonMPS = result.output

    needs_reschedule = schedule.action in ("reschedule", "hitl_required")

    return {
        "production_schedule": schedule.model_dump(),
        "needs_reschedule": needs_reschedule,
        "messages": result.all_messages(),
    }


async def reschedule_node(state: ProdState) -> dict:
    """Run the Rescheduling Agent to apply a new shop-floor sequence."""
    from agents.production.reschedule import get_axon_reschedule_agent
    from core.schema.production import AxonSequencing

    maintenance_json = json.dumps(state.get("maintenance_constraints", []), default=str)
    schedule_json = json.dumps(state.get("production_schedule", {}), default=str)
    cycle_id = state["cycle_id"]

    prompt = (
        f"Planning cycle: {cycle_id}\n"
        f"Current MPS: {schedule_json}\n"
        f"Maintenance constraints: {maintenance_json}\n\n"
        "Reschedule all affected work orders. Do not use blocked work centres."
    )

    result = await get_axon_reschedule_agent().run(prompt)
    sequencing: AxonSequencing = result.output

    return {
        "production_schedule": {
            **(state.get("production_schedule") or {}),
            "sequencing": sequencing.model_dump(),
        },
        "messages": result.all_messages(),
    }


def _reschedule_route(state: ProdState) -> str:
    return "reschedule" if state.get("needs_reschedule") else END


def build_production_subgraph() -> Any:
    graph = StateGraph(ProdState)
    graph.add_node("mps", mps_node)
    graph.add_node("reschedule", reschedule_node)

    graph.add_edge(START, "mps")
    graph.add_conditional_edges(
        "mps",
        _reschedule_route,
        {"reschedule": "reschedule", END: END},
    )
    graph.add_edge("reschedule", END)

    return graph.compile()


axon_production_subgraph = build_production_subgraph()
