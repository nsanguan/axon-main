# Scenario: Stock Check with External Purchase — Supervisor + Draft-Only

## File: `escalation_stock_check.md`
## Type: Escalation / Warehouse Shortage
## Severity: Medium (Manager-level resolution, Draft-Only PO)

---

### Given (Context)

A store-level stock check request for **WH01 / Store KB-001**. The warehouse agent finds **zero on-hand stock** for 3 SKUs (SKU-A, SKU-B, SKU-C) and the main warehouse is also depleted.

**Setup:**
- **MCP Agent Store**: `get_stock_onhand(wh="WH01", store="KB-001")` returns onhand=0, min_stock=50
- **MCP Agent Store**: `get_stock_onhand(wh="MAIN", store="KB-001")` returns onhand=0 (main WH also empty)
- **MCP Agent Buyer**: `get_supplier_list(items=["SKU-A","SKU-B","SKU-C"])` returns SUP-01 (Global Parts)
- **MCP Agent Buyer**: `get_price_quote(supplier="SUP-01", items=[...])` returns prices + 45,000 THB total
- **MCP RAG**: SOP says *"When on-hand = 0 and main WH depleted, external purchase is required. Draft PO must be approved by manager before submission."*

### When (Trigger)

**User request**: "ตรวจสอบ Stock WH01 Store KB-001 ต้องเพิ่มอะไร" (Check stock at WH01 KB-001, what needs to be reordered?)

**Executive Intent Router** classifies:
- `intent_id`: "stock_check_and_suggest_reorder"
- `entities`: {"wh": "WH01", "store": "KB-001"}
- `confidence`: 0.95

### Then (Expected Orchestrator Behavior)

**Step 1 — EXECUTIVE: Intent Classification**
- Executive Agent's Intent Router classifies the request
- Routes to `stock_check_reorder_flow`
- Entities passed to state: `{wh: "WH01", store: "KB-001"}`
- No HITL needed (routing only)

**Step 2 — SUPERVISOR: Dispatch**
- Supervisor reads state → detects `demands` exist (stock check request)
- Dispatches **WhereHouseAgent** (Manager: Warehouse specialist)
- `Command(goto="where_house_node", update={...})`
- Safety check: `agent_call_count = 1 < MAX_SUPERVISOR_ROUNDS = 6`

**Step 3 — MANAGER: WhereHouseAgent — Stock Check**
- Calls MCP: `mcp_agent_store.get_inventory_levels({location: "WH01", store: "KB-001"})`
- Returns: `{onhand: 0, min_stock: 50, items_below_min: ["SKU-A","SKU-B","SKU-C"], main_wh_onhand: 0}`
- Sets `_next_action = "external_purchase_required"` (3-branch logic)
- Reports back to Supervisor

**Step 4 — SUPERVISOR: Conditional Branch**
- Reads `_next_action == "external_purchase_required"`
- **Draft-Only Mandate**: Since external purchase is required, dispatches BuyerAgent
- `Command(goto="buyer_node", update={shortage_items: ["SKU-A","SKU-B","SKU-C"], source: "external_purchase_required"})`

**Step 5 — MANAGER: BuyerAgent — Draft PO**
- Calls MCP buyer tools:
  - `mcp_agent_buyer.get_suppliers({items: ["SKU-A","SKU-B","SKU-C"]})` → selects best supplier
  - `mcp_agent_buyer.get_item_costs({supplier: "SUP-01", items: [...]})` → gets pricing
- Creates **draft** purchase order: `draft_purchase_order(supplier="SUP-01", items=[...], qty=[50,60,40])`
- Returns: `{po_draft_id: "PO-DRAFT-2026-001", total_cost_thb: 45000, requires_approval: true}`
- **Draft-Only**: Does NOT call `submit_purchase_order()` — only `draft_purchase_order()`

**Step 6 — RESPONSE: Summary to User**
- Synthesizes results:
  ```
  Stock WH01 / Store KB-001: EMPTY (main WH also depleted)
  Recommended: Purchase 3 items from Global Parts Co., Ltd.
  Total: 45,000 THB
  Lead time: 5 days
  Action needed: Human approval to submit PO PO-DRAFT-2026-001
  ```

---

### Escalation Audit Trail

| Level | Agent | Action | Duration |
|-------|-------|--------|----------|
| EXECUTIVE | intent_router | Classified: stock_check_reorder | ~500ms |
| SUPERVISOR | supervisor_node | Dispatched WhereHouseAgent | ~100ms |
| MANAGER | where_house_node | Stock check: 0 onhand, external purchase | ~2s (MCP call) |
| SUPERVISOR | supervisor_node | Branch: external purchase → BuyerAgent | ~100ms |
| MANAGER | buyer_node | Draft PO: 3 items, 45,000 THB | ~3s (MCP calls) |
| HUMAN | planning_manager | **Pending**: approve PO draft? | — |

### Draft-Only Mandate Verified

| Step | Tool Called | Action | Human Required? |
|------|------------|--------|---------------- |
| 5a | `get_suppliers` | READ | ❌ No |
| 5b | `get_item_costs` | READ | ❌ No |
| 5c | `draft_purchase_order` | **DRAFT** | ❌ No (AI creates draft) |
| 6 | `submit_purchase_order` | **SUBMIT** | ✅ YES (human only) |

### Golden Rules Verified

| Rule | Status | Evidence |
|------|--------|----------|
| No Mesh Coupling | ✅ | WhereHouseAgent → Supervisor → BuyerAgent (hub-and-spoke) |
| Draft-Only Mandate | ✅ | BuyerAgent only drafts; human submits |
| Node → Subgraph | ✅ | Each agent is a simple `async def` (could upgrade to subgraph) |

### HITL Decision

```
Decision: Pending human approval for PO PO-DRAFT-2026-001
Escalation Level: MANAGER (score ~75K, below EXECUTIVE threshold)
No Executive HITL required — standard procurement workflow
```
