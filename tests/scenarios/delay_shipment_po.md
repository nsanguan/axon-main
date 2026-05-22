# Scenario: Raw Material Delay (PO Delay)

## File: `delay_shipment_po.md`
## Type: Procurement / Supply Delay
## Severity: Critical (VIP order impacted + delay > 7 days)

---

### Given (Context)

A procurement delay notification of **14 days** for Microchip XC-7742 (PO #78990).

**Setup:**
- **MCP Oracle EBS**: Returns 50,000 units on PO, 2,000 on-hand (safety stock is 10,000).
- **MCP RAG**: SOP says *"Air-freight is allowed for critical components when customer priority > 80."*
- **Sales Orders**: One VIP order (DataCorp, P=95, $250K revenue) requires FG-003 which uses 4x chips per board.
- **WIP**: 500 boards in progress (WIP-20245), needs 2,000 chips to complete.
- **Alternative supplier**: ChipLink GmbH (LT=14d, $1.95/unit, 96% reliability).

### When (Trigger)

The **Buyer/Procurement Agent** receives an automated alert and calls the orchestrator.

### Then (Expected Orchestrator Behavior)

**Step 1 — TRIGGER ANALYSIS**
- Must call `oracle_ebs.get_purchase_orders({po_number: "PO-78990"})`
- Confirm: item = Microchip XC-7742, delay = 14 days, reason = port congestion

**Step 2 — IMPACT ASSESSMENT**
- Must call `mcp_agent_store.get_inventory_levels({item_id: "RM-099"})`
- Must call `oracle_ebs.get_bom({item_id: "FG-003"})` to confirm dependency
- Must call `oracle_ebs.list_wip_jobs({item_id: "FG-003"})` to check production impact
- Must call `mcp_agent_store.get_sales_orders({})` to find at-risk orders
- Must call `llmwiki.get_sop({process_code: "supply_chain.delay_handling"})`
- Must calculate: revenue at risk = $250,000 (DataCorp), boards blocked = 500

**Step 3 — SOLUTION GENERATION**
- Must generate at least **2 solutions**:

| Option | Description | Cost | SLA | Utility |
|--------|------------|------|-----|---------|
| **A** | Keep sea freight, delay production, notify DataCorp | ~$3,500 penalties | 68% | 0.42 |
| **B** | DHL Air Freight expedite + weekend SMT overtime | ~$22,950 | 97% | **0.81** |

**Step 4 — HITL**
- **HITL required**: YES (VIP order P=95 AND delay > 7 days)
- Must present comparison table to Planning Manager
- Must recommend Option B

**Step 5 — EXECUTION**
- After approval, must describe WRITE calls:
  1. `oracle_ebs.create_purchase_requisition` — expedite amendment
  2. `oracle_ebs.reschedule_wip_job` — add 32h overtime
  3. `mcp_agent_store.create_shipment` — book DHL Air Freight
  4. Notify Sales Agent → DataCorp customer update

---

### Conflict Points

| Agents Involved | Potential Conflict |
|----------------|-------------------|
| Procurement vs. Finance | Air freight cost ($18.75K) exceeds procurement budget |
| Production vs. Logistics | Expedited chips arrive in 3d, but SMT-Line1 may not have capacity |
| Sales vs. Finance | VIP satisfaction vs. cost overrun |

### HITL Decision

```
Decision: Option B — Expedited Air + Weekend OT
Approved by: Planning Manager
Rationale: 989% ROI ($250K revenue - $22.95K cost)
```
