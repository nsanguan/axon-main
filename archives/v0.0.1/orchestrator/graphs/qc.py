"""
orchestrator.graphs.qc — Quality Control sub-graph.

Flowchart:
  [START] -> [qc_inspection] -> {ng_found?}
      yes -> [lock_and_rework] -> [END]
      no  -> [END]

The QC Inspection Agent detects NG items, locks stock, and injects rework demand.
"""

from __future__ import annotations

import json
from typing import Any

from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict


class QCState(TypedDict):
    cycle_id: str
    ng_items: list[dict]
    rework_orders: list[dict]
    messages: list


async def qc_inspection_node(state: QCState) -> dict:
    """Run the QC Inspection Agent to detect NG items and lock stock."""
    from agents.qc.inspection import get_axon_qc_agent
    from core.schema.quality import AxonNGItem

    cycle_id = state["cycle_id"]
    prompt = (
        f"Planning cycle: {cycle_id}\n\n"
        "Scan all open quality inspections for NG (non-conforming) items. "
        "For each NG item: lock the affected stock and create a rework demand. "
        "Return the list of AxonNGItem records."
    )

    result = await get_axon_qc_agent().run(prompt)
    ng_items: list[AxonNGItem] = result.output

    return {
        "ng_items": [item.model_dump() for item in ng_items],
        "messages": result.all_messages(),
    }


def _ng_found_route(state: QCState) -> str:
    """Route to rework extraction if any NG items were found."""
    return "extract_rework_orders" if state.get("ng_items") else END


async def extract_rework_orders_node(state: QCState) -> dict:
    """Extract rework_order_id fields from ng_items into rework_orders list."""
    rework_orders = []
    for ng in state.get("ng_items", []):
        rwo_id = ng.get("rework_order_id")
        if rwo_id:
            rework_orders.append({"rework_order_id": rwo_id, "ng_ref": ng.get("id")})
    return {"rework_orders": rework_orders}


def build_qc_subgraph() -> Any:
    graph = StateGraph(QCState)
    graph.add_node("qc_inspection", qc_inspection_node)
    graph.add_node("extract_rework_orders", extract_rework_orders_node)

    graph.add_edge(START, "qc_inspection")
    graph.add_conditional_edges(
        "qc_inspection",
        _ng_found_route,
        {"extract_rework_orders": "extract_rework_orders", END: END},
    )
    graph.add_edge("extract_rework_orders", END)

    return graph.compile()


axon_qc_subgraph = build_qc_subgraph()
