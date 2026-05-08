# Scenario: Production Breakdown — Full Escalation Ladder

## File: `escalation_production_breakdown.md`
## Type: Escalation / Production Crisis
## Severity: Critical (triggers ALWAYS_EXECUTIVE — mandatory HITL)

---

### Given (Context)

A complete production line failure on **SMT-Line1** — the only high-speed pick-and-place line for FG-003 Server Mainboard. Estimated repair: **5 days**. This is classified as `EventType.PRODUCTION_BROKEN` which is in the `ALWAYS_EXECUTIVE` whitelist.

**Setup:**
- **MCP Oracle EBS**: SMT-Line1 capacity drops from 160h to 0h. SMT-Line2 has 140h but needs 1d retooling.
- **MCP RAG**: SOP says *"If a critical work center fails, check alternate routing or subcontracting. Escalate to Planning Manager if throughput drops > 30%."*
- **WIP**: WIP-20245 (500 boards) and WIP-20250 (300 boards) queued on SMT-Line1.
- **Sales**: DataCorp order (P=95, $250K) due June 30; TechCo order (P=70, $90K) due July 5.
- **Subcontractor**: ElectroAssem Inc can take 200 boards/day at $15/board premium.

### When (Trigger)

**Maintenance Agent** sends a fault alert via IoT sensor: SMT-Line1 spindle motor failure, ETA for repair = 5 days. Raw sensor data flows into the `worker_node`.

### Then (Expected Orchestrator Behavior)

**Step 1 — WORKER: Anomaly Detection**
- Worker node receives IoT alert via MCP: `oracle_ebs.get_asset_health({work_center: "SMT-Line1"})`
- Computes severity score using `SeverityScorer.compute()`:
  - Event type: `PRODUCTION_BROKEN`
  - Impact: $500,000 (4 departments affected × $125K/day production value)
  - Urgency: 3.0 (rate of degradation — each day of downtime compounds delays)
  - Dept count: 4 (production, maintenance, sales, logistics)
  - Customer risk: 2.0 (DataCorp VIP order P=95)
  - **Score: $500K × 3.0 × 4 × 2.0 = 12,000,000**
- Route: **EXECUTIVE** (score > 10,000 AND whitelisted event type)
- HITL: **REQUIRED** (ALWAYS_EXECUTIVE)

**Step 2 — EXECUTIVE: Crisis Assessment**
- Executive Agent receives Director-level summary:
  - `director_summary`: "SMT-Line1 down 5 days. 800 boards queued. DataCorp $250K at risk."
  - `financial_exposure_usd`: $250,000
  - `affected_departments`: ["production", "maintenance", "sales", "logistics"]
  - `escalation_history`: [Worker detection, Supervisor routing]
- Executive returns `ExecutiveOutput` with:
  - `risk_level`: "critical"
  - `rationale`: minimum 50 chars explaining the cross-departmental impact
  - `recommended_actions`: at least 2 `StrategicAction` objects with `reversible` flags
  - `requires_human_approval`: True
  - `escalate_to_board`: False (operational, not regulatory/safety)

**Step 3 — HITL: Approval Required**
- Graph pauses via `interrupt()` with payload:
  ```
  {
    "risk_level": "critical",
    "rationale": "Production line 100% down...",
    "actions": [
      "[approve] Emergency subcontracting to ElectroAssem — $15/board premium (reversible)",
      "[notify] DataCorp & TechCo of potential delay — proactive communication (reversible)",
      "[approve] SMT-Line2 retooling budget — $4,200 OT (irreversible — tooling change)"
    ],
    "notify_external": true,
    "est_resolution": "48h"
  }
  ```

**Step 4 — RESUME: Human Decision**
- Planning Manager reviews and responds: `"approve"`
- Graph resumes from interrupt with `Command(resume="approve")`
- Executive assessment is stored in `executive_assessment` state
- Escalation step recorded in `escalation_steps` audit trail

**Step 5 — EXECUTION: Write-back**
- `oracle_ebs.update_work_center_status({work_center: "SMT-Line2", status: "active"})`
- `oracle_ebs.reschedule_wip_job({wip_job: "WIP-20250", work_center: "SMT-Line2"})`
- `mcp_agent_buyer.create_purchase_requisition({supplier: "ElectroAssem Inc"})` — **Draft-Only Mandate**: this creates a draft, human submits final PO
- Sales Agent: notify DataCorp and TechCo of updated delivery schedule

---

### Escalation Audit Trail

| Level | Agent | Action | Score |
|-------|-------|--------|-------|
| WORKER | worker_node | IoT fault detection | 12,000,000 |
| SUPERVISOR | supervisor_node | Route: EXECUTIVE (score > 10K + whitelist) | — |
| EXECUTIVE | executive_node | Crisis assessment + HITL | risk=critical |
| HUMAN | planning_manager | Approved all 3 actions | — |

### Golden Rules Verified

| Rule | Status | Evidence |
|------|--------|----------|
| Context Isolation | ✅ | Executive only sees Director summary, not raw IoT data |
| Action Transparency | ✅ | Each action has `reversible=True/False` |
| Draft-Only Mandate | ✅ | purchase_requisition = draft; human submits final |
| No Mesh Coupling | ✅ | All coordination through Supervisor edges |
| Board Escalation | ✅ | Not triggered (operational, not regulatory) |

### HITL Decision

```
Decision: Approve all 3 recommended actions
Approved by: Planning Manager
Rationale: $250K revenue at risk > $19.2K recovery cost
Escalation Level: EXECUTIVE
Total Escalation Steps: 4 (Worker → Supervisor → Executive → Human)
```
