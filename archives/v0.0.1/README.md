# Axon (Agentic-ASCP) 🧠📦

**"The AI-Native Nervous System for Modern Supply Chains"**

Axon is an open-source, AI-native Supply Chain Planning (ASCP) engine designed to transform traditional supply chain management into a real-time, autonomous nerve system.

Axon is **ERP-agnostic**: it interfaces with any System of Record via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io). The core reasoning layer (agents + orchestrator) never speaks directly to any ERP — all integration is handled through swappable MCP server adapters.

- **Reasoning**: [PydanticAI](https://ai.pydantic.dev/) — structured, type-safe agent outputs
- **Orchestration**: [LangGraph](https://langchain-ai.github.io/langgraph/) — stateful, resumable planning workflows
- **Integration**: [FastMCP](https://github.com/jlowin/fastmcp) — ERP adapters as MCP servers (SSE transport)
- **License**: Apache 2.0

---

## Mission

To democratize advanced planning logic and provide a transparent, explainable alternative to legacy monolithic ASCP systems like Oracle ASCP, SAP APO, and similar enterprise applications.

---

## Architecture

Axon decouples planning logic from data storage. By using MCP, Axon can orchestrate supply chain actions across Odoo, SAP, Oracle, and custom legacy databases **without changing a single line of core reasoning code**.

```
┌─────────────────────────────────────────────────────────────────┐
│                     NORTHBOUND (User/System)                    │
│           REST API · Chat UI · ERP Dashboards · Alerts          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                   ORCHESTRATION LAYER                           │
│                LangGraph — AxonState + Workflow                  │
│      sync_demand → run_planning → update_pegging → notify       │
└──────────────┬──────────────────────────┬───────────────────────┘
               │                          │
┌──────────────▼──────────┐  ┌────────────▼──────────────────────┐
│   Planning Manager      │  │       Executive Agent             │
│   (PydanticAI Agent)    │  │       (PydanticAI Agent)          │
│                         │  │                                   │
│  Purchase Cluster:      │  │  Escalation authority —           │
│  Buyer → Manager →      │  │  resolves low-confidence &        │
│  Director               │  │  unresolvable exceptions          │
└──────────────┬──────────┘  └────────────┬──────────────────────┘
               │                          │
               └──────────┬───────────────┘
                           │  MCP (SSE)
┌──────────────────────────▼───────────────────────────────────────┐
│                    MCP SERVER ADAPTERS                           │
│   mcp-ascp-planning  │  mcp-ascp-procurement  │  mcp-ascp-inv.  │
│   (FastMCP / SSE)    │  (FastMCP / SSE)        │  (FastMCP / SSE)│
└──────────────┬──────────────────────────────────────────────────┘
               │  XML-RPC / REST / SDK
┌──────────────▼───────────────────────────────────────────────────┐
│               SYSTEMS OF RECORD (plug any ERP here)              │
│   Odoo  ·  SAP  ·  Oracle  ·  Custom Legacy  ·  APIs            │
└──────────────────────────────────────────────────────────────────┘
```

**Key design insight**: To connect Axon to a new ERP, you only need to write a new MCP server adapter. The Planning Manager, Executive Agent, and LangGraph workflow never change.

---

## Core Concepts

### Planning Cycle
A single end-to-end execution of the Axon workflow, identified by a `cycle_id` (e.g. `CYCLE-2026-05-08-001`). Each cycle:
1. Syncs demand from the System of Record
2. Detects shortages against available supply
3. Allocates stock or triggers procurement
4. Logs full AI reasoning to the record's activity log (Chatter for Odoo)
5. Creates Human-in-the-Loop approval gates for critical decisions

### Pegging Ledger
The central planning artifact: a record that links a demand item (e.g. a Sales Order line) to its supply allocation (e.g. a Purchase Order line or on-hand stock). Axon reads and writes pegging records to track coverage status.

### AI Reasoning Trail (Explainability)
Every AI decision is posted as a structured note on the affected record, visible directly in the ERP UI. Humans can always see *why* Axon made a change, without leaving their ERP.

### Human-in-the-Loop (HITL)
When Axon encounters a decision that exceeds confidence thresholds (e.g. price increase > 10%, lead time > 14 days), it creates an approval task for a human planner and pauses the workflow until the task is resolved.

---

## Repository Structure

```
axon/
├── LICENSE                               # Apache 2.0
├── README.md                             # This file
├── pyproject.toml                        # Python project (axon-ascp)
├── AGENT.md                              # AI agent policy document
├── PROJECT_PLAN.md                       # Architecture & development phases
│
├── core/
│   ├── config.py                         # pydantic-settings BaseSettings
│   ├── odoo_client.py                    # Odoo XML-RPC adapter (reference impl.)
│   └── skills/                           # Executable domain skill modules
│       ├── base_skill.py
│       ├── communication_skills.py       # AI reasoning → ERP activity log
│       ├── planning_skills.py            # Pegging ledger + demand/supply streams
│       ├── procurement_skills.py         # RFQ, PO, vendor lead time
│       ├── inventory_skills.py           # Stock quant, moves, reservations
│       ├── sales_skills.py               # Sale order reads (demand source)
│       └── impact_analysis_skill.py      # Cost/time delta analysis
│
├── mcp_servers/
│   ├── mcp-ascp-planning/                # Planning MCP adapter
│   ├── mcp-ascp-procurement/             # Procurement MCP adapter
│   └── mcp-ascp-inventory/              # Inventory MCP adapter
│
├── agents/
│   ├── planning_manager.py               # Planning Manager (PydanticAI)
│   ├── executive_agent.py                # Executive Agent (PydanticAI)
│   └── purchase/
│       ├── buyer_agent.py                # Buyer: vendor selection + RFQ
│       ├── manager_agent.py              # Purchase Manager: impact analysis
│       └── director_agent.py             # Purchase Director: final approval
│
└── orchestrator/
    ├── state.py                          # AxonState TypedDict
    ├── purchase_workflow.py              # Purchase sub-graph (LangGraph)
    └── workflow.py                       # Main planning workflow (LangGraph)
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- An ERP with an available MCP adapter (Odoo bundled; others: implement your own)

### Installation

```bash
git clone https://github.com/nsanguan/axon.git
cd axon
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Configuration

```bash
cp .env.example .env
# Edit .env with your ERP credentials and LLM API keys
```

**Minimum `.env` for Odoo adapter:**

```bash
ODOO_URL=http://localhost:8069
ODOO_DB=your_database
ODOO_USER=admin
ODOO_API_KEY=your_odoo_api_key

ANTHROPIC_API_KEY=your_anthropic_key

MCP_PLANNING_PORT=8001
MCP_PROCUREMENT_PORT=8002
MCP_INVENTORY_PORT=8003
```

### Start MCP Servers

```bash
# In separate terminals:
fastmcp run mcp_servers/mcp-ascp-planning/server.py --transport sse --port 8001
fastmcp run mcp_servers/mcp-ascp-procurement/server.py --transport sse --port 8002
fastmcp run mcp_servers/mcp-ascp-inventory/server.py --transport sse --port 8003
```

### Run Tests

```bash
pytest tests/ -v
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Agent Framework | [PydanticAI](https://ai.pydantic.dev/) |
| Orchestration | [LangGraph](https://langchain-ai.github.io/langgraph/) |
| MCP Servers | [FastMCP](https://github.com/jlowin/fastmcp) |
| Config | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| Python | 3.12+ |
| Odoo Connector | `xmlrpc.client` (stdlib) |
| LLM | Anthropic Claude (default), or any PydanticAI-compatible model |

---

## Adding a New ERP Adapter

1. Create `mcp_servers/mcp-ascp-<domain>/server.py` using FastMCP
2. Implement the standard Axon tool interface (`axon_get_*`, `axon_create_*`, `axon_post_comment`, `axon_create_activity`)
3. Add the server URL to `core/config.py`
4. No changes to agents or orchestrator are needed

See [PROJECT_PLAN.md](PROJECT_PLAN.md) for the full MCP tool interface specification.

---

## Roadmap

- [x] Core skill layer (planning, procurement, inventory, communication)
- [x] FastMCP server adapters (Odoo reference implementation)
- [x] PydanticAI agents (Planning Manager, Executive, Purchase Cluster)
- [x] LangGraph orchestration with HITL interrupt gates
- [ ] SAP adapter (mcp-ascp-sap-planning)
- [ ] Oracle NetSuite adapter
- [ ] Web UI for planning cycle monitoring
- [ ] Docker Compose stack for local development
- [ ] Agent evaluation harness (reproducible planning scenarios)

---

## Contributing

Contributions are welcome! Please read [AGENT.md](AGENT.md) for coding policies and MCP tool interface requirements.

```bash
# Run linter
ruff check .

# Run tests
pytest tests/ -v
```

---

## License

Licensed under the [Apache License 2.0](LICENSE).

Copyright 2026 Axon Contributors
