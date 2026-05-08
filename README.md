# 🧠 Axon

### **The Open-Source Agentic Planning OS (Pure MCP Architecture)**

**Axon** is a next-generation Supply Chain Planning (ASCP) framework built for the **Agentic AI era**. Unlike legacy systems that rely on direct database connections, Axon is **100% MCP-native**. It decouples "Enterprise Perception" from "Decision Cognition," treating every ERP and Knowledge Base as a standardized service.

---

## 🌟 Key Strategic Features

* **100% MCP-Native Architecture**: No direct DB connections (JDBC/ORDS). All systems—Oracle EBS, SAP, Odoo, and RAG—interface via the **Model Context Protocol**.
* **Plug-and-Play Connectors**: Swap between different ERP versions or vendors simply by switching the MCP host.
* **External Knowledge Mesh**: Leverages your **External RAG MCP Server** to verify every plan against corporate SOPs and legal constraints.
* **Universal Semantic Schema**: A unified Pydantic-based data language (`axon.core.schema`) that translates diverse MCP tool outputs into a single planning context.
* **Autonomous Negotiation**: A LangGraph-powered "Conflict Resolution" engine where 10+ departmental agents negotiate to find the highest utility outcome.
* **Self-Improving Logic**: An Experience Ledger that records the performance of AI-generated plans to refine future reasoning.

---

## 🏗 Modular Project Structure

```text
axon/
├── src/
│   └── axon/                      # Installable Python package
│       ├── __init__.py
│       ├── core/                  # Logic &amp; Shared Governance
│       │   ├── schema/            # Universal Semantic Models (Pydantic v2)
│       │   │   ├── base.py        # Demand, Supply, Allocation, MCPToolOutput
│       │   │   ├── demand.py      # Forecast &amp; Sales models
│       │   │   ├── supply.py      # Inventory &amp; Production models
│       │   │   └── allocation.py  # Matching &amp; Optimization models
│       │   ├── config.py          # Typed settings (pydantic-settings)
│       │   ├── learning/          # Experience Ledger &amp; Decision Memory
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
├── infra/                         # Docker Compose &amp; deployment
│   └── docker-compose.yml
├── pyproject.toml                 # Build &amp; Dependencies
├── requirements.txt               # Full tech stack (pip install)
├── requirements-dev.txt           # Dev tooling (pytest, ruff, mypy)
├── AGENTS.md                      # Agent instructions (OpenAI / Cursor / Copilot)
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

### **Phase 4: Feedback & Control (Month 5)**

* Launch **Admin Control Tower** for real-time strategic weight tuning.
* Activate the **Experience Ledger** to log the success/failure of plans.
* Enable **Human-in-the-loop (HITL)** for final plan approvals.

### **Phase 5: Scale & Governance (Month 6+)**

* Secure Bi-directional MCP tool-calls for ERP write-backs.
* Finalize RBAC and AI Guardrails for enterprise safety.

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

*For the Agentic Era | [nsanguan/axon](https://github.com/nsanguan/axon)

---

**Architect's Note:**
By going **Strictly MCP**, you've made the system incredibly clean. The `src/axon/connectors/mcp_oracle_ebs/` 
module no longer contains SQL or JDBC drivers; instead, it contains **Tool Definitions** and **Response Parsers**.
 This is the most future-proof way to build AI-driven enterprise software.