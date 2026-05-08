
## Phase 4 — What Was Built

### 4.1 Experience Ledger
- **Schema models**: ExperienceRecord, PlanTrace, PlanContext, PlanOutcome, LedgerQuery, SimilarPlanResult
- **ExperienceLedger class**: PostgreSQL-backed CRUD with asyncpg, transaction-safe writes, trace recording, retention policy (90d hot → 2y warm → purge)
- **TagBasedEmbedder**: Deterministic hash-based vector embeddings (384-dim, pgvector compatible), keyword extraction for fallback similarity search
- **LearningConfig**: pydantic-settings integration, enabled/disabled, retention, embedding config
- **get_pool()**: Shared database connection pool helper for master graph integration

### 4.2 Strategic Admin Dashboard (Control Tower)
- **FastAPI backend**:
  - `/api/weights` — GET/PUT strategic business weights
  - `/api/weights/defaults` — reset to defaults
  - `/api/plans` — list plans from Experience Ledger
  - `/api/plans/{id}` — plan detail
  - `/api/approvals/pending` — pending HITL approvals
  - `/api/approvals/action` — approve/reject plans
  - `/api/approvals/config` — HITL configuration
  - `/api/agents` — domain agent listing
  - `/api/tools` — MCP tool catalog
  - `/api/system` — system health / degradation
  - `/api/health` — health check
- **Next.js frontend** (Control Tower pages):
  - Dashboard overview with stats cards, weights bars, server status
  - Strategic Weights config with sliders and validation
  - Plan History with filtering and status badges
  - Pending Approvals with approve/reject actions

### 4.3 HITL Integration
- **node_approve**: Proper HITL decision logic with 5 conditions for requiring human review
- **_needs_hitl()**: Deadlock, VIP demand, conflict count, confidence threshold detection
- **route_after_approve**: Routes to LEARN or END based on approval state
- **Shared notifications module**: In-memory pending approvals queue wired to dashboard API

### 4.4 Master Graph Updates
- **node_learn**: Writes plan context, traces, negotiations to Experience Ledger
- **PlanningState**: Extended with 9 new fields (hitl_required, approval_plan_id, business_weights, etc.)
- **record_plan_from_state()**: Extracts planning state into ExperienceRecord
- **record_outcome()**: Updates plan outcomes after execution
