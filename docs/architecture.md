# Axon — Architecture

> Version: 0.0.2 | Last updated: 2026-05-22

## 1. System Overview

```
                        ┌──────────────────────────────────────┐
                        │          CONTROL TOWER (UI)          │
                        │    Next.js frontend / FastAPI backend │
                        └──────────────┬───────────────────────┘
                                       │
                          Strategic weights, approvals
                                       │
┌──────────────────────────────────────┼──────────────────────────────────────┐
│                           ORCHESTRATOR (LangGraph)                           │
│                                                                            │
│  ┌──────────┐   ┌───────────────┐   ┌────────────┐   ┌─────────────────┐  │
│  │ Master   │   │ Conflict      │   │ Utility    │   │ HITL Approval   │  │
│  │ Graph    │──▶│ Resolver      │──▶│ Engine     │──▶│ Node            │  │
│  └──────────┘   └───────────────┘   └────────────┘   └─────────────────┘  │
└──────┬───────────────────────────────┬──────────────────────────────────────┘
       │                               │
       │ Agent proposals               │ Negotiation results
       │                               │
┌──────┴───────────────────────────────┴──────────────────────────────────────┐
│                          COGNITION LAYER (Agents)                           │
│                                                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │ Sales    │ │Production│ │Procuremnt│ │Warehouse │ │  ... (10 total)  │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────────┬─────────┘ │
│       │             │            │            │                │           │
│       └─────────────┴────────────┴────────────┴────────────────┘           │
│                                  │                                          │
│                    All agents call MCP tools through                        │
│                    the universal connector registry                         │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                        MCP Protocol (SSE / Streamable HTTP)
                                   │
┌──────────────────────────────────┼──────────────────────────────────────────┐
│                      PERCEPTION LAYER (MCP Connectors)                      │
│                                                                            │
│  EBS Domain Connectors (9 servers)        Other ERPs     Knowledge         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ demand   │ │ supply   │ │ productn │  │ SAP      │  │ LLMWiki      │  │
│  │ :8102    │ │ :8103    │ │ :8104    │  │ Conn     │  │ Policy Svr   │  │
│  ├──────────┤ ├──────────┤ ├──────────┤  └──────────┘  │ :8000        │  │
│  │ logistics│ │ quality  │ │ asset    │  ┌──────────┐  └──────────────┘  │
│  │ :8105    │ │ :8106    │ │ :8107    │  │ Odoo     │                    │
│  ├──────────┤ ├──────────┤ ├──────────┤  │ Conn     │                    │
│  │ finance  │ │ engineer │ │ warehouse│  └──────────┘                    │
│  │ :8108    │ │ :8109    │ │ :8111    │                                   │
│  └──────────┘ └──────────┘ └──────────┘                                   │
│                                                                            │
│  All connectors extend BaseMCPConnector                                    │
│  (circuit breaker, retry, cache, dual transport)                           │
└──────────┬──────────────────────────────────────────────────────────────────┘
           │
   ┌───────┴────────┐    ┌─────────────────┐    ┌──────────────────┐
   │ EBS MCP Agent  │    │ SAP / Odoo      │    │ EraOwl-LLMWiki   │
   │ (10 servers)   │    │ MCP Servers     │    │ Policy Server    │
   │ Oracle EBS DB  │    │                 │    │ (24 MCP tools)   │
   └────────────────┘    └─────────────────┘    └──────────────────┘
```

## 2. Data Flow

Every planning cycle follows this sequence:

```
1. FETCH         Orchestrator triggers all connectors to fetch current state
                     via MCP tool calls (inventory, WIP, orders, SOPs).

2. TRANSFORM     Each connector's SemanticTransformer maps MCPToolOutput
                     → core schema types (Demand, Supply, Allocation).

3. REASON        Each domain agent receives its slice of the schema,
                     enriched with LLMWiki-sourced policies, and produces
                     an AgentProposal.

4. NEGOTIATE     The Conflict Resolver collects all proposals, computes
                     utility scores, and runs up to N negotiation rounds
                     to converge on a global plan.

5. APPROVE        High-impact plans route through the HITL approval node
                     in the Control Tower before execution.

6. LEARN         The Experience Ledger records the plan, context, decisions,
                     and eventual outcomes for future reasoning.
```

### Sequence: MCP Tool Call Lifecycle

```
Agent                Connector            MCP Server           Redis
  │                      │                     │                  │
  │──call_tool(tool)────▶│                     │                  │
  │                      │──check cache────────│─────────────────▶│
  │                      │◀─────miss───────────│──────────────────│
  │                      │──circuit breaker────│                  │
  │                      │──POST /mcp/call────▶│                  │
  │                      │                     │──execute tool────│
  │                      │◀──MCPToolOutput─────│                  │
  │                      │──cache response─────│─────────────────▶│
  │                      │──transform──────────│                  │
  │◀──Demand/Supply──────│                     │                  │
```

## 3. Error Model

Axon must remain operational when external systems are partially unavailable.
The error model defines how each layer degrades gracefully.

### Error Categories

| Category | Example | Handling |
|----------|---------|----------|
| `MCP_UNAVAILABLE` | Server unreachable, timeout | Circuit breaker opens after 3 consecutive failures. Agent uses cached data (Redis) if fresh; otherwise marks that ERP's data as `stale`. |
| `MCP_PARTIAL` | Tool returns error for one item, success for others | Partial results are accepted. Affected items receive `confidence=0.0` and a `_error` metadata tag. |
| `TRANSFORM_FAILED` | MCP output schema changed, transformer can't parse | Logged at ERROR, raw MCPToolOutput preserved in event log. Item skipped with alert. |
| `AGENT_TIMEOUT` | Agent exceeds `timeout_seconds` | Proposal is submitted with best-effort partial results. Marked `status=incomplete`. |
| `NEGOTIATION_DEADLOCK` | Agents fail to converge after N rounds | Fallback to weighted-random tiebreaker using business weights. Result flagged for mandatory HITL review. |
| `LLMWIKI_UNAVAILABLE` | LLMWiki Policy Server down | Agents proceed without policy context. All outputs flagged `policy_check=skipped`. |

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
| `DEGRADED` | 1 MCP server unhealthy | Plan with partial data; affected ERP's entities marked stale |
| `LIMITED` | 2+ MCP servers or LLMWiki unhealthy | Agents use cached data only; all outputs flagged for HITL |
| `CRITICAL` | All MCP servers unhealthy | System returns last-known-good plan from the Experience Ledger |

## 4. Conflict Resolution Algorithm

The conflict resolver operates over at most `N` rounds (default: 5).

### Per-round process

1. Each agent submits an `AgentProposal` containing its desired allocations.
2. The **Utility Engine** scores each proposal against the business weights:

   ```
   U_i = Σ (w_k × s_ik)    for k in {cost, delivery, quality, ...}
   ```
   where `w_k` is a strategic weight (set via Control Tower) and `s_ik`
   is agent `i`'s normalized score on dimension `k`.

3. **Conflict detection**: two proposals conflict when they allocate the same
   supply to different demands, or allocate beyond available supply.

4. **Resolution strategy** (in order):
   - **a. Clarification**: conflicting agents are asked to justify their
     position within 250 characters.
   - **b. Amendment**: agents may submit amended proposals based on other
     agents' clarifications.
   - **c. Utility auction**: if conflict persists, the supply is awarded to
     the proposal with higher `U_i` for that specific supply-demand pair.
   - **d. Tiebreaker**: equal utility → weighted-random selection using
     business weights as probability distribution.

5. **Convergence**: the round ends when no conflicts remain or `max_rounds`
   is reached. Global utility `U_total = Σ U_i` is recorded per round so
   the Master Graph can select the best round.

### Convergence guarantee

The utility auction (step 4c) is deterministic for any given set of
proposals, so the algorithm always terminates in at most `N` rounds.
Non-convergence after `N` rounds triggers the `NEGOTIATION_DEADLOCK`
error path.

## 5. Experience Ledger

### Schema

```python
class ExperienceRecord:
    plan_id: UUID
    created_at: datetime
    context: PlanContext          # Snapshot of Demand/Supply/Policy at plan time
    final_plan: list[Allocation]
    negotiations: list[NegotiationRound]
    outcome: PlanOutcome | None   # Populated later when results are known
    tags: list[str]               # "on_time", "over_budget", "replan_triggered"
```

### Retention strategy

- Hot storage (Postgres): last 90 days of plans, full detail
- Warm storage (S3-compatible): 91 days – 2 years, summary only
- Expiry: auto-purge after 2 years unless tagged `reference`

### Retrieval

- Semantic similarity search via embedding of `context` + `tags`
- Used at agent reasoning time to retrieve similar past plans:
  `retrieve_similar(demand_profile, constraint_set) → top_k plans`

### PlanTrace — step-by-step reasoning audit

Every agent decision is recorded as a chain of trace steps, forming a
complete reasoning audit trail. This complements the round-level
`NegotiationRound` with fine-grained step-level transparency.

```python
class PlanTrace:
    decision_id: UUID              # Links to ExperienceRecord
    step_sequence: int             # Order within the decision chain
    trigger_event: str             # What caused this step (violation_detected, demand_spike, …)
    agent_id: str                  # Which agent produced this step
    logic_version: str             # Prompt/model version hash, e.g. "planning_v2.3"
    input_snapshot: dict           # State visible to the agent at this step
    output_snapshot: dict          # What the agent decided
    confidence: float              # 0.0–1.0 at this step
    duration_ms: int               # LLM call duration
    model_used: str                # e.g. "claude-sonnet-4-20250514"
    timestamp: datetime
```

Each trace step is immutable — once written, it cannot be modified.
The full chain for a plan is reconstructed by querying `WHERE decision_id = ? ORDER BY step_sequence`.

### Confidence scoring

Per-step confidence feeds into the plan-level confidence:

```
plan_confidence = avg(step.confidence) × negotiation_resolution_factor
```

where `negotiation_resolution_factor` is 1.0 for resolved plans, 0.7 for
deadlock-resolved plans, and 0.5 for HITL-overridden plans.

## 6. Testing Strategy

### Test pyramid

```
        ┌──────────┐
        │    E2E    │  Full planning cycle with MCP stubs (1 scenario per domain)
        │ (Phase 3+)│
        ├──────────┤
        │Integration│  Agent negotiation with mock MCP servers (pytest + docker)
        │           │
        ├──────────┤
        │   Unit    │  Schema validation, transformer logic, utility scoring
        │           │
        └──────────┘
```

### Unit tests (Phase 1, written alongside code)
- Schema round-trip: serialize → deserialize → validate integrity
- SemanticTransformer.can_handle() routing logic
- Utility scoring engine: known inputs → expected output
- Circuit breaker state machine transitions

### Integration tests (Phase 2–3)
- Agent + MCP stub: agent calls tool, receives stubbed response, produces proposal
- 2-agent conflict: production vs maintenance → verify resolution
- Full negotiation: all 10 agents with predefined weights, verify convergence

### Simulation framework (Phase 3)
- Scenario files in YAML: define initial Demand/Supply state, business weights, expected outcome
- `axon-sim run scenarios/basic_plan.yaml` — deterministic replay
- Used for regression testing as the system evolves

### Property-based tests (Phase 3+)
- Utility scores are monotonic: adding supply never decreases total utility
- Allocation quantity never exceeds available supply
- All demand is either allocated or explicitly deferred (no silent drops)

### UAT Scenario Template (Phase 3+)

Each UAT scenario follows this format:

| # | Scenario | Trigger | Expected Result |
|---|----------|---------|-----------------|
| 1 | Supplier delay | PO delivery date slips 5 days | ProcurementAgent detects via supply_stream → negotiation_log created → alt supplier or reschedule proposed |
| 2 | Machine breakdown | Work center efficiency drops to 0 | MaintenanceAgent updates capacity → ProductionAgent reschedules WIP jobs → simulation updated |
| 3 | Demand spike | VIP sales order with priority=95 enters | Demand re-sorts pegging queue → lower-priority demands displaced → violation flagged if supply insufficient |
| 4 | Full plan simulation | User triggers simulation via Control Tower | 100 demands matched to supplies in < 10s → violations flagged → plan_trace populated per step |
| 5 | Policy violation | Plan violates RAG-stored SOP | QAAgent flags via check_compliance → plan blocked at HITL node → human override required |
| 6 | Deadlock resolution | Production vs Maintenance conflict over asset | Negotiation runs ≤ 5 rounds → utility auction resolves or NEGOTIATION_DEADLOCK → HITL |

## 7. Deployment Checklist

```
PRE-DEPLOY
□ .env filled with production values (no change-me defaults)
□ All MCP server URLs reachable from deployment environment
□ PostgreSQL database created and connection verified (settings.database.url)
□ Redis instance running and reachable (settings.redis.url)
□ LLM API key configured (settings.llm.api_key)
□ Logfire token configured for production observability

AXON CORE
□ pyproject.toml dependencies installed (pip install -e ".[dev]")
□ All tests pass: ruff check && ruff format --check && mypy src/ && pytest
□ Schema models validate: MCPToolOutput → SemanticTransformer → Domain models
□ Circuit breaker tests pass: CLOSED → OPEN → HALF_OPEN → CLOSED

MCP SERVERS
□ Each ERP MCP server running and exposing expected tools
□ Tool discovery: list_tools() returns complete catalog for each server
□ SemanticTransformer.can_handle() routes correctly for all tool × server combinations
□ Cache TTL configured per tool in Redis

AGENTS
□ All 10 domain agents instantiate without error
□ Each agent's tool registry contains correct subset of MCP tools
□ Agent proposals produce valid AgentProposal instances (schema validation)
□ RAG integration: get_sop and check_compliance return data

ORCHESTRATOR
□ MasterGraph compiles without error
□ ConflictResolver terminates within max_rounds for known conflict scenarios
□ HITL approval node pauses and resumes correctly
□ Experience Ledger records plan with full PlanTrace chain

SECURITY
□ .env NOT committed to version control
□ No hardcoded secrets in source code
□ RBAC groups defined (viewer, planner, manager, agent_api)
□ WRITE tool HITL gating enforced per docs/mcp-tools.md

PERFORMANCE
□ Dashboard load < 2 seconds (cold start)
□ MCP tool call < 500ms p99 with Redis cache hit
□ Pegging/violation scan < 5 seconds for 1000 allocation records
□ Agent negotiation < 60 seconds for 10-agent conflict

MONITORING
□ Logfire spans visible for all MCP calls and agent reasoning
□ Correlation IDs propagated across MCP → transformer → agent → orchestrator
□ Circuit breaker metrics exported (state, failure_count, last_transition)
□ Alert configured for CRITICAL degradation level
```
