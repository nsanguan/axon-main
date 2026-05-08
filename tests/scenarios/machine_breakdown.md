# Scenario: Machine Breakdown

## File: `machine_breakdown.md`
## Type: Production / Equipment Failure
## Severity: Critical (key work center down, VIP orders queued)

---

### Given (Context)

**SMT-Line1** (the only high-speed pick-and-place line for FG-003 Server Mainboard) has suffered an unexpected breakdown. Estimated repair time: **5 days**.

**Setup:**
- **MCP Oracle EBS**: SMT-Line1 capacity drops from 160h to 0h for next week.
- **MCP RAG**: SOP says *"If a critical work center fails, check alternate routing or subcontracting. Escalate to Planning Manager if throughput drops > 30%."*
- **WIP**: WIP-20245 (500 boards) and WIP-20250 (300 boards) both queued on SMT-Line1.
- **Sales**: DataCorp order (P=95, $250K) due June 30; TechCo order (P=70, $90K) due July 5.
- **Alternate routing**: SMT-Line2 has 140h available but requires 1-day retooling and 20% slower cycle time.
- **Subcontractor**: ElectroAssem Inc can take 200 boards/day, $15/board premium.

### When (Trigger)

**Maintenance Agent** sends a fault alert: SMT-Line1 spindle motor failure, ETA for repair = 5 days.

### Then (Expected Orchestrator Behavior)

**Step 1 — TRIGGER ANALYSIS**
- Call `oracle_ebs.list_wip_jobs({work_center: "SMT-Line1"})`
- Call `oracle_ebs.get_work_center_capacity({work_center: "SMT-Line1"})`
- Confirm: SMT-Line1 fully down, 800 boards queued

**Step 2 — IMPACT ASSESSMENT**
- Call `mcp_agent_store.get_sales_orders({})` to identify at-risk customers
- Call `external_rag.get_sop({process_code: "production.work_center_failure"})`
- Calculate: throughput loss = 800 boards × $250/board = $200K revenue at risk/week

**Step 3 — SOLUTION GENERATION**

| Option | Description | Cost | SLA | Utility |
|--------|------------|------|-----|---------|
| **A** | Wait for repair (5d), then catch up with 1-week overtime | $8,000 OT | 82% | 0.55 |
| **B** | Split: retool SMT-Line2 (1d) + subcontract 200 boards/d to ElectroAssem | $18,500 | 96% | **0.78** |

**Step 4 — HITL**
- **HITL required**: YES (throughput drop > 30% = 100% on this line)
- Must present comparison with subcontracting cost vs. revenue at risk

**Step 5 — EXECUTION**
- `oracle_ebs.update_work_center_status({work_center: "SMT-Line2", status: "active"})`
- `oracle_ebs.reschedule_wip_job({wip_job: "WIP-20250", work_center: "SMT-Line2"})`
- `oracle_ebs.create_purchase_requisition({supplier: "ElectroAssem Inc", ...})`
- Log subcontract order in procurement system

---

### Conflict Points

| Agents Involved | Potential Conflict |
|----------------|-------------------|
| Production vs. Maintenance | Maintenance says 5d repair; production wants 3d |
| Procurement vs. Production | Subcontracting cost vs. in-house cost |
| QA/QC | Subcontracted boards need incoming inspection — extra delay |

### HITL Decision

```
Decision: Option B — Split to SMT-Line2 + Subcontract
Approved by: Planning Manager
Rationale: $18.5K cost preserves $290K in customer revenue
```
