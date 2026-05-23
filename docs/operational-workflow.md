# Axon — Operational Workflow

> Version: 0.0.2 | Last updated: 2026-05-23

## 1. System Architecture

```
                          CONTROL TOWER (UI)
                     Next.js frontend / FastAPI backend
                                  │
                      Strategic weights, approvals
                                  │
┌─────────────────────────────────┼─────────────────────────────────────┐
│                      ORCHESTRATOR (LangGraph)                          │
│                                                                        │
│  ┌──────────┐   ┌───────────────┐   ┌────────────┐   ┌─────────────┐ │
│  │ Master   │   │ Conflict      │   │ Utility    │   │ HITL        │ │
│  │ Graph    │──▶│ Resolver      │──▶│ Engine     │──▶│ Approval    │ │
│  └──────────┘   └───────────────┘   └────────────┘   └─────────────┘ │
└──────┬─────────────────────────────────────────────────────────────────┘
       │                        MCP Protocol (SSE / Streamable HTTP)
       │
┌──────┴─────────────────────────────────────────────────────────────────┐
│                    COGNITION LAYER (10 Domain Agents)                    │
│                                                                          │
│  ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ Sales  │ │Production│ │Procurement│ │Warehouse │ │  ... 10 total │  │
│  └────────┘ └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└──────┬──────────────────────────────────────────────────────────────────┘
       │
┌──────┴──────────────────────────────────────────────────────────────────┐
│                 PERCEPTION LAYER (10 MCP Connectors)                      │
│                                                                          │
│  ebs_demand :8102   ebs_supply :8103   ebs_production :8104             │
│  ebs_logistics:8105  ebs_quality :8106  ebs_asset :8107                │
│  ebs_finance :8108   ebs_engineering:8109  ebs_warehouse :8111          │
│  ebs_auth    :8101                                                       │
└──────┬──────────────────────────────────────────────────────────────────┘
       │
┌──────┴──────────────────────────────────────────────────────────────────┐
│                      DATA SOURCES (MCP Servers)                           │
│                                                                          │
│  EBS MCP Agent (10 servers)    SAP    Odoo    LLMWiki Policy Server     │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2. Trigger Points — How Planning Cycles Start

Axon is **event-driven**. A planning cycle is triggered by one of:

### 2.1 REST API Call (Production)

```
POST /api/escalation/start
Body: {
    "event_type": "po_delay",          // disruption type
    "raw_detail": "PO#8921 delayed 8 days",
    "affected_departments": ["production", "procurement", "sales"],
    "thread_id": "optional-uuid"
}
→ MasterGraph.ainvoke(state) → full planning cycle
```

**Port**: 8020 (API server via Docker) or 8000 (orchestrator standalone)

### 2.2 CLI Simulation (Development/Testing)

```bash
axon-sim run tests/scenarios/machine_breakdown.md
→ SimulationRunner → MasterGraph().run(planning_context)
```

### 2.3 HITL Resume (After Human Approval)

```
POST /api/escalation/{thread_id}/approve
Body: { "decision": "approve" }
→ graph.ainvoke(Command(resume=decision)) → resumes from APPROVE node
```

## 3. Complete Planning Cycle — 8 Phases

Every planning cycle runs through these LangGraph nodes in order:

```
RETRIEVE → FETCH → TRANSFORM → REASON → NEGOTIATE → APPROVE → LEARN → STORE
```

### Phase 1: RETRIEVE (`node_retrieve_context`)

**Purpose**: Load past insights from long-term memory.

**Actions**:
1. Query `memory_store` table (PostgresStore) for:
   - Agent insights from past cycles (`agent_insights/*`)
   - Plan history (`plan_history/*`)
   - Negotiation patterns (`negotiation_patterns/*`)
2. Inject these into `past_insights` so agents can reference historical decisions

**Output**: `state.past_insights` — list of historical records with similarity scores

---

### Phase 2: FETCH (`node_fetch`)

**Purpose**: Pull current operational state from all MCP servers in parallel.

**Actions**:

| Server | Tools Called | Data Retrieved |
|--------|-------------|----------------|
| `ebs_demand` | `get_sales_orders`, `get_demand_forecast` | Open sales orders, forecasted demand |
| `ebs_supply` | `get_inventory_levels`, `get_purchase_orders` | On-hand inventory, open POs |
| `sap` | `get_sales_orders` | SAP-side demand |
| `llmwiki` | `get_sop` | Manufacturing SOPs |

**Graceful degradation**: If any server fails, it's added to `failed_servers` and the cycle continues with remaining data. Degradation level is computed:
- 0 failed → `FULL`
- 1 failed → `DEGRADED`
- 2 failed → `LIMITED`
- 3+ failed → `CRITICAL`

**Output**: `state.raw_demands`, `state.raw_supplies`, `state.raw_policies` — wrapped as `MCPToolOutput` dicts

---

### Phase 3: TRANSFORM (`node_transform`)

**Purpose**: Map MCPToolOutput → Domain models via SemanticTransformers.

**Actions**:
1. For each raw MCPToolOutput dict, reconstruct the typed `MCPToolOutput` object
2. Route to correct transformer via `can_handle()`:
   - `OracleEBSTransformer` — for oracle_ebs-sourced data
   - `SAPTransformer` — for SAP-sourced data
   - `OdooTransformer` — for Odoo-sourced data
3. Each transformer maps to `Demand` or `Supply` Pydantic models
4. Items that fail transformation get `confidence=0.0` and are logged

**Output**: `state.demands`, `state.supplies` — lists of typed domain models

---

### Phase 4: REASON (`node_reason`)

**Purpose**: All 10 domain agents analyze their area and produce proposals.

**Actions**:
1. Build connector registry from settings (all enabled MCP connectors)
2. Instantiate all 10 agents with shared context:
   - `SalesAgent`, `ProcurementAgent`, `FinanceAgent` (commercial group)
   - `ProductionAgent`, `LogisticsAgent`, `WarehouseAgent` (operations group)
   - `QAAgent`, `QCAgent`, `MaintenanceAgent`, `PDAgent` (technical group)
3. Each agent receives:
   - Current demands, supplies, allocations
   - Past insights from Phase 1
   - Business weights
   - Access to MCP tools via connector registry
4. All 10 agents run in parallel via `asyncio.gather`
5. Each agent produces an `AgentProposal` with:
   - `allocations`: list of demand→supply bindings
   - `utility_score`: 0.0–1.0 self-assessment
   - `justification`: natural language reasoning
   - `status`: proposed/accepted/rejected/amended

**Agent-specific tools** (via PydanticAI):

| Agent | MCP Tools |
|-------|----------|
| Sales | `get_sales_orders`, `get_demand_forecast`, `get_available_to_promise`, `get_inventory_levels`, `get_shipments` |
| Production | `list_wip_jobs`, `get_bom`, `get_work_center_capacity`, `get_routing`, `reschedule_wip_job` |
| Procurement | `get_suppliers`, `get_item_costs`, `get_purchase_orders`, `get_supplier_performance`, `create_purchase_requisition` |
| Warehouse | `get_inventory_levels`, `get_safety_stock`, `get_storage_capacity`, `get_inventory_aging` |
| Logistics | `get_shipments`, `get_carrier_rates`, `get_transit_times`, `get_delivery_constraints`, `create_shipment` |
| Finance | `get_item_costs`, `get_budget`, `get_gl_accounts`, `get_profitability` |
| QA | `get_sop`, `check_compliance`, `get_audit_history`, `get_regulatory_requirements` |
| QC | `get_inspection_plan`, `get_defect_history`, `create_inspection_lot` |
| PD | `get_bom`, `get_engineering_changes`, `get_item_master` |
| Maintenance | `get_asset_health`, `get_maintenance_schedule`, `get_downtime_history`, `update_work_center_status` |

**Output**: `state.agent_proposals` — dict of `agent_id → AgentProposal`

---

### Phase 5: NEGOTIATE (`node_negotiate`)

**Purpose**: Conflict Resolver runs utility-auction rounds until convergence.

**Algorithm**:
1. Deserialize agent proposals into typed `AgentProposal` objects
2. Create `ConflictResolver` with business weights and `max_rounds` (default: 5)
3. Run negotiation:

```
Round N:
  1. Each agent submits proposal
  2. Utility Engine scores each: U_i = Σ (w_k × s_ik)
  3. Conflict detection: same supply → different demand, or overallocation
  4. Resolution:
     a. Clarification (250 char justification exchange)
     b. Amendment (agents revise based on others' positions)
     c. Utility auction (higher U_i wins the supply-demand pair)
     d. Tiebreaker (weighted-random using business weights)
  5. Converged if no conflicts remain
```

4. Record all rounds, select best by global utility

**Convergence guarantee**: The utility auction is deterministic → always terminates in ≤N rounds. Non-convergence after N rounds → `NEGOTIATION_DEADLOCK` error.

**Output**: `state.final_plan` (list of allocations), `state.deadlock`, `state.negotiation_rounds`

---

### Phase 6: APPROVE (`node_approve`)

**Purpose**: Human-in-the-Loop approval gate.

**Decision logic**:

| Condition | Action |
|-----------|--------|
| Deadlock reached | Mandatory HITL |
| VIP order impacted (priority > 80) | Mandatory HITL |
| Delay > 7 days | Mandatory HITL |
| Cost impact > $50,000 | Mandatory HITL |
| First 5 planning cycles | Mandatory HITL |
| All other cases | Auto-approve if confidence ≥ 0.6 |

**HITL flow**:
1. Plan recorded to Experience Ledger (pending)
2. Dashboard notification sent (`notify_pending_approval`)
3. Graph pauses at APPROVE node (LangGraph interrupt)
4. Human reviews via Control Tower UI
5. Resume: `POST /api/escalation/{thread_id}/approve` with decision
6. Graph continues to LEARN phase

**Auto-approval flow**: Plan marked approved, continues to LEARN immediately.

**Executive escalation**: If severity score > `DIRECTOR_MAX`, routes to `node_executive` for strategic assessment before approval.

**Output**: `state.approved`, `state.hitl_required`, `state.approval_plan_id`

---

### Phase 7: LEARN (`node_learn`)

**Purpose**: Record plan, context, and outcome in Experience Ledger.

**Actions**:
1. If plan was already recorded during HITL → update outcome
2. If not → record fresh:
   - `ExperienceRecord` with full context snapshot
   - `PlanTrace` chain (step-by-step agent decisions)
   - Tags, confidence scores, timing data
3. Dashboard notification: `notify_plan_recorded`

**Retention policy**:
- Hot (0–90 days): full detail in PostgreSQL
- Warm (91 days–2 years): summary only
- Purge (>2 years): deleted unless tagged `reference`

**Output**: `state.experience_record_id`

---

### Phase 8: STORE (`node_store_insights`)

**Purpose**: Persist learnings to long-term memory for future cycles.

**Actions**:
1. Save plan summary → `plan_history` namespace
2. Save agent-specific insights → `agent_insights/{agent_id}` namespace
3. If >2 negotiation rounds → save pattern → `negotiation_patterns` namespace

**Output**: Memory store updated for next RETRIEVE phase

---

## 4. Data Flow (End-to-End)

### MCP Tool Call Lifecycle

```
Agent              Connector           MCP Server           Redis
  │                    │                    │                  │
  │──call_tool(tool)──▶│                    │                  │
  │                    │──check cache───────│─────────────────▶│
  │                    │◀───miss────────────│──────────────────│
  │                    │──circuit breaker───│                  │
  │                    │──POST /mcp/call───▶│                  │
  │                    │                    │──execute tool─── │
  │                    │◀──MCPToolOutput────│                  │
  │                    │──cache response────│─────────────────▶│
  │                    │──transform─────────│                  │
  │◀──Demand/Supply────│                    │                  │
```

### State Flow Through the Graph

```
PlanningRequest        raw_demands[]        demands[]           agent_proposals{}
   │                      │                    │                     │
   ▼                      ▼                    ▼                     ▼
[RETRIEVE]───past_insights[]                [TRANSFORM]          [REASON]
   │                                           │                     │
   ▼                                           ▼                     ▼
[FETCH]─────raw_supplies[]───────────────supplies[]───────allocation proposals
   │                                           │                     │
   ▼                                           ▼                     ▼
raw_policies[]                            [NEGOTIATE]──────negotiation_rounds[]
                                              │                     │
                                              ▼                     ▼
                                       final_plan[]           deadlock flag
                                              │
                            ┌─────────────────┼─────────────────┐
                            ▼                                   ▼
                       [APPROVE]                           [EXECUTIVE]
                       approved=T/F                    (if severity > threshold)
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
         [LEARN]      (HITL pause)   (rejected → END)
         experience_record_id
              │
              ▼
         [STORE]
         memory_store updated
              │
              ▼
            END
```

## 5. Conflict Resolution Detail

### Business Weights (configurable via Control Tower)

```
cost:          0.30  (default)
delivery:      0.30
quality:       0.20
sustainability: 0.10
flexibility:   0.10
                1.00
```

### Utility Score Calculation

For agent `i` across dimension `k`:
```
U_i = Σ (w_k × s_ik)
```

where:
- `w_k` = business weight for dimension k
- `s_ik` = agent i's normalized score on dimension k (0.0–1.0)

### Tiebreaker Rule

When two agents have equal utility for a supply-demand pair, the Conflict Resolver uses a **weighted-random tiebreaker** using business weights as the probability distribution. The agent with the higher weight in the most relevant dimension wins.

## 6. Error Handling & Degradation

### Circuit Breaker (per MCP server)

```
State: CLOSED ──(3 consecutive failures)──▶ OPEN
                                              │
                                     (60s cooldown)
                                              │
                                              ▼
State: HALF_OPEN ──(1 success)──▶ CLOSED
                  ──(1 failure)──▶ OPEN
```

### Degradation Levels

| Level | Condition | Behavior |
|-------|-----------|----------|
| `FULL` | All MCP servers healthy | Normal operation |
| `DEGRADED` | 1 MCP server unhealthy | Plan with partial data; affected entities marked stale |
| `LIMITED` | 2+ MCP servers or LLMWiki unhealthy | Agents use cached data; all outputs flagged for HITL |
| `CRITICAL` | All MCP servers unhealthy | Return last-known-good plan from Experience Ledger |

### Error Categories

| Category | Example | Handling |
|----------|---------|----------|
| `MCP_UNAVAILABLE` | Server unreachable, timeout | Circuit breaker opens; use Redis cache if fresh |
| `MCP_PARTIAL` | Tool error for one item | Partial results accepted; `confidence=0.0` + `_error` tag |
| `TRANSFORM_FAILED` | Schema changed, transformer can't parse | Raw MCPToolOutput preserved; item skipped with alert |
| `AGENT_TIMEOUT` | Agent exceeds `timeout_seconds` | Best-effort partial proposal; `status=incomplete` |
| `NEGOTIATION_DEADLOCK` | No convergence after N rounds | Weighted-random tiebreaker; mandatory HITL |
| `LLMWIKI_UNAVAILABLE` | Policy Server down | Agents proceed without policy context; `policy_check=skipped` |

## 7. Escalation Ladder

```
Event
  │
  ▼
[WORKER]  ── severity ≤ 2,000 ──▶ auto-resolve
  │ severity > 2,000
  ▼
[MANAGER] ── severity ≤ 10,000 ──▶ within-department resolution
  │ severity > 10,000
  ▼
[DIRECTOR] ── cross-department coordination
  │ severity > 10,000 OR always_executive event
  ▼
[EXECUTIVE] ── strategic HITL decision
  │ escalate_to_board=True
  ▼
[BOARD] ── financial fraud, data breach, regulatory violation, safety incident
```

### Severity Score Formula

```
score = impact_value × urgency × dept_count × customer_risk
```

### Event Types That Always Escalate to Executive

- `PRODUCTION_BROKEN`
- `SAFETY_INCIDENT`
- `SUPPLIER_CRISIS`

### Board Escalation Triggers

- Financial fraud
- Data breaches
- Regulatory violations
- Safety incidents involving injuries

## 8. Deployment Architecture

### Services (Docker Compose)

```
┌──────────────┐     ┌─────────────────┐     ┌───────────────┐
│ axon-frontend│────▶│    axon-api     │────▶│ axon-orch     │
│  (Next.js)   │     │  (FastAPI 8020) │     │ (MasterGraph) │
│  :3000       │     │                 │     │ :8000         │
└──────────────┘     └─────────────────┘     └───────┬───────┘
                                                     │
                   ┌─────────────────────────────────┼──────────┐
                   │  MCP protocol                    │          │
                   ▼                                  ▼          │
          ┌───────────────┐  ┌──────────────┐  ┌──────────────┐ │
          │ agent-comm    │  │ agent-ops    │  │ agent-tech   │ │
          │ :8201         │  │ :8202        │  │ :8203        │ │
          │ Sales         │  │ Production   │  │ QA,QC,PD     │ │
          │ Procurement   │  │ Logistics    │  │ Maintenance  │ │
          │ Finance       │  │ Warehouse    │  │              │ │
          └───────────────┘  └──────────────┘  └──────────────┘ │
                   │              │               │              │
                   └──────────────┴───────────────┘              │
                                  │                               │
                         ┌────────▼────────┐          ┌──────────▼──────────┐
                         │ EBS MCP Agent   │          │      Redis          │
                         │ (10 servers)    │          │      :6379          │
                         │ :8101-8111      │          └─────────────────────┘
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │   PostgreSQL    │
                         │   :5435         │
                         └─────────────────┘
```

### Database Schema Organization

| Schema | Tables | Purpose |
|--------|--------|---------|
| `axon_brain` | 8 | Checkpoints, memory store, orchestrator logs, experience records, plan traces |
| `axon_agents` | 3 | Agent proposals, negotiation rounds, proposal-allocations join |
| `axon_plan` | 3 | Demands (18 cols), supplies (17 cols), allocations (11 cols) |
| `axon_mcp` | 2 | Tool registry (54 tools), agent-tool assignments |
| `axon_board` | 6 | System config, business weights, HITL queue, approval audit, KPIs, events |
| `axon_process` | 0 | Reserved for future workflows |
| `axon_admin` | 0 | Reserved for future admin |

## 9. Operational Commands

### Startup

```bash
# Infrastructure
docker compose -f infra/docker-compose.yml up -d

# Database migration
AXON_DATABASE__URL="postgresql+asyncpg://axon:password@host:5435/axon" \
  python -m axon.core.schema.migrate

# Seed sample data
AXON_DATABASE__URL="postgresql+asyncpg://axon:password@host:5435/axon" \
  python -m axon.core.schema.seed
```

### Trigger a Planning Cycle

```bash
# Via REST API
curl -X POST http://localhost:8020/api/escalation/start \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "po_delay",
    "raw_detail": "PO#8921 delayed 8 days",
    "affected_departments": ["production", "procurement", "sales"]
  }'

# Via CLI simulation
axon-sim run tests/scenarios/machine_breakdown.md
```

### Monitoring

```bash
# Health check
curl http://localhost:8020/api/health

# HITL queue status
curl http://localhost:8020/api/pending-approvals

# Business weights
curl http://localhost:8020/api/weights
```

## 10. Key Design Invariants

1. **No direct database access** — all ERP data flows through MCP
2. **Agents never touch ERP-native IDs** — they reason through `EntityRef`
3. **All MCP responses normalized** through `SemanticTransformer.can_handle()` routing
4. **Conflict resolution always terminates** — max N rounds with utility-auction tiebreaker
5. **Every MCP call carries a `correlation_id`** for full audit trail
6. **No mesh coupling** — agents never call each other directly, only through Supervisor (LangGraph edges)
7. **Draft-Only Mandate** — manager agents create drafts; only humans execute final writes
8. **Every StrategicAction includes `reversible: bool`** — human approvers must know if action can be undone
