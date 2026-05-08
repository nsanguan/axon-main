# 🧠 Axon

### **The Open-Source Agentic Planning OS (Pure MCP Architecture)**

**Axon** is a next-generation Supply Chain Planning (ASCP) framework built for the **Agentic AI era**. Unlike legacy systems that rely on direct database connections, Axon is **100% MCP-native**. It is designed as an **AI-native planning and orchestration layer** that sits above ERP systems and turns demand, inventory, procurement, and operational signals into coordinated decisions and actionable workflows.

In practical terms, Axon is an **agentic supply chain planning nerve system for modern ERPs**: it connects ERP execution, planning logic, and multi-agent reasoning without coupling the core planning engine to any one system of record.

---

## 🌟 Key Strategic Features

* **100% MCP-Native Architecture**: No direct DB connections (JDBC/ORDS). All systems—Oracle EBS, SAP, Odoo, and RAG—interface via the **Model Context Protocol**.
* **Plug-and-Play Connectors**: Swap between different ERP versions or vendors simply by switching the MCP host.
* **External Knowledge Mesh**: Leverages your **External RAG MCP Server** to verify every plan against corporate SOPs and legal constraints.
* **Universal Semantic Schema**: A unified Pydantic-based data language (`axon.core.schema`) that translates diverse MCP tool outputs into a single planning context.
* **Autonomous Negotiation**: A LangGraph-powered "Conflict Resolution" engine where 10+ departmental agents negotiate to find the highest utility outcome.
* **Self-Improving Logic**: An Experience Ledger that records the performance of AI-generated plans to refine future reasoning.
* **ERP-Agnostic Planning Layer**: Works as a decision and orchestration layer above systems like Oracle EBS, SAP, and Odoo rather than replacing them.
* **Human-in-the-Loop Ready**: Designed for approval gates, explainability, and enterprise-safe operational decision support.

---

## 🚀 Why Axon

Most systems solve only one part of the operational planning problem:

* **ERPs** are good at recording and executing transactions.
* **Planning tools** are good at generating forecasts or recommendations.
* **Agent frameworks** are good at orchestrating AI workflows.

But supply chain teams need all three to work together.

Axon bridges that gap by combining:

* **planning intelligence**
* **workflow orchestration**
* **ERP-connected execution context**
* **agentic decision support**

That makes Axon more than an ERP integration and more than a generic agent framework — it is a **planning brain and coordination layer** for supply chain operations.

---

## 🏗 Modular Project Structure

```text
axon/
├── src/
│   └── axon/                      # Installable Python package
│       ├── __init__.py
│       ├── core/                  # Logic & Shared Governance
│       │   ├── schema/            # Universal Semantic Models (Pydantic v2)
│       │   │   ├── base.py        # Demand, Supply, Allocation, MCPToolOutput
│       │   │   ├── demand.py      # Forecast & Sales models
│       │   │   ├── supply.py      # Inventory & Production models
│       │   │   └── allocation.py  # Matching & Optimization models
│       │   ├── config.py          # Typed settings (pydantic-settings)
│       │   ├── learning/          # Experience Ledger & Decision Memory
│       │   └── telemetry/         # Logfire / OpenTelemetry
│       │
│       ├── connectors/            # Perception Layer (Pure MCP Clients)
│       │   ├── mcp_oracle_ebs/    # Oracle EBS MCP Client (No JDBC) 🟢
│       │   ├── mcp_sap/           # SAP MCP Client
│       │   ├── mcp_odoo/          # Odoo MCP Client
│       │   └── mcp_external_rag/  # Bridge to your External RAG Server
│       │
│       ├── agents/                # Cognition Layer (Specialized Agents)
│       │   ├── base_agent.py      # Parent Agent (MCP Tool-calling capable)
│       │   ├── tools.py           # MCP tool definitions per agent
│       │   ├── commercial/        # Sales, Procurement, Finance
│       │   ├── technical/         # QA, QC, Maintenance, PD
│       │   └── operations/        # Production Planner, Warehouse, Logistics
│       │
│       ├── orchestrator/          # The Nervous System (Workflows)
│       │   ├── master_graph.py    # LangGraph Orchestration
│       │   ├── conflict_resolver.py   # Utility-based Negotiation Logic
│       │   └── tools/             # Unified toolset for all MCP servers
│       │
│       └── dashboard/             # Control Tower UI
│           ├── frontend/          # Next.js Strategic Weights UI
│           └── backend/           # FastAPI Control Layer
│
├── docs/                          # Architecture & Design
│   ├── architecture.md
│   ├── mcp-tools.md
│   └── adr/
├── tests/                         # Simulation & Integration tests
│   └── scenarios/                 # Gherkin-style disruption scenarios
├── scripts/                       # Scenario test runner
├── examples/                      # Escalation architecture reference
├── infra/                         # Docker Compose &amp; deployment
│   └── docker-compose.yml
├── pyproject.toml                 # Build & Dependencies
├── requirements.txt               # Full tech stack (pip install)
├── requirements-dev.txt           # Dev tooling (pytest, ruff, mypy)
├── AGENTS.md                      # Agent instructions (instruction manual)
└── README.md                      # Documentation
```

---

## 🏢 10-Department Agentic Mesh

Axon orchestrates the following domains, each acting as an autonomous agent that consumes MCP tools.
See [docs/mcp-tools.md](docs/mcp-tools.md) for the full tool catalog with parameter signatures.

1. **Sales**: Demand & ATP (Available to Promise)
2. **Production**: MPS & Finite Capacity Scheduling
3. **Procurement**: Automated Sourcing & Supplier Sync
4. **Warehouse**: Safety Stock & Inventory Optimization
5. **Logistics**: Route & Distribution Planning
6. **Finance**: ROI, Costing & Budget Alignment
7. **QA (Quality Assurance)**: Regulatory & SOP Compliance (via RAG)
8. **QC (Quality Control)**: Inspection & Rework Logic
9. **PD (Product Development)**: BOM Engineering & New Product Intro
10. **Maintenance**: Predictive Downtime & Asset Health

---

## 🧭 Competitive Positioning

Axon sits at the intersection of:

* **supply chain planning**
* **ERP operations**
* **agentic AI orchestration**

Compared with systems like **Odoo**, **ERPNext**, **OpenBoxes**, **Apache OFBiz**, and **Tryton**, Axon focuses on the layer above transaction execution: **decision-making, planning orchestration, and intelligent operational coordination**.

Compared with general-purpose agent systems like **PraisonAI** or **OpenAgentsControl**, Axon is **domain-specific** and designed around the realities of supply chain workflows and ERP-connected environments.

In short:

* **ERP systems** execute transactions.
* **Inventory systems** manage stock and movement.
* **Agent frameworks** orchestrate generic AI workflows.
* **Axon** connects planning intelligence, workflow coordination, and ERP-aware decision-making.

---

## 🗺 Implementation Roadmap

### **Phase 1: Pure MCP Foundation (Month 1)**

* Initialize `pyproject.toml` with pinned dependencies and Dockerized infrastructure (Postgres + Redis).
* Build `axon.core.schema` as the "Universal Receiver" for all MCP tool outputs.
* Implement typed configuration via `pydantic-settings` (`.env` → `settings`).
* Establish connection to the **External RAG MCP Server** with `ContextRetriever`.
* Setup **Logfire** for full-trace observability with correlation IDs.
* Write unit tests alongside schema code (round-trip validation, transformer routing, circuit breaker).

### **Phase 2: ERP Perception Mesh (Month 2)**

* Integrate **Oracle EBS MCP Server** (Standardized tool-based access to MTL/WIP).
* Integrate SAP and Odoo MCP Servers.
* Build the **Semantic Transformer** to cast MCP JSON outputs into Axon Schema.

### **Phase 3: Cognitive Logic & Conflict (Month 3-4)**

* Deploy 10 Specialized Agents with **RAG-augmented reasoning**.
* Develop the **Conflict Resolution Engine** to handle cross-departmental "deadlocks" (e.g., Maintenance vs. Production).
* Implement the **Utility Engine** to calculate the best plan based on Business Weights.

### **Phase 4: Feedback & Control (Month 5)** ✅

* Launch **Admin Control Tower** for real-time strategic weight tuning. ✅
* Activate the **Experience Ledger** to log the success/failure of plans. ✅
* Enable **Human-in-the-loop (HITL)** for final plan approvals. ✅
* PostgreSQL-backed `axon_brain` schema (experience_records, memory_store, plan_traces). ✅
* Async `ExperienceLedger` with JSONB codec, `search_path=axon_brain`, semantic similarity retrieval. ✅

### **Phase 5: Scale & Governance (Month 6+)** ✅

* Secure Bi-directional MCP tool-calls for ERP write-backs. ✅
* Finalize RBAC and AI Guardrails for enterprise safety. ✅
* Escalation architecture: 4-tier ladder (Worker→Manager→Director→Executive). ✅
* Executive Agent with Intent Router + Crisis Decider. ✅
* HITL approval API with REST endpoints and SSE streaming. ✅
* Draft-Only Mandate for AI procurement recommendations. ✅

### **Phase 6: Control Tower Dashboard** ✅

* **FastAPI backend** (`src/axon/dashboard/backend/`) on port **8200** with 27-endpoint API. ✅
* **Next.js 14 App Router** frontend (`src/axon/dashboard/frontend/`) on port **3010**. ✅
* `axon_board` PostgreSQL schema — 6 tables: `system_config`, `business_weights`, `hitl_queue`, `approval_audit`, `board_events`, `board_kpis`. ✅
* `BoardRepository` — async DB-backed storage with in-memory fallback for all Control Tower state. ✅
* **Strategic Weights** page — live CRUD for `cost / delivery / quality / sustainability / flexibility` weights with DB persistence. ✅
* **Plan History** page — 10 seeded plans across aerospace customers (Boeing, Airbus, Lockheed, GE Aviation, Raytheon) with confidence scores, allocation counts, deadlock / approved status. ✅
* **Pending Approvals** page — 4 seeded HITL scenarios (VIP order, machine breakdown deadlock, cost-threshold expediting, demand spike); approve/reject actions write audit trail to `axon_board.approval_audit`. ✅
* **Dashboard home** — system health card, degradation badge, pending approval count. ✅
* API proxy: Next.js `/api/*` → FastAPI `localhost:8200/api/*` via `next.config.js` rewrites. ✅

---

## 🛠 Tech Stack

* **LLM Layer**: Model-agnostic via `pydantic-ai` — Claude, GPT, Gemini, or local models via `AXON_LLM__MODEL`
* **State Machine**: `langgraph` (StateGraph + checkpointing)
* **Knowledge Base**: External RAG MCP Server (Standalone)
* **Standard Protocol**: Model Context Protocol (MCP) — all ERP and data access
* **Data Validation**: `pydantic` v2 + `pydantic-settings`
* **Observability**: `logfire` (OpenTelemetry tracing + structured logging)
* **Infrastructure**: PostgreSQL (LangGraph state) + Redis (MCP response cache)

---

## 📌 Positioning Summary

**Axon is not just another ERP, not just another forecasting tool, and not just another generic agent framework.**

It is an **AI-native planning and orchestration layer** for modern ERP environments — purpose-built to help supply chain teams move from fragmented planning processes to intelligent, explainable, and increasingly autonomous operations.

---

## 🧪 How to Run Tests

### Python Unit Tests

```bash
# Run all unit tests
pytest

# Run a specific test file
pytest tests/test_schema.py

# Run with verbose output
pytest -v
```

### Lint & Type Check

```bash
# Lint
ruff check src/ tests/

# Format check
ruff format --check src/ tests/

# Type check
mypy src/

# All checks (before committing)
ruff check src/ tests/ && ruff format --check src/ tests/ && mypy src/ && pytest
```

### Scenario Tests (Integration Simulation)

Scenarios are Markdown files in `tests/scenarios/` describing supply chain disruptions in **Gherkin-style** (Given-When-Then). Each scenario defines:

- **Given (Context)**: Current state — inventory, orders, capacity
- **When (Trigger)**: The disruption event
- **Then (Expected Behavior)**: MCP tools to call, solutions to generate, HITL decisions

```bash
# List available scenarios
python scripts/test_runner.py --list

# Dry-run all scenarios (parse + display without invoking orchestrator)
python scripts/test_runner.py --dry-run

# Run a single scenario
python scripts/test_runner.py tests/scenarios/delay_shipment_po.md
```

**Available scenarios:**

| File | Type | Severity |
|------|------|----------|
| `delay_shipment_po.md` | Procurement / Supply Delay | Critical |
| `machine_breakdown.md` | Production / Equipment Failure | Critical |
| `demand_spike.md` | Sales / Demand Surge | High |
| `inventory_shortage.md` | Warehouse / Raw Material Shortage | High |
| `escalation_production_breakdown.md` | Escalation / Multi-tier | Critical |
| `escalation_stock_check.md` | Escalation / Inventory Review | High |

To add a new scenario, create a `tests/scenarios/<name>.md` file following the Gherkin-style template.
The `scripts/test_runner.py` auto-discovers all `.md` files in the directory.

---

## 🗄 Database Schemas

Axon uses PostgreSQL with five namespaced schemas:

| Schema | Purpose | Key Tables |
|--------|---------|------------|
| `axon_brain` | Agent memory, experience ledger, orchestrator logs | `experience_records`, `memory_store`, `plan_traces`, `orchestrator_logs` |
| `axon_plan` | Demand/Supply/Allocation planning records | `demands`, `supplies`, `allocations` |
| `axon_agents` | Negotiation rounds and agent proposals | `negotiation_rounds`, `agent_proposals`, `proposal_allocations` |
| `axon_mcp` | Tool registry and agent-tool assignments | `tool_registry`, `agent_tool_assignments` |
| `axon_board` | Control Tower state (weights, HITL queue, audit) | `business_weights`, `system_config`, `hitl_queue`, `approval_audit`, `board_events`, `board_kpis` |

```bash
# Run migrations (create all schemas + tables)
python src/axon/core/schema/migrate.py

# Seed sample data (10 plans, 4 HITL scenarios, weights, events)
python src/axon/core/schema/seed.py
```

---

## 🖥 Control Tower (Dashboard)

The Axon Control Tower is a live web dashboard backed by FastAPI + Next.js.

```bash
# Start backend API (port 8200)
.venv/bin/python3 -m uvicorn axon.dashboard.backend.app:create_app --factory \
    --host 0.0.0.0 --port 8200 --reload

# Start frontend (port 3010)
cd src/axon/dashboard/frontend && npm run dev -- -p 3010
```

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | System health, degradation level, pending approvals count |
| Plan History | `/plans` | All recorded plans with confidence, status, tags |
| Strategic Weights | `/weights` | Tune cost/delivery/quality/sustainability/flexibility weights |
| Pending Approvals | `/approvals` | HITL queue — approve or reject AI-generated plans |

API reference: `http://localhost:8200/docs` (Swagger UI)

---

*For the Agentic Era | [nsanguan/axon](https://github.com/nsanguan/axon)*

---

**Architect's Note:**
By going **Strictly MCP**, you've made the system incredibly clean. The `src/axon/connectors/mcp_oracle_ebs/` 
module no longer contains SQL or JDBC drivers; instead, it contains **Tool Definitions** and **Response Parsers**.
This is the most future-proof way to build AI-driven enterprise software.
