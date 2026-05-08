# Axon (Agentic-ASCP) 🧠📦 — Project Plan

> **Project**: Axon — AI-Native Supply Chain Planning Engine
> **Tagline**: "The AI-Native Nervous System for Modern Supply Chains"
> **Mission**: Democratize advanced planning logic with a transparent, explainable alternative to legacy monolithic ASCP systems.
> **Architecture**: ERP-agnostic. Any System of Record (Odoo, SAP, Oracle, custom DB) connects via MCP. PydanticAI agents reason over universal `core.schema` models. LangGraph orchestrates the planning workflow.
> **License**: Apache 2.0

---

## Architectural Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        THE BRAINS (agents/)                              │
│   Planning Agent · Executive Agent · Buyer · Manager · Director          │
│   ✓ Only speak core.schema models (AxonDemandStream, AxonPlanningDecision, …)   │
│   ✓ Zero knowledge of which ERP they are connected to                   │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │  PydanticAI MCPServerSSE
┌────────────────────────────▼─────────────────────────────────────────────┐
│                  THE NERVOUS SYSTEM (orchestrator/)                      │
│             LangGraph · AxonState · graphs/main.py                       │
│   ✓ Calls skills via adapter methods — no ERP model names visible        │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                   THE FOUNDATION (core/)                                 │
│  core/schema/     — universal AxonDemandItem, AxonSupplyItem, AxonAllocation         │
│  core/protocols/  — AxonDemandProvider, AxonSupplyProvider, AxonAllocationWriter …   │
│  core/skills/     — Odoo-specific skill modules (Odoo adapter impl.)     │
│  core/odoo_client.py — AxonOdooXMLRPCClient (XML-RPC, no direct SQL)        │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                     THE BRIDGES (adapters/)                              │
│  adapters/mcp_client.py     — MCPServerSSE factory                       │
│  adapters/mapping/odoo.py   — Odoo dict → universal schema mapper        │
└──────────┬─────────────────────────────────────────────────────┬─────────┘
           │ SSE/MCP                                             │
┌──────────▼──────────────┐     ┌──────────────────────────────▼─────────┐
│   THE SENSORS — Odoo    │     │        THE SENSORS — Future ERPs        │
│  mcp_servers/odoo/      │     │   mcp_servers/sap/server.py             │
│  ├── planning/server.py │     │   mcp_servers/legacy_db/server.py       │
│  ├── procurement/       │     │   (Add any ERP here — agents never      │
│  └── inventory/         │     │    change, only MCP servers change)     │
└──────────┬──────────────┘     └─────────────────────────────────────────┘
           │ XML-RPC
┌──────────▼──────────────────────────────────────────────────────────────┐
│                    System of Record (Odoo)                              │
│   Planning buffer models · sale.order · purchase.order · stock.quant    │
│   (Details are inside the Odoo MCP adapter — not visible to agents)     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Core Principles

| Principle | Rule |
|-----------|------|
| **ERP-agnostic core** | Agents import only `core.schema`, never ERP model names |
| **MCP-first** | Data flows through MCP tools — not direct XML-RPC from agents |
| **No direct SQL** | All ERP calls via `AxonOdooXMLRPCClient` XML-RPC |
| **Universal schema** | `AxonDemandItem`, `AxonSupplyItem`, `AxonAllocation` are the agent lingua franca |
| **AI Reasoning Trail** | Every ERP write auto-posts reasoning to the ERP audit trail |
| **HITL gate** | Director Agent must create a human approval task before confirming high-impact POs |
| **Adapter boundary** | ERP model names must NEVER appear outside `core/skills/`, `adapters/`, or `mcp_servers/<erp>/` |

---

## Directory Structure

```
axon/
├── LICENSE                               # Apache 2.0
├── .env                                  # Credentials (never commit)
├── AGENT.md                              # Agent policy document
├── PROJECT_PLAN.md                       # This file
├── pyproject.toml                        # Root Python project (axon-ascp)
│
├── core/                                 # THE FOUNDATION
│   ├── config.py                         # pydantic-settings BaseSettings
│   ├── odoo_client.py                    # AxonOdooXMLRPCClient (Odoo adapter detail)
│   ├── schema/                           # ★ Universal ERP-agnostic data models
│   │   ├── demand.py                     # AxonDemandItem, AxonDemandStream, AxonDemandSource
│   │   ├── supply.py                     # AxonSupplyItem, AxonSupplyStream, AxonSupplySource
│   │   └── allocation.py                 # AxonAllocation, AxonPlanningDecision, AxonShortageItem
│   ├── protocols/                        # Abstract Protocol contracts
│   │   └── __init__.py                   # AxonDemandProvider, AxonSupplyProvider, AxonAllocationWriter …
│   └── skills/                           # Odoo-specific skill modules
│       ├── base_skill.py
│       ├── communication_skills.py       # mail.thread + mail.activity (Chatter/HITL)
│       ├── planning_skills.py            # Pegging ledger + demand/supply buffer ops
│       ├── procurement_skills.py         # RFQ, PO, vendor lead time ops
│       ├── inventory_skills.py           # Stock quant, moves, reservation ops
│       ├── sales_skills.py               # sale.order read ops (demand source)
│       └── impact_analysis_skill.py      # Cost/time impact analysis (read-only)
│
├── adapters/                             # THE BRIDGES
│   ├── mcp_client.py                     # MCPServerSSE factory for agents
│   └── mapping/
│       └── odoo.py                       # Odoo dict → universal schema mapper
│
├── mcp_servers/                          # THE SENSORS — one subfolder per ERP
│   ├── odoo/                             # Odoo MCP adapter (reference implementation)
│   │   ├── planning/server.py
│   │   ├── procurement/server.py
│   │   └── inventory/server.py
│   ├── sap/server.py                     # SAP placeholder (RFC/OData stubs)
│   └── legacy_db/server.py              # Legacy SQL DB placeholder
│
├── agents/                               # THE BRAINS — ERP-agnostic
│   ├── planning.py                       # Planning Manager Agent
│   ├── executive.py                      # Executive Agent
│   └── purchase/
│       ├── buyer.py
│       ├── manager.py
│       └── director.py
│
└── orchestrator/                         # THE NERVOUS SYSTEM
    ├── state.py                          # AxonState TypedDict
    └── graphs/
        ├── main.py                       # Main LangGraph StateGraph
        └── purchase.py                   # Purchase sub-graph
```

> **Boundary rule**: ERP-specific model names must ONLY appear inside `core/skills/`, `adapters/mapping/odoo.py`, and `mcp_servers/odoo/`. Everything else is ERP-agnostic.

---

## Universal Schema (`core/schema/`)

The agent lingua franca. No ERP imports allowed here.

### `AxonDemandItem`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Universal demand ID (`odoo:demand:42`, `sap:pir:X`) |
| `source_type` | `AxonDemandSource` | SALE_ORDER / FORECAST / MPS / MRP / MANUAL / TRANSFER |
| `product_id` | `str` | Universal product reference |
| `demand_qty` | `float` | Total demand quantity |
| `confirmed_qty` | `float` | Already confirmed/delivered |
| `demand_date` | `date` | Required delivery date |
| `status` | `AxonDemandStatus` | OPEN / PEGGED / PARTIAL / EXCEPTION / CLOSED |
| `open_qty` | property | `demand_qty - confirmed_qty` |

### `AxonSupplyItem`

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Universal supply ID |
| `source_type` | `AxonSupplySource` | ON_HAND / PURCHASE_ORDER / MANUFACTURING_ORDER / TRANSFER |
| `supply_qty` | `float` | Total available quantity |
| `available_qty` | `float` | Unallocated quantity |
| `supply_date` | `date` | Expected availability date |
| `lead_days` | `int \| None` | Lead time in days |

### `AxonAllocation` (pegging record)

| Field | Type | Description |
|-------|------|-------------|
| `demand_id` | `str` | Links to `AxonDemandItem.id` |
| `supply_id` | `str` | Links to `AxonSupplyItem.id` |
| `allocated_qty` | `float` | Pegged quantity |
| `status` | `AxonAllocationStatus` | DRAFT / FIRM / RELEASED / PARTIAL / EXCEPTION / CANCELLED |
| `confidence` | `float` | Agent confidence 0–1 |
| `ai_context` | `str` | Human-readable reasoning |

### `AxonPlanningDecision`

Primary output of the Planning Agent.

| Field | Description |
|-------|-------------|
| `action` | ALLOCATE / SHORTAGE / EXCEPTION / HITL_REQUIRED / NO_ACTION |
| `allocations` | Pegging decisions |
| `shortages` | Products that cannot be covered |
| `confidence` | < 0.7 → escalate to Executive |

---

## Adapter Protocol Layer (`core/protocols/`)

```python
class AxonDemandProvider(Protocol):
    def get_demand_stream(self, cycle_id: str, **filters) -> AxonDemandStream: ...
    def sync_demand(self, cycle_id: str, ai_context: str) -> int: ...

class AxonSupplyProvider(Protocol):
    def get_supply_stream(self, cycle_id: str, **filters) -> AxonSupplyStream: ...
    def get_on_hand(self, product_id: str, location_ref: str | None) -> float: ...

class AxonAllocationWriter(Protocol):
    def write_allocation(self, allocation: AxonAllocation, ai_context: str) -> int: ...
    def update_allocation(self, erp_id: int, qty: float, status: str, ai_context: str) -> bool: ...

class AxonActivityWriter(Protocol):   # HITL gate
    def create_hitl_activity(self, ...) -> int: ...
    def is_activity_done(self, activity_id: int) -> bool: ...

class AxonReasoningLogger(Protocol):  # Audit trail
    def log_reasoning(self, model, record_id, action_taken, ai_context, ...) -> int: ...
```

**To add a new ERP**: implement these protocols for your ERP, create `mcp_servers/<erp>/server.py` that exposes the standard tool names, update `.env` with the new port. Agents never change.

---

## MCP Server Layer (`mcp_servers/`)

### Odoo Adapter (`mcp_servers/odoo/`)

**Planning tools** (port `MCP_PLANNING_PORT`):

| Tool | Description |
|------|-------------|
| `axon_get_ledger` | Read pegging/allocation records |
| `axon_update_allocation` | Write allocation + post reasoning to audit trail |
| `axon_create_exception` | Mark allocation as exception |
| `axon_check_shortage` | Demand vs supply gap analysis |
| `axon_sync_demand_stream` | Pull confirmed SOs into demand buffer |
| `axon_get_supply_stream` | Read supply buffer |
| `axon_post_comment` | Post AI reasoning to ERP audit trail |
| `axon_create_activity` | Create HITL approval task |
| `axon_check_activity_done` | Poll HITL completion |

**Procurement tools** (port `MCP_PROCUREMENT_PORT`):

| Tool | Description |
|------|-------------|
| `axon_get_rfq_list` | List draft purchase orders |
| `axon_create_rfq` | Create RFQ for shortage |
| `axon_confirm_po` | Confirm PO (Director only) |
| `axon_get_vendor_lead_time` | Query vendor lead times |
| `axon_analyse_rfq_impact` | Cost/time impact classification |

**Inventory tools** (port `MCP_INVENTORY_PORT`):

| Tool | Description |
|------|-------------|
| `axon_get_stock_quant` | On-hand stock levels |
| `axon_get_incoming_moves` | Scheduled receipts |
| `axon_get_outgoing_demand` | Open outgoing moves |
| `axon_reserve_stock` | Reserve stock against demand |

---

## Agent Layer (`agents/`)

All agents are ERP-agnostic. They import from `core.schema`, connect via `adapters.mcp_client`.

### Planning Agent (`planning.py`)

1. `axon_sync_demand_stream` → refresh demand buffer
2. `axon_get_ledger` + `axon_check_shortage` → analyse gaps
3. Sufficient stock → `axon_update_allocation` → `action=ALLOCATE`
4. Shortage → `action=SHORTAGE` (Supervisor routes to Purchase Cluster)
5. Exception → `axon_create_activity` → `action=HITL_REQUIRED`

### Purchase Cluster (`purchase/`)

```
Buyer    → vendor selection + axon_create_rfq
Manager  → axon_analyse_rfq_impact → acceptable / warning / critical
Director → acceptable: axon_confirm_po
           critical:   axon_create_activity (HITL gate) → wait → axon_confirm_po
```

Impact thresholds:

| Metric | Warning | Critical (HITL) |
|--------|---------|-----------------|
| Price increase | > 5% | > 10% |
| Extra lead time | > 7 days | > 14 days |

### Executive Agent (`executive.py`)

Invoked when confidence < 0.7. Connects to all three MCP servers. Returns `AxonExecutiveSummary`.

---

## Orchestrator (`orchestrator/`)

Main workflow (`graphs/main.py`):

```
sync_demand_node      → _planning.get_demand_stream()
sync_supply_node      → _planning.get_supply_stream() + get_ledger()
planning_manager_node → Planning Agent via MCP
supervisor_node       → router (no LLM)
  ├─ SHORTAGE        → purchase_cluster_node
  ├─ HITL_REQUIRED   → hitl_checkpoint_node
  ├─ LOW_CONF        → executive_node
  └─ ALLOCATE        → update_pegging_node → notify_node → END
```

**Constraint**: The orchestrator never contains ERP model names. All model references stay inside `core/skills/`.

---

## Configuration (`.env`)

```dotenv
ODOO_URL=http://your-odoo-host:8069
ODOO_DB=your_database
ODOO_USER=admin
ODOO_API_KEY=your_api_key

LLM_PLANNING_MODEL=anthropic:claude-sonnet-4-6
LLM_BUYER_MODEL=anthropic:claude-sonnet-4-6
LLM_EXECUTIVE_MODEL=anthropic:claude-sonnet-4-6

MCP_PLANNING_PORT=8001
MCP_PROCUREMENT_PORT=8002
MCP_INVENTORY_PORT=8003

# Uncomment when adding new ERP adapters:
# MCP_SAP_PLANNING_PORT=8010
# MCP_LEGACY_DB_PORT=8011
```

---

## Running

```bash
# Install
pip install -e .

# Start Odoo MCP adapter servers
python mcp_servers/odoo/planning/server.py &
python mcp_servers/odoo/procurement/server.py &
python mcp_servers/odoo/inventory/server.py &

# Run tests
pytest tests/ -v

# Schema/import tests only (no Odoo needed)
pytest tests/ -v -k "schema or adapter or protocol"
```

---

## Checklist

### Foundation
- [x] `core/schema/` — universal AxonDemandItem, AxonSupplyItem, AxonAllocation, AxonPlanningDecision
- [x] `core/protocols/` — 5 adapter Protocol contracts
- [x] `core/skills/` — Odoo skill modules
- [x] `adapters/mcp_client.py` — MCPServerSSE factory
- [x] `adapters/mapping/odoo.py` — Odoo dict → universal schema mappers

### MCP Servers
- [x] `mcp_servers/odoo/planning/server.py`
- [x] `mcp_servers/odoo/procurement/server.py`
- [x] `mcp_servers/odoo/inventory/server.py`
- [x] `mcp_servers/sap/server.py` — SAP placeholder
- [x] `mcp_servers/legacy_db/server.py` — Legacy DB placeholder

### Agents
- [x] `agents/planning.py`
- [x] `agents/executive.py`
- [x] `agents/purchase/buyer.py`
- [x] `agents/purchase/manager.py`
- [x] `agents/purchase/director.py`

### Orchestrator
- [x] `orchestrator/state.py` — ERP-agnostic `AxonState`
- [x] `orchestrator/graphs/main.py`
- [x] `orchestrator/graphs/purchase.py`

### Odoo Addon
- [ ] `axon_core` Odoo addon with planning/demand/supply buffer models
- [ ] All buffer models have `mail.thread` + `mail.activity.mixin`
- [ ] XML-RPC access verified from Python
