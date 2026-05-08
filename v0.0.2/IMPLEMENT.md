# 🚀 Axon: Strategic Implementation Plan

> Version 0.0.2 — 2026-05-08
>
> Companion documents:
> - [Architecture & Error Model](docs/architecture.md)
> - [ADR-001: Pure MCP Architecture](docs/adr/001-mcp-only.md)
> - [Project manifest](pyproject.toml)

---

## Phase 1: Foundation & Semantic Governance (Month 1)

*Focus: Establishing the universal language, knowledge bridge, and buildable project skeleton.*

- **1.1 Project Skeleton**: Initialize `pyproject.toml` with pinned dependencies (`pydantic-ai`, `langgraph`, `mcp`, `httpx`, `logfire`). Configure `ruff`, `mypy`, `pytest`. Ship `infra/docker-compose.yml` with Postgres (LangGraph state) and Redis (MCP response cache).
- **1.2 Universal Schema Development**: Build `src/axon/core/schema/base.py` using Pydantic v2. Define `MCPToolOutput`, `EntityRef`, `Demand`, `Supply`, `Allocation`, `AgentProposal`, `NegotiationRound`, and the `SemanticTransformer` protocol. Every MCP response is normalized into these types before agents see it.
- **1.3 Configuration Layer**: Implement `src/axon/core/config.py` via `pydantic-settings`. All MCP server URLs, API keys, agent defaults, and infrastructure config loaded from environment (`.env.example` provided). No scattered `os.getenv` calls.
- **1.4 External RAG Integration**: Establish the client-side connection to the **External RAG MCP Server**. Implement the `ContextRetriever` to pull SOPs and policies dynamically into agent prompts — wrapped in `MCPToolOutput` and transformed like any other data source.
- **1.5 Telemetry & Tracing**: Initialize **Logfire**. Set up instrumentation to trace every "thought" and "tool call" made by the agents. Every `MCPToolOutput` carries a `correlation_id` for end-to-end auditability.
- **1.6 Testing Foundation**: Write unit tests alongside schema code — round-trip validation, `SemanticTransformer.can_handle()` routing, and circuit breaker state machine transitions.

## Phase 2: MCP Perception Mesh (Month 2)

*Focus: Connecting the AI brain to enterprise data via pure MCP — with graceful degradation.*

- **2.1 Oracle EBS MCP Integration**: Connect to the Oracle EBS MCP server. Map its tools (e.g., `get_inventory_levels`, `list_wip_jobs`) through a `SemanticTransformer` subclass to Axon Core Schema types.
- **2.2 Multi-ERP Expansion**: Integrate SAP and Odoo MCP servers. Each gets its own `SemanticTransformer` — the orchestrator routes `MCPToolOutput` to the correct transformer via `can_handle()`.
- **2.3 MCP Resilience Layer**: Implement per-server circuit breaker (3 failures → OPEN, 60s cooldown → HALF_OPEN). Implement degradation levels (`FULL` → `DEGRADED` → `LIMITED` → `CRITICAL`) so the system plans with partial data when ERPs are unreachable. Redis caching with per-tool TTL as first-line defense.
- **2.4 Tool Discovery Logic**: Implement an automated discovery service that scans available MCP servers, registers their capabilities to the shared tool registry, and alerts when tools appear or disappear.
- **2.5 Integration Tests**: Agent + MCP stub scenarios. Verify that an agent receiving stubbed MCP responses produces valid `AgentProposal` instances.

## Phase 3: Domain Cognition & Negotiation (Month 3-4)

*Focus: Building specialized intelligence and the conflict resolution engine.*

- **3.1 Domain Agent Deployment**: Develop 10 specialized agents (Sales, Finance, Maintenance, etc.) using `pydantic-ai`. Each agent is assigned specific MCP tools and RAG access. Agents are **model-agnostic** — the LLM backend (Claude, GPT, Gemini, local model) is configurable via `AXON_LLM__MODEL`.
- **3.2 Conflict Resolution Sub-graph**: Build the negotiation logic in **LangGraph**. When agents propose conflicting plans (e.g., Production wants more uptime while Maintenance wants a shutdown), the system triggers an automated resolution with a **guaranteed termination** path:
    1. **Clarification**: conflicting agents justify their position (≤250 chars)
    2. **Amendment**: agents may submit amended proposals
    3. **Utility auction**: supply awarded to the proposal with higher utility score `U_i` for that specific pair
    4. **Tiebreaker**: equal utility → weighted-random selection using business weights
- **3.3 Utility Scoring Engine**: Implement `U_i = Σ (w_k × s_ik)` for each agent proposal, where `w_k` are strategic weights (set via Control Tower) and `s_ik` are normalized scores on dimensions like cost, delivery, and quality. Global utility `U_total = Σ U_i` is tracked per negotiation round.
- **3.4 Negotiation Timeout**: Maximum 5 rounds (configurable). Non-convergence triggers `NEGOTIATION_DEADLOCK` → weighted-random tiebreaker + mandatory HITL review.

## Phase 4: Learning Loop & Executive Control (Month 5)

*Focus: Making the system smarter and giving control back to the users.*

- **4.1 Experience Ledger**: Implement `src/axon/core/learning/`. Every plan is recorded with:
    - Full `PlanContext` (Demand/Supply/Policy snapshot at plan time)
    - All `NegotiationRound` history
    - Tags (`on_time`, `over_budget`, `replan_triggered`)
    - Outcome (populated after execution)
    - **Retention**: 90 days hot (Postgres, full detail), up to 2 years warm (summary only), auto-purge after 2 years
    - **Retrieval**: semantic similarity search via embeddings — `retrieve_similar(demand_profile, constraint_set)` returns top-k past plans for agent reasoning
- **4.2 Strategic Admin Dashboard**: Launch the **Control Tower**. Provide a UI for executives to adjust "Strategic Weights" (e.g., shifting priority from *Cost Saving* to *On-time Delivery*). Weights feed directly into the Utility Scoring Engine.
- **4.3 Human-in-the-Loop (HITL)**: Implement approval nodes in LangGraph. High-impact plans and all deadlock-resolved plans require a human manager to "approve" or "reject" with feedback via the dashboard. Rejected plans are recorded in the Experience Ledger as negative examples.

## Phase 5: Enterprise Hardening & Write-back (Month 6+)

*Focus: Moving from planning to execution safely.*

- **5.1 Secure Write-back**: Enable "Action" tools on the MCP servers to allow Axon to write planned orders and schedules back to Oracle EBS or SAP. Write-back only after HITL approval. All writes logged with correlation ID for audit.
- **5.2 Enterprise RBAC**: Finalize Role-Based Access Control. Ensure agents only access MCP tools and RAG data relevant to their specific domain. Tool-level authorization enforced at the MCP server boundary.
- **5.3 Performance Optimization**: Refine LLM prompts, optimize MCP tool-call batching, and tune Redis TTLs to reduce latency in global plan generation.
- **5.4 E2E & Property-Based Testing**: Full planning cycle with MCP stubs. Property-based tests verify invariants: utility scores are monotonic, allocations never exceed supply, all demand is allocated or explicitly deferred.

---

## Error Handling Strategy (Cross-cutting)

| Layer | Error Category | Handling |
|-------|---------------|----------|
| Connector | `MCP_UNAVAILABLE` | Circuit breaker → cached data → stale marker |
| Connector | `MCP_PARTIAL` | Accept partial results; failed items get `confidence=0.0` |
| Connector | `TRANSFORM_FAILED` | Log raw output, skip item, alert |
| Agent | `AGENT_TIMEOUT` | Submit best-effort proposal, mark incomplete |
| Orchestrator | `NEGOTIATION_DEADLOCK` | Weighted-random tiebreaker, mandatory HITL |
| Orchestrator | `RAG_UNAVAILABLE` | Proceed without policy check, flag outputs |

## Testing Strategy

```
        ┌──────────┐
        │    E2E    │  Full planning cycle with MCP stubs
        │ (Phase 3+)│
        ├──────────┤
        │Integration│  Agent negotiation with mock MCP servers
        │           │
        ├──────────┤
        │   Unit    │  Schema, transformers, utility engine, circuit breaker
        │           │
        └──────────┘
```

- **Unit tests (Phase 1+)**: Schema round-trip, transformer routing, utility scoring, circuit breaker transitions
- **Integration tests (Phase 2+)**: Agent + MCP stub scenarios, 2-agent conflict resolution
- **Simulation framework (Phase 3+)**: YAML scenario files → deterministic replay (`axon-sim run`)
- **Property-based tests (Phase 3+)**: Invariants — monotonic utility, supply bounds, demand completeness

---

## Success Metrics (KPIs)

| Metric | Target |
|--------|--------|
| **Data Normalization** | 100% of ERP data cast to Core Schema |
| **Policy Compliance** | 0% of AI plans violating RAG-stored SOPs |
| **Negotiation Speed** | Cross-departmental conflicts resolved in < 60 seconds |
| **Resilience** | System remains operational with ≤ 2 MCP servers down |
| **Learning Rate** | 15% improvement in plan accuracy after 3 months of feedback |

---

## Deployment Checklist

Reference this checklist at the end of each phase before declaring it complete.
See [docs/architecture.md §7](docs/architecture.md#7-deployment-checklist) for the full per-layer breakdown.

```
PRE-DEPLOY
□ .env filled with production values (no change-me defaults)
□ All MCP server URLs reachable from deployment environment
□ PostgreSQL database created and connection verified (settings.database.url)
□ Redis instance running and reachable (settings.redis.url)
□ LLM API key configured (settings.llm.api_key)
□ Logfire token configured for production observability

AXON CORE
□ Dependencies installed: pip install -e ".[dev]"
□ All tests pass: ruff check && ruff format --check && mypy src/ && pytest
□ Schema models validate: MCPToolOutput → SemanticTransformer → Domain models
□ Circuit breaker tests pass: CLOSED → OPEN → HALF_OPEN → CLOSED

MCP SERVERS
□ Each ERP MCP server running and exposing expected tools
□ Tool discovery: list_tools() returns complete catalog per server
□ SemanticTransformer.can_handle() routes correctly for all tool × server combos
□ Cache TTL configured per tool in Redis

AGENTS
□ All 10 domain agents instantiate without error
□ Each agent's tool registry contains correct MCP tool subset
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
□ Violation scan < 5 seconds for 1000 allocation records
□ Agent negotiation < 60 seconds for 10-agent conflict

MONITORING
□ Logfire spans visible for all MCP calls and agent reasoning
□ Correlation IDs propagated across MCP → transformer → agent → orchestrator
□ Circuit breaker metrics exported (state, failure_count, last_transition)
□ Alert configured for CRITICAL degradation level
```

---

**Status:** *Phase 5 Complete — Write-back, RBAC, caching, E2E property tests*
**GitHub:** [nsanguan/axon](https://github.com/nsanguan/axon)
