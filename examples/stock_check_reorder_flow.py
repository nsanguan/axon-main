"""stock_check_reorder_flow — Example workflow from Escalate_Tech walkthrough.

Flow (mirrors agent_roles_and_flow_walkthrough.html):
  User: "ตรวจสอบ Stock WH01 Store KB-001 ต้องเพิ่มอะไร"

  1. Executive Agent (Intent Router)
     → classifies: intent="stock_check_and_suggest_reorder"
     → entities: {wh: "WH01", store: "KB-001"}

  2. Supervisor → dispatches WhereHouseAgent

  3. WhereHouseAgent (Manager: Warehouse expert)
     → MCP: get_stock_onhand(wh="WH01", store="KB-001")
     → result: {onhand: 0, min_stock: 50, items_below_min: ["SKU-A",...]}

  4. Supervisor — conditional branch:
     - onhand > min → END (report only)
     - 0 < onhand < min → replenish from Main WH
     - onhand == 0 + Main WH empty → BuyerAgent (this path)

  5. BuyerAgent (Manager: Procurement expert)
     → MCP: get_supplier_list(items), get_price_quote(supplier, items)
     → result: {supplier: "SUP-01", total_cost: 45000, po_draft_id: "PO-DRAFT-001"}

  6. Response → summary to user
     → "Stock WH01/KB-001: empty. Recommend purchase 3 items from SUP-01, 45,000 THB."

Key design rules from Escalate_Tech:
  - No Mesh Coupling: Agents never call each other directly
  - Draft-Only Mandate: BuyerAgent uses draft_purchase_order() only.
    Final submit_purchase_order() requires human approval.
  - HITL: PO requires human confirmation before submission.
"""

from __future__ import annotations

from typing import Any

from axon.core.telemetry import log_event
from axon.orchestrator.supervisor import supervisor_dispatch

# =============================================================================
# Mock MCP responses for this flow
# =============================================================================

MOCK_STOCK_CHECK_RESPONSE = {
    "wh": "WH01",
    "store": "KB-001",
    "onhand": 0,
    "min_stock": 50,
    "max_stock": 200,
    "items_below_min": ["SKU-A", "SKU-B", "SKU-C"],
    "main_wh_onhand": 0,  # Main warehouse also empty
    "shortage_detected": True,
    "replenish_from_main_wh": False,
}

MOCK_PURCHASE_SUGGESTION = {
    "supplier": "SUP-01",
    "supplier_name": "Global Parts Co., Ltd.",
    "items": ["SKU-A", "SKU-B", "SKU-C"],
    "quantities": {"SKU-A": 50, "SKU-B": 60, "SKU-C": 40},
    "unit_prices": {"SKU-A": 120.0, "SKU-B": 250.0, "SKU-C": 180.0},
    "total_cost_thb": 45000.0,
    "lead_time_days": 5,
    "po_draft_id": "PO-DRAFT-2026-001",
    "requires_approval": True,
    "summary": "Emergency restock for WH01/KB-001 — 3 items, 45,000 THB, 5d lead time",
}


# =============================================================================
# Stock Check Node (WhereHouseAgent)
# =============================================================================


async def where_house_node(state: dict[str, Any]) -> dict[str, Any]:
    """WhereHouseAgent — Manager-level specialist for warehouse ops.

    In production: calls MCP tools to check stock.
    In this example: returns mock data.

    Escalate_Tech rule: Managers are single-purpose specialists.
    They do NOT know about other agents — only their domain.
    """
    log_event("info", "where_house_check", state=state.get("entities", {}))

    # In production: result = await mcp_client.call("get_stock_onhand", **entities)
    result = MOCK_STOCK_CHECK_RESPONSE

    state["stock_result"] = result

    # Determine next action based on stock level (3-branch logic)
    if result["onhand"] > result["min_stock"]:
        next_action = "report_only"
    elif result["onhand"] > 0:
        next_action = "replenish_from_main_wh"
    else:
        # onhand == 0 and main WH also empty → need external purchase
        next_action = "external_purchase_required"

    state["_next_action"] = next_action

    log_event(
        "info",
        "where_house_result",
        onhand=result["onhand"],
        min_stock=result["min_stock"],
        next_action=next_action,
    )

    return {
        "stock_result": result,
        "_next_action": next_action,
    }


# =============================================================================
# Purchase Suggestion Node (BuyerAgent)
# =============================================================================


async def buyer_node(state: dict[str, Any]) -> dict[str, Any]:
    """BuyerAgent — Manager-level specialist for procurement.

    Draft-Only Mandate (from Escalate_Tech spec):
      BuyerAgent uses draft_purchase_order() to create a PO draft.
      Only a human can call submit_purchase_order() to finalize.
      This ensures the AI remains a recommender, not a financial authority.
    """
    log_event("info", "buyer_create_draft", stock=state.get("stock_result", {}))

    # In production: calls MCP buyer tools
    #   result = await mcp_client.call("get_supplier_list", items)
    #   result = await mcp_client.call("get_price_quote", supplier, items)
    #   result = await mcp_client.call("draft_purchase_order", supplier, items, qty)
    result = MOCK_PURCHASE_SUGGESTION

    state["purchase_suggestion"] = result
    state["_po_draft_id"] = result["po_draft_id"]
    state["_requires_human_approval"] = result["requires_approval"]

    log_event(
        "info",
        "buyer_draft_created",
        po_draft_id=result["po_draft_id"],
        total_cost=result["total_cost_thb"],
        supplier=result["supplier"],
    )

    return {
        "purchase_suggestion": result,
        "_po_draft_id": result["po_draft_id"],
        "_requires_human_approval": result["requires_approval"],
    }


# =============================================================================
# Flow runner — simulates the full walkthrough
# =============================================================================


async def run_stock_check_flow():
    """Simulate the full stock_check_reorder_flow from the HTML walkthrough."""
    print("=" * 60)
    print("  STOCK CHECK REORDER FLOW")
    print("  User: ตรวจสอบ Stock WH01 Store KB-001 ต้องเพิ่มอะไร")
    print("=" * 60)

    # Step 0: Initial state
    state = {
        "entities": {"wh": "WH01", "store": "KB-001"},
        "stock_result": None,
        "purchase_suggestion": None,
        "_supervisor_consulted": [],
        "_supervisor_round": 0,
        "_next_action": None,
    }

    # Step 1: Executive would classify intent here
    print("\n[Executive] Intent: stock_check_and_suggest_reorder")
    print(f"  Entities: {state['entities']}")

    # Step 2: Supervisor dispatches WhereHouseAgent
    print("\n[Supervisor] → dispatching where_house_agent")
    target, updates = supervisor_dispatch({"demands": [{"item": "FG-001"}]}, 0)
    print(f"  Target: {target}")
    state.update(updates)

    # Step 3: WhereHouseAgent checks stock
    print("\n[WhereHouseAgent] Checking stock WH01/KB-001...")
    result = await where_house_node(state)
    state.update(result)
    print(f"  On-hand: {state['stock_result']['onhand']}")
    print(f"  Min stock: {state['stock_result']['min_stock']}")
    print(f"  Items below min: {state['stock_result']['items_below_min']}")
    print(f"  Next action: {state['_next_action']}")

    # Step 4: Supervisor conditional branch
    print(f"\n[Supervisor] Conditional branch: {state['_next_action']}")
    if state["_next_action"] == "external_purchase_required":
        print("  → Routing to BuyerAgent (external purchase needed)")

        # Step 5: BuyerAgent creates draft PO
        print("\n[BuyerAgent] Creating purchase suggestion...")
        po_result = await buyer_node(state)
        state.update(po_result)
        po = state["purchase_suggestion"]
        print(f"  Supplier: {po['supplier']} ({po['supplier_name']})")
        print(f"  Items: {len(po['items'])} SKUs")
        print(f"  Total cost: {po['total_cost_thb']:,.0f} THB")
        print(f"  PO Draft ID: {po['po_draft_id']}")
        print(f"  Lead time: {po['lead_time_days']} days")
        print("  Draft-Only: YES — requires human approval before submission")

        # Step 6: Final response
        print("\n[Response] Summary to user:")
        print("  Stock WH01 / Store KB-001: EMPTY (main WH also depleted)")
        print(f"  Recommended: Purchase {len(po['items'])} items from {po['supplier_name']}")
        print(f"  Total: {po['total_cost_thb']:,.0f} THB")
        print(f"  Lead time: {po['lead_time_days']} days")
        print(f"  Action needed: Human approval to submit PO {po['po_draft_id']}")
    else:
        print("  → No external purchase needed")

    print(f"\n{'='*60}")
    print(f"  FLOW COMPLETE — {len(state.get('_supervisor_consulted', []))} agent(s) consulted")
    print(f"{'='*60}")

    return state


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_stock_check_flow())
