# Scenario: Inventory Shortage

## File: `inventory_shortage.md`
## Type: Warehouse / Raw Material Shortage
## Severity: High (critical material below safety stock, no incoming supply)

---

### Given (Context)

**RM-001** (Titanium Alloy Ti-6Al-4V Sheet) has fallen below safety stock:
- Current on-hand: **800 kg** (safety stock: 1,200 kg)
- Minimum 200 kg needed to keep CNC machining running for next 5 days
- Next scheduled arrival: PO-2026-0891 (1,500 kg) due in **20 days**
- No alternative supplier approved for aerospace-grade Ti-6Al-4V

**Setup:**
- **MCP Oracle EBS**: RM-001 is a critical raw material for FG-001 (Aircraft Bolt AN4-10A).
- **MCP Agent Store**: 3,000 units FG-001 on-hand, plus WIP WIP-10234 (2,500 units, in-progress).
- **MCP RAG**: SOP says *"Aerospace materials cannot be substituted without QA recertification. Partial rationing is allowed per priority matrix."*
- **Sales**: Boeing SO-2026-0421 (5,000 units, P=90, due June 30).
- **Procurement**: No backup supplier qualified for AMS-4911 spec titanium.
- **Warehouse**: 800 kg remaining = 4 days production at current consumption rate.

### When (Trigger)

**Warehouse Agent** sends an inventory alert: RM-001 below safety stock (800/1,200 kg).

### Then (Expected Orchestrator Behavior)

**Step 1 — TRIGGER ANALYSIS**
- Call `mcp_agent_store.get_inventory_levels({item_id: "RM-001"})`
- Confirm: 800 kg on-hand, safety stock = 1,200 kg, shortage = 400 kg

**Step 2 — IMPACT ASSESSMENT**
- Call `mcp_agent_store.get_sales_orders({item_id: "FG-001"})` — Boeing SO (5,000 units, P=90)
- Call `oracle_ebs.get_bom({item_id: "FG-001"})` — check per-unit RM-001 consumption (0.5 kg/unit)
- Call `oracle_ebs.list_wip_jobs({item_id: "FG-001"})` — WIP-10234 consuming RM-001
- Call `mcp_agent_buyer.get_purchase_orders({item_id: "RM-001"})` — check PO status
- Call `external_rag.get_sop({process_code: "warehouse.material_shortage"})`
- Calculate: 800 kg ÷ 0.5 kg/unit = 1,600 units max. Boeing needs 5,000. Gap = 3,400 units.
- **Revenue at risk**: 3,400 units × $5.20/unit = $17,680 immediate; Boeing SO at risk = $250K+ if not fulfilled.

**Step 3 — SOLUTION GENERATION**

| Option | Description | Cost | SLA | Utility |
|--------|------------|------|-----|---------|
| **A** | Ration: produce 1,600 units for Boeing, delay balance 20 days until PO arrives | $0 premium, $8,200 penalty | 55% | 0.35 |
| **B** | Ration + air-freight PO from alternate supplier + QA recertification overtime | $15,800 premium | 92% | **0.68** |

**Option B details:**
- Split: produce 1,600 units immediately using on-hand RM-001
- Air-freight 1,000 kg from TitaniumMet emergency stock (no alternative supplier for AMS-4911)
- QA overtime: recertify alternate batch in 3 days (vs 7 normal)
- Production: limited OT to stretch remaining RM-001 to cover 3,200 units

**Step 4 — HITL**
- **HITL required**: YES (Boeing VIP order P=90, material shortage > 30%)
- Must present QA recertification timeline + cost vs. partial delivery penalty

**Step 5 — EXECUTION**
- `mcp_agent_buyer.create_purchase_requisition({item: "RM-001", supplier: "TitaniumMet", expedite: true})`
- `oracle_ebs.reschedule_wip_job({wip_job: "WIP-10234", split: true, ...})` — ration remaining material
- `oracle_ebs.create_inspection_lot({item: "RM-001", type: "incoming_qa"})` — QA recertification
- Sales Agent: update Boeing with secured delivery date

---

### Conflict Points

| Agents Involved | Potential Conflict |
|----------------|-------------------|
| Warehouse vs. Production | Rationing: who gets the last 800 kg? |
| QA/QC vs. Procurement | No backup supplier approved — new source needs 7d recertification |
| Sales vs. Finance | Partial delivery penalty vs. expedite cost |
| Procurement vs. QA | Expedited material needs rush inspection — QA at capacity |

### HITL Decision

```
Decision: Option B — Ration + Air Freight + QA Overtime
Approved by: Planning Manager
Rationale: Protects Boeing VIP relationship, $17.7K cost vs. $250K revenue at risk
```
