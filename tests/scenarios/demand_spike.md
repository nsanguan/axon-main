# Scenario: Demand Spike

## File: `demand_spike.md`
## Type: Sales / Demand Surge
## Severity: High (unforecasted volume exceeds capacity)

---

### Given (Context)

A major customer (MegaCorp) submitted an **unexpected rush order**: 3,000 units of FG-003 Server Mainboard v5, delivery required in **3 weeks** (instead of normal 6-week lead time). This represents a **60% demand spike** over the forecast.

**Setup:**
- **MCP Oracle EBS**: Current approved forecast = 5,000 units/month. MegaCorp order adds 3,000 = 8,000 total.
- **MCP Agent Store**: On-hand finished goods = 150 units (buffer for existing SOs only).
- **MCP RAG**: SOP says *"Demand spikes > 30% above forecast require HITL approval before committing. Check capacity first."*
- **WIP**: SMT-Line1 at 91% capacity. SMT-Line2 idle but needs 1d retool.
- **Raw materials**: RM-099 (Microchip) on PO-78990 arriving in 14d via sea freight.
- **Suppliers**: ChipLink GmbH can expedite 20K chips in 7d at $1.95/unit (vs standard $0.85).
- **Finance**: MegaCorp order value = $750,000. Gross margin = 35%.
- **Competing orders**: DataCorp (P=95, $250K) and TechCo (P=70, $90K) already scheduled.

### When (Trigger)

**Sales Agent** receives the MegaCorp rush order request and calls the orchestrator.

### Then (Expected Orchestrator Behavior)

**Step 1 — TRIGGER ANALYSIS**
- Call `mcp_agent_store.get_sales_orders({})` and `mcp_agent_store.get_demand_forecast({})`
- Confirm: total demand = 8,000 units vs. 5,000 capacity = 60% spike

**Step 2 — IMPACT ASSESSMENT**
- Call `mcp_agent_store.get_inventory_levels({item_id: "FG-003"})`
- Call `oracle_ebs.list_wip_jobs({item_id: "FG-003"})`
- Call `oracle_ebs.get_work_center_capacity({work_center: "SMT-Line1"})`
- Call `mcp_agent_buyer.get_suppliers({item_id: "RM-099"})` for chip availability
- Call `llmwiki.get_sop({process_code: "sales.demand_spike"})`
- Calculate: capacity gap = 3,000 units × 4 chips = 12,000 additional chips needed

**Step 3 — SOLUTION GENERATION**

| Option | Description | Cost | SLA | Utility |
|--------|------------|------|-----|---------|
| **A** | Accept with partial delivery: 1,500 units on time, 1,500 delayed 2 weeks | $12,000 penalty risk | 72% | 0.48 |
| **B** | Accept full + expedite chips (ChipLink 7d) + activate SMT-Line2 + weekend OT | $34,500 premium | 94% | **0.74** |

**Additional agent coordination needed:**
- **Finance Agent**: ROI analysis — Option B margin = $750K × 35% - $34.5K = $228K net
- **Production Agent**: SMT-Line2 retool + OT schedule feasibility
- **QA/QC Agent**: Additional inspection capacity for doubled output

**Step 4 — HITL**
- **HITL required**: YES (demand spike > 30%, revenue impact > $50K)
- Must present Finance Agent's ROI analysis alongside production feasibility

**Step 5 — EXECUTION**
- `mcp_agent_buyer.create_purchase_requisition({item: "RM-099", supplier: "ChipLink", expedite: true})`
- `oracle_ebs.reschedule_wip_job({wip_job: "split", work_center: "SMT-Line2", ...})`
- `mcp_agent_store.create_shipment({customer: "MegaCorp", ...})`
- Sales Agent: commit delivery date to MegaCorp

---

### Conflict Points

| Agents Involved | Potential Conflict |
|----------------|-------------------|
| Sales vs. Finance | Accepting $750K order vs. $34.5K premium + margin erosion |
| Sales vs. Production | 3-week delivery vs. 5-week realistic capacity |
| Production vs. Warehouse | Doubled output needs 50% more storage space |
| QA/QC vs. Production | Inspection capacity may bottleneck at 2x throughput |

### HITL Decision

```
Decision: Option B — Accept full order + expedite + second line
Approved by: Planning Manager
Rationale: Net margin $228K, customer relationship strategic value
```
