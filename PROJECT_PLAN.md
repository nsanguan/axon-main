# EraOwl-Agentic-ASCP — Project Plan

> **Project**: EraOwl Agentic Supply Chain Planning (ASCP)
> **Goal**: Replace legacy Oracle ASCP with a real-time, event-driven, AI-native supply chain planning system layered over Odoo 19.4 alpha.
> **Architecture**: Multi-layer Southbound/Northbound pattern — Odoo as the system of record, FastMCP servers as the southbound layer, PydanticAI agents as the reasoning layer, and LangGraph as the orchestration/state layer.

---

## Architectural Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     NORTHBOUND (User/System)                    │
│           REST API · Chat UI · ERP Dashboards · Email           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│              ORCHESTRATION LAYER  (Phase 4)                     │
│               LangGraph — ASCPState + Workflow                  │
│     sync_demand → run_planning → update_pegging → notify        │
└──────────────┬──────────────────────────┬───────────────────────┘
               │                          │
┌──────────────▼──────────┐  ┌────────────▼──────────────────────┐
│    AGENT LAYER (Ph 3)   │  │       AGENT LAYER  (Ph 3)         │
│   Planning Manager      │  │       Executive Agent             │
│   (PydanticAI Agent)    │  │       (PydanticAI Agent)          │
└──────────────┬──────────┘  └────────────┬──────────────────────┘
               │                          │
┌──────────────▼──────────────────────────▼───────────────────────┐
│              SOUTHBOUND MCP SERVERS  (Phase 2)                  │
│  mcp-ascp-planning  │  mcp-ascp-procurement │  mcp-ascp-inv.    │
│  (FastMCP / SSE)    │  (FastMCP / SSE)      │  (FastMCP / SSE)  │
└──────────────┬──────────────────────────────────────────────────┘
               │  XML-RPC / JSON-2 API
┌──────────────▼───────────────────────────────────────────────────┐
│                   ODOO 19.4 alpha  (System of Record)            │
│  era.ascp.pegging.ledger · era.ascp.demand.stream                │
│  era.ascp.supply.stream  · sale.order · purchase.order           │
│  stock.move · mrp.production · product.product                   │
└──────────────────────────────────────────────────────────────────┘
```

### Core Principles

- **No Odoo patching**: Everything via inheritance and modular addons
- **No direct SQL**: All Odoo calls via `OdooXMLRPCClient` (XML-RPC only)
- **Naming convention**: `mcp-ascp-` prefix for all specialized MCP servers
- **All tool I/O**: Pydantic `BaseModel` with `Field(description=...)` on every param
- **`ai_context`**: Required field on every MCP tool input — logs the agent's reasoning
- **Atomicity**: Multi-step Odoo operations wrapped in a single custom Odoo method
- **AI Reasoning in Chatter**: Every tool that writes or updates an Odoo record MUST also call `communication_skills.post_ai_reasoning()` to post the `ai_context` to the record's Chatter — so humans can always read why the AI made a change

---

## Directory Structure

```
EraOwl-Agentic-ASCP/
├── .env                                  # Credentials (never commit)
├── .gitignore
├── .github/skills/                       # Skill reference docs (Markdown, read-only)
├── AGENT.md                              # Agent policy document
├── PROJECT_PLAN.md                       # This file
├── pyproject.toml                        # Root Python project config
│
├── core/                                 # Shared infrastructure
│   ├── __init__.py
│   ├── config.py                         # pydantic-settings BaseSettings
│   ├── odoo_client.py                    # OdooXMLRPCClient wrapper
│   └── skills/                           # ★ Executable Python skill modules
│       ├── __init__.py
│       ├── communication_skills.py       # ★ mail.activity + message_post (AI→Chatter)
│       ├── planning_skills.py            # Pegging ledger + demand/supply stream ops
│       ├── procurement_skills.py         # RFQ, PO, vendor lead time ops
│       ├── inventory_skills.py           # Stock quant, moves, reservation ops
│       ├── sales_skills.py               # sale.order, SO lines ops
│       └── base_skill.py                 # Base class shared by all skill modules
│
├── mcp_servers/
│   ├── mcp-ascp-planning/                # Phase 2A — primary planning server
│   │   ├── pyproject.toml
│   │   ├── server.py                     # FastMCP entry point (SSE transport)
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── pegging.py                # Pegging ledger tools
│   │       └── demand.py                 # Demand stream tools
│   │
│   ├── mcp-ascp-procurement/             # Phase 2B — procurement server
│   │   ├── pyproject.toml
│   │   ├── server.py
│   │   └── tools/
│   │       └── __init__.py
│   │
│   └── mcp-ascp-inventory/               # Phase 2C — inventory server
│       ├── pyproject.toml
│       ├── server.py
│       └── tools/
│           └── __init__.py
│
├── agents/
│   ├── __init__.py
│   ├── planning_manager.py               # Phase 3 — Planning Manager Agent
│   ├── executive_agent.py                # Phase 3 — Executive Agent
│   └── purchase/                         # Phase 3 — Purchase Cluster (Hierarchy)
│       ├── __init__.py
│       ├── buyer_agent.py                # Buyer: vendor selection + RFQ creation
│       ├── manager_agent.py              # Purchase Manager: cost/time impact analysis
│       └── director_agent.py             # Purchase Director: final approval + HITL gate
│
└── orchestrator/
    ├── __init__.py
    ├── state.py                          # Phase 4 — ASCPState TypedDict
    ├── purchase_workflow.py              # Phase 4 — Purchase Sub-graph (Buyer→Manager→Director)
    └── workflow.py                       # Phase 4 — Main LangGraph StateGraph
```

> **Note**: `.github/skills/` contains the **Markdown reference docs** used by AI agents to understand Odoo conventions. `core/skills/` contains the **executable Python modules** that implement those conventions as callable functions.

---

## Setup Phase: Core Skills Layer

**Goal**: Establish the shared Python skill modules in `core/skills/` that all MCP servers import. This is the single place where all Odoo domain logic lives — MCP tools are thin wrappers over these skills.

### `base_skill.py`
Abstract base class providing `self.client: OdooXMLRPCClient` and the shared `post_ai_reasoning()` delegation. All other skill classes inherit from this.

### `communication_skills.py` ★ (New — AI Reasoning in Chatter)

The most critical skill module. Provides two capabilities:

**1. `post_ai_reasoning(model, record_id, ai_context, action_taken)`**
- Calls `message_post` on the Odoo record via XML-RPC
- Posts a formatted Chatter message: `[AI-ASCP] <action_taken>\nReason: <ai_context>`
- Used automatically by every write/update operation in all other skill modules
- The model must have `mail.thread` (required for all `era.ascp.*` models)

**2. `create_activity(model, record_id, activity_type, summary, note, deadline)`**
- Creates a `mail.activity` on the record to assign a follow-up task to a human user
- Used when an exception requires human intervention
- Activity types: `mail.mail_activity_data_todo`, `mail.mail_activity_data_warning`

**XML-RPC call pattern for `message_post`**:
```python
client.call_method(
    "era.ascp.pegging.ledger",
    "message_post",
    [record_id],
    body=f"<b>[AI-ASCP]</b> {action_taken}<br/><i>Reason: {ai_context}</i>",
    message_type="comment",
    subtype_xmlid="mail.mt_note",
)
```

**Chatter posting rule (MANDATORY)**:
> Every skill function that calls `client.write()`, `client.create()`, or `client.call_method()` (business action) **must** call `self.post_ai_reasoning()` immediately after. No silent writes.

### `impact_analysis_skill.py` (New — Cost/Time Impact Analysis)

A **read-only** skill that compares a proposed procurement action against the Odoo baseline (`product.supplierinfo`) and classifies the impact:

- **`analyse_rfq_lines(partner_id, proposed_lines)`** — per-line impact: `price_delta_pct`, `lead_delta_days`, `cost_delta`, `classification` (`acceptable` / `warning` / `critical`), plus a `_summary` aggregate with `hitl_required: bool`.
- **`analyse_po_for_approval(po_id)`** — re-analyse an existing PO for Director pre-approval.

**Thresholds**:

| Metric | Warning | Critical (HITL required) |
|--------|---------|---------------------------|
| Price increase | > 5% | > 10% |
| Extra lead time | > 7 days | > 14 days |

The skill never writes to Odoo. Calling agents post results to Chatter via `communication_skills`.

### `planning_skills.py`
Wraps all `era.ascp.pegging.ledger` and `era.ascp.demand.stream` / `era.ascp.supply.stream` operations. Each write method auto-posts to chatter via `communication_skills`.

### `procurement_skills.py`
Wraps `purchase.order`, `purchase.order.line`, `product.supplierinfo` operations. PO confirmations, RFQ creation, and vendor price updates all post reasoning to chatter.

### `inventory_skills.py`
Wraps `stock.quant`, `stock.move`, and custom reservation methods. Stock reservations post reasoning to chatter.

### `sales_skills.py`
Wraps `sale.order` and `sale.order.line` read operations (read-only — demand sync source).

---

## Phase 1: Core Odoo Models (Odoo Addon)

**Goal**: Define the data foundation in Odoo — the three core ASCP streams/ledger models that all agents read from and write to.

**Deliverables**:
- New Odoo addon: `era_ascp_core` (installed at `/u01/erp/Odoo/odoo-server/addons`)
- Model `era.ascp.pegging.ledger` — links demand to supply allocations
- Model `era.ascp.demand.stream` — unified demand view (sales, forecasts, MPS)
- Model `era.ascp.supply.stream` — unified supply view (POs, MOs, transfers, stock)

**Key Fields — `era.ascp.pegging.ledger`**:

| Field | Type | Description |
|-------|------|-------------|
| `name` | Char | Pegging reference |
| `demand_source_ref` | Char | Source demand record (e.g. SO line ref) |
| `supply_source_ref` | Char | Source supply record (e.g. PO line ref) |
| `product_id` | Many2one → `product.product` | Planned product |
| `allocated_qty` | Float | Quantity pegged/allocated |
| `uom_id` | Many2one → `uom.uom` | Unit of measure |
| `status` | Selection | `draft`, `firm`, `released`, `partial`, `exception` |
| `plan_date` | Date | Planned fulfillment date |
| `demand_date` | Date | Required by date |
| `ai_last_action` | Text | Last AI reasoning logged |

**Key Fields — `era.ascp.demand.stream`**:

| Field | Type | Description |
|-------|------|-------------|
| `source_type` | Selection | `sale_order`, `forecast`, `mps`, `manual` |
| `source_ref` | Char | External reference |
| `product_id` | Many2one → `product.product` | Planned product |
| `demand_qty` | Float | Gross demand quantity |
| `confirmed_qty` | Float | Confirmed / pegged quantity |
| `demand_date` | Date | Required date |
| `state` | Selection | `open`, `pegged`, `exception`, `closed` |

**Policies**:
- Follow `odoo-module-development` and `odoo-orm` skills exactly
- Every model must have `security/ir.model.access.csv` entry
- Use `mail.thread` + `mail.activity.mixin` on **all** `era.ascp.*` models — required for AI Chatter posting
- Module version format: `19.4.1.0.0`
- Add `tracking=True` on key fields (`status`, `allocated_qty`, `state`) so field changes also appear in chatter automatically

---

## Phase 2: Southbound MCP Servers (The Connector Layer)

**Goal**: Expose domain-specific Odoo operations as typed, AI-callable FastMCP tools. Each server is an independent Python package communicating via SSE transport.

All tools follow these rules:
- Every tool input **must** include `ai_context: str` — passed to Odoo on every write
- Write tools auto-post to Chatter via `communication_skills` inside the skill layer
- Read tools (`ascp_get_*`) are lightweight — no Chatter post needed
- Tools are thin wrappers over `core/skills/` — no Odoo logic in tool code itself

---

### mcp-ascp-planning (Phase 2A)

This is the primary MCP server. All planning agents connect here.

#### Planning & Ledger Tools

| Tool | Skill Used | Operation |
|------|-----------|----------|
| `ascp_get_ledger` | `planning_skills` | `search_read` on `era.ascp.pegging.ledger` — filter by product, status, date |
| `ascp_update_allocation` | `planning_skills` | `write` allocated_qty + status → auto-posts to Chatter |
| `ascp_sync_demand_stream` | `planning_skills` + `sales_skills` | Pull confirmed SOs → write to `era.ascp.demand.stream` |
| `ascp_get_supply_stream` | `planning_skills` | `search_read` on `era.ascp.supply.stream` — filter by product, date range |
| `ascp_check_shortage` | `planning_skills` + `inventory_skills` | Compare demand vs available stock → return shortage list |
| `ascp_create_exception` | `planning_skills` | Set status=`exception` + auto-posts Chatter with reason |

#### Communication Tools (shared across all servers)

| Tool | Skill Used | Operation |
|------|-----------|----------|
| `ascp_post_comment` | `communication_skills` | Post AI reasoning as a Chatter note on any Odoo record |
| `ascp_create_activity` | `communication_skills` | Create `mail.activity` on a record to request human approval |
| `ascp_check_activity_done` | `communication_skills` | Poll whether a pending `mail.activity` has been marked done |

**`ascp_create_activity` detail** — used for Human-in-the-Loop:
```
Input:
  model: str            — Odoo model name (e.g. "era.ascp.pegging.ledger")
  record_id: int        — record to attach the activity to
  summary: str          — activity title shown to the planner
  note: str             — full reasoning for the human to read
  deadline: str         — ISO date by which human must respond
  ai_context: str       — why the AI is requesting this approval

Output:
  activity_id: int      — ID of the created mail.activity
  record_url: str       — direct link to open the record in Odoo UI
```

**`ascp_post_comment` detail** — used to log every AI action:
```
Input:
  model: str            — Odoo model name
  record_id: int        — record to post the note on
  action_taken: str     — what the AI did (e.g. "Updated allocation to 75 units")
  ai_context: str       — the full reasoning behind the action
  cycle_id: str | None  — planning cycle reference (optional)

Output:
  message_id: int       — ID of the created mail.message
```

---

### mcp-ascp-procurement (Phase 2B)

| Tool | Skill Used | Operation |
|------|-----------|----------|
| `ascp_get_rfq_list` | `procurement_skills` | `search_read` `purchase.order` — state=`draft`/`sent` |
| `ascp_create_rfq` | `procurement_skills` | `create` PO with lines → auto-posts Chatter |
| `ascp_confirm_po` | `procurement_skills` | `button_confirm` → auto-posts Chatter |
| `ascp_get_vendor_lead_time` | `procurement_skills` | `search_read` `product.supplierinfo` by product |
| `ascp_analyse_rfq_impact` | `impact_analysis_skill` | **NEW** Compare proposed lines vs Odoo baseline — returns ImpactResult list with `classification` and `hitl_required` |
| `ascp_analyse_po_for_approval` | `impact_analysis_skill` | **NEW** Re-analyse existing PO for Director pre-approval check |
| `ascp_post_comment` | `communication_skills` | Post AI reasoning to PO Chatter |
| `ascp_create_activity` | `communication_skills` | Request human approval on PO |
| `ascp_check_activity_done` | `communication_skills` | Poll whether activity is done |

---

### mcp-ascp-inventory (Phase 2C)

| Tool | Skill Used | Operation |
|------|-----------|----------|
| `ascp_get_stock_quant` | `inventory_skills` | `search_read` `stock.quant` by product/location |
| `ascp_get_incoming_moves` | `inventory_skills` | Incoming `stock.move` by date/product |
| `ascp_get_outgoing_demand` | `inventory_skills` | Outgoing `stock.move` vs demand stream |
| `ascp_reserve_stock` | `inventory_skills` | Atomic reserve + peg → auto-posts Chatter |
| `ascp_post_comment` | `communication_skills` | Post AI reasoning to stock record |
| `ascp_create_activity` | `communication_skills` | Request human approval on inventory decision |

**Standard Tool Pattern** — tools are thin wrappers, all logic is in `core/skills/`:

```python
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from core.skills.planning_skills import PlanningSkills
from core.skills.communication_skills import CommunicationSkills

mcp = FastMCP("mcp-ascp-planning")
planning = PlanningSkills()    # wraps OdooXMLRPCClient; write methods auto-post chatter
comms = CommunicationSkills()  # direct chatter / activity access

# ── READ tool (no chatter) ──────────────────────────────────────────
class GetLedgerInput(BaseModel):
    product_id: int | None = Field(None, description="Filter by product.product ID")
    status_filter: list[str] | None = Field(None, description="Filter by status values")
    limit: int = Field(50, description="Max records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")

@mcp.tool()
def ascp_get_ledger(input: GetLedgerInput) -> list[dict]:
    """Query era.ascp.pegging.ledger — read-only, no Chatter post."""
    return planning.get_ledger(input)

# ── WRITE tool (chatter auto-posted inside skill) ────────────────────
class UpdateAllocationInput(BaseModel):
    pegging_id: int = Field(description="Pegging ledger record ID to update")
    allocated_qty: float = Field(description="New allocated quantity")
    status: str = Field(description="New status value")
    ai_context: str = Field(description="Reason why the agent is calling this tool")

@mcp.tool()
def ascp_update_allocation(input: UpdateAllocationInput) -> dict:
    """Update allocation — Chatter post happens automatically inside planning_skills."""
    return planning.update_allocation(input)

# ── COMMUNICATION tools ──────────────────────────────────────────────
class PostCommentInput(BaseModel):
    model: str = Field(description="Odoo model name, e.g. era.ascp.pegging.ledger")
    record_id: int = Field(description="ID of the record to post the note on")
    action_taken: str = Field(description="What the AI did")
    ai_context: str = Field(description="Full reasoning behind the action")
    cycle_id: str | None = Field(None, description="Planning cycle reference")

@mcp.tool()
def ascp_post_comment(input: PostCommentInput) -> dict:
    """Post AI reasoning as a Chatter note on any Odoo record."""
    return comms.post_ai_reasoning(
        input.model, input.record_id, input.ai_context,
        input.action_taken, input.cycle_id,
    )

class CreateActivityInput(BaseModel):
    model: str = Field(description="Odoo model name")
    record_id: int = Field(description="Record to attach the activity to")
    summary: str = Field(description="Activity title shown to the planner")
    note: str = Field(description="Full reasoning for the human to read")
    deadline: str = Field(description="ISO date deadline for human response")
    ai_context: str = Field(description="Why the AI is requesting this approval")

@mcp.tool()
def ascp_create_activity(input: CreateActivityInput) -> dict:
    """Create a mail.activity on a record to request human approval (HITL gate)."""
    return comms.create_activity(
        input.model, input.record_id,
        input.summary, input.note, input.deadline,
    )
```

**Chatter note format** posted on every write:
```
[AI-ASCP] Updated allocated_qty=50.0 → 75.0, status=firm
Reason: SO/2026/0042 confirmed for 75 units. Stock available at WH/Stock (100 on-hand).
Cycle: CYCLE-2026-05-06-001 | Confidence: 0.92
```

---

## Phase 3: Agents & Orchestration (The Brain Layer)

**Goal**: Build the reasoning agents and the Supervisor workflow that coordinates them. This is "Pattern C" — Supervisor routing with Human-in-the-Loop gates.

---

### Agents

#### Planning Manager Agent

- **Model**: `anthropic:claude-sonnet-4-6`
- **MCP Toolset**: `mcp-ascp-planning` (SSE)
- **Output**: `PlanningDecision`
- **Core Logic**:
  1. Call `ascp_get_ledger` + `ascp_sync_demand_stream` to get current state
  2. Call `ascp_check_shortage` to detect stock shortfalls
  3. **If shortage found** → set `action="shortage"`, populate `shortages` list → Supervisor routes to **Purchase Cluster**
  4. **If allocatable** → call `ascp_update_allocation` (chatter auto-posted)
  5. **If major decision needed** → call `ascp_create_activity` for HITL gate

```python
class PlanningDecision(BaseModel):
    action: str          # "allocate" | "shortage" | "hitl_required" | "no_action"
    pegging_updates: list[AllocationUpdate]
    shortages: list[ShortageItem]    # populated when action="shortage"
    hitl_activity_ids: list[int]     # Odoo mail.activity IDs awaiting human response
    summary: str
    confidence: float    # 0.0 – 1.0; < 0.7 forces HITL
```

#### Purchase Cluster (Hierarchy) ★ New

Three agents work in sequence: **Buyer → Purchase Manager → Purchase Director**.
Orchestrated by `orchestrator/purchase_workflow.py` as a LangGraph sub-graph.
Triggered when Planning Manager returns `action="shortage"`.

##### Buyer Agent

- **Model**: `anthropic:claude-sonnet-4-6`
- **MCP Toolset**: `mcp-ascp-procurement` (SSE)
- **Output**: `BuyerDecision`
- **Core Logic**:
  1. Receive shortage list from Supervisor state
  2. Call `ascp_get_vendor_lead_time` to find fastest supplier per product
  3. Call `ascp_create_rfq` for each shortage → Chatter auto-posted
  4. Return `BuyerDecision` with `proposed_lines` (price_unit + lead_days) for the Manager
  5. Does **NOT** confirm POs — confirmation is the Director's job

```python
class BuyerDecision(BaseModel):
    action: str              # "rfq_created" | "no_vendor" | "partial_coverage" | "error"
    proposed_lines: list[ProposedLine]   # input for Manager's impact analysis
    rfq_ids: list[int]
    shortages_covered: list[int]
    shortages_uncovered: list[int]
    summary: str
```

##### Purchase Manager Agent

- **Model**: `anthropic:claude-sonnet-4-6`
- **MCP Toolset**: `mcp-ascp-procurement` (SSE) — uses `ascp_analyse_rfq_impact`
- **Output**: `ManagerAnalysis`
- **Core Logic**:
  1. Receive `BuyerDecision.proposed_lines`
  2. Call `ascp_analyse_rfq_impact` per RFQ → compare vs Odoo baseline
  3. Interpret results: `acceptable` / `warning` / `critical`
  4. Post analysis to each RFQ's Chatter via `ascp_post_comment`
  5. Return `ManagerAnalysis` with recommendation for the Director

```python
class ManagerAnalysis(BaseModel):
    overall_classification: str  # "acceptable" | "warning" | "critical"
    total_cost_delta: float
    overall_price_delta_pct: float
    line_analyses: list[LineAnalysis]
    recommendation: str          # "confirm_all" | "confirm_acceptable_only" | "require_hitl" | "reject_all"
    hitl_required: bool          # True if any line is 'critical'
    summary: str
    purchase_analysis_log: str   # stored in ASCPState.purchase_analysis_logs
```

##### Purchase Director Agent

- **Model**: `anthropic:claude-opus-4-6`
- **MCP Toolset**: `mcp-ascp-procurement` (SSE)
- **Output**: `DirectorDecision`
- **Core Logic**:
  1. Receive `ManagerAnalysis`
  2. **`acceptable` lines** → call `ascp_confirm_po` immediately
  3. **`critical` lines** (price > 10% OR lead > 14 days) → **ALWAYS** call `ascp_create_activity` for Human Director approval in Odoo; do NOT confirm until approved
  4. **`warning` lines** → confirm with policy check or create HITL if needed
  5. Post decision reasoning to Chatter via `ascp_post_comment`

```python
class DirectorDecision(BaseModel):
    action: str              # "confirmed" | "hitl_pending" | "partial_confirm" | "rejected"
    confirmed_po_ids: list[int]
    hitl_activity_ids: list[int]
    pending_po_ids: list[int]
    rejected_po_ids: list[int]
    summary: str
    director_reasoning: str  # stored in purchase_analysis_logs
```

**HITL rule (non-negotiable)**:
> If `ManagerAnalysis.hitl_required` is `True`, the Director MUST call `ascp_create_activity` with `activity_type_xmlid="mail.mail_activity_data_warning"` and must NOT confirm the PO until the human marks the activity Done.

#### Executive Agent

- **Model**: `anthropic:claude-opus-4-6`
- **MCP Toolset**: All three servers
- **Triggered by**: Supervisor when `confidence < 0.7` or unresolvable exceptions
- **Output**: `ExecutiveSummary`

```python
executive_agent = Agent(
    'anthropic:claude-opus-4-6',
    tools=[planning_manager_agent.as_tool(), buyer_agent.as_tool()],
    output_type=ExecutiveSummary,
)
```

---

### Phase 4: LangGraph Orchestration (The State Machine)

**Goal**: Main Supervisor Node routes work between agents. The Purchase Cluster runs as an embedded sub-graph.

#### ASCPState

```python
class ASCPState(TypedDict):
    cycle_id: str
    demand_stream: list[dict]
    pegging_ledger: list[dict]
    supply_stream: list[dict]
    shortages: list[dict]
    planning_decision: dict | None
    # ── Purchase Cluster outputs ──
    buyer_decision: dict | None
    manager_analysis: dict | None
    director_decision: dict | None
    purchase_analysis_logs: list[str]    # append-only; each agent appends its reasoning
    # ── Executive escalation ──
    executive_summary: dict | None
    # ── HITL ──
    hitl_activity_ids: list[int]
    human_approval_required: bool
    messages: list[AnyMessage]
```

#### Supervisor Node — Routing Logic

The Supervisor is a LangGraph node (not an LLM) that reads `ASCPState` and decides the next node:

```python
def supervisor_node(state: ASCPState) -> str:
    decision = state["planning_decision"]
    if decision["action"] == "shortage":
        return "purchase_cluster"     # route to Purchase Sub-graph
    if decision["action"] == "hitl_required":
        return "hitl_checkpoint"
    if decision["confidence"] < 0.7:
        return "executive_node"
    return "update_pegging"
```

#### Purchase Sub-graph (`orchestrator/purchase_workflow.py`)

Contains its own `PurchaseState` and 3 nodes:

```
[START]
   │
   ▼
[buyer_node] ──→ [manager_node] ──→ [director_node]
                                          │
               ┌──────────────────────────┴─────────────────┐
               │ hitl_pending                                │ confirmed
               ▼                                             ▼
  [purchase_hitl_checkpoint]                   [purchase_complete] ──→ [END]
               │  (interrupt → resume)
               └──────────────────────────→ [director_node]  (re-run)
```

After `purchase_complete`, the sub-graph returns and main workflow merges `PurchaseState` (buyer_decision, manager_analysis, director_decision, purchase_analysis_logs) back into `ASCPState`.

#### Workflow Graph (Pattern C — Supervisor + Purchase Sub-graph)

```
[START]
   │
   ▼
[sync_demand] ──→ [sync_supply]
                       │
                       ▼
              [planning_manager_agent]
                       │
                       ▼
                [supervisor_node]  ← routes based on PlanningDecision
                  │       │       │
          shortage│  hitl │  low  │ allocate
                  │  req. │ conf. │
                  ▼       ▼       ▼
         [buyer_agent] [hitl_  [executive_
              │        checkpt]   agent]
              │           │         │
              │    ┌──────┘         │
              └────┴────────────────┘
                           │
                           ▼
                  [update_pegging]  ← write PlanningDecision to Odoo
                           │        ← ascp_update_allocation (auto-chatter)
                           ▼
                      [notify]      ← ascp_post_comment summary to key records
                           │
                           ▼
                         [END]
```

#### HITL Checkpoint — How it works

```
1. Agent calls ascp_create_activity(model, record_id, summary, note, deadline)
   └─→ Odoo creates mail.activity → planner sees task in their Odoo inbox

2. LangGraph workflow PAUSES at [hitl_checkpoint] node
   └─→ State is persisted to checkpointer (SQLite / PostgreSQL)

3. Human opens Odoo, reads AI reasoning in Chatter + Activity note
   └─→ Clicks "Mark Done" or "Refuse"

4. External trigger (webhook / cron) calls ascp_check_activity_done
   └─→ Returns approved=True / False

5. LangGraph RESUMES:
   ├── approved=True  → continue to [update_pegging]
   └── approved=False → return to [supervisor_node] with human feedback
```

**Features**:
- Durable execution via LangGraph checkpointing (SQLite dev / PostgreSQL prod)
- Multiple HITL gates per cycle (one per shortage item or exception)
- Planning cycle trigger: cron / webhook / manual run
- Full message history + agent decisions preserved per cycle in state store

---

## Prompt Roadmap (3-Prompt Build Order)

This is the confirmed build sequence. Each Prompt corresponds to a logical bundle of work:

### Prompt 1 — "The House & The Engine"
Build the foundation: project scaffold, shared client, all skill modules.

| # | Task | Notes |
|---|------|-------|
| 1 | Project scaffold + root `pyproject.toml` | All folders, empty `__init__.py` files |
| 2 | `core/config.py` + `core/odoo_client.py` | pydantic-settings + XML-RPC client |
| 3 | `core/skills/base_skill.py` | Abstract base with `self.client` + `post_ai_reasoning()` delegation |
| 4 | `core/skills/communication_skills.py` | `post_ai_reasoning()` + `create_activity()` + `check_activity_done()` |
| 5 | `core/skills/planning_skills.py` | Pegging ledger + demand/supply stream ops (chatter on writes) |
| 6 | `core/skills/procurement_skills.py` | PO, RFQ, vendor ops (chatter on writes) |
| 7 | `core/skills/inventory_skills.py` | Stock quant, moves, reservation (chatter on writes) |
| 8 | `core/skills/sales_skills.py` | sale.order read-only ops (demand sync source) |
| 9 | `era_ascp_core` Odoo addon (`era.ascp.*` models with `mail.thread`) | Phase 1 |

### Prompt 2 — "The Workstations" (Southbound MCP Servers)
Expose skill functions as typed MCP tools. Thin wrappers only.

| # | Task | Notes |
|---|------|-------|
| 10 | `mcp-ascp-planning` server + tools | `ascp_get_ledger`, `ascp_update_allocation`, `ascp_check_shortage`, `ascp_sync_demand_stream`, `ascp_post_comment`, `ascp_create_activity`, `ascp_check_activity_done` |
| 11 | `mcp-ascp-procurement` server + tools | `ascp_get_rfq_list`, `ascp_create_rfq`, `ascp_confirm_po`, `ascp_get_vendor_lead_time`, **`ascp_analyse_rfq_impact`**, **`ascp_analyse_po_for_approval`**, `ascp_post_comment`, `ascp_create_activity`, `ascp_check_activity_done` |
| 12 | `mcp-ascp-inventory` server + tools | `ascp_get_stock_quant`, `ascp_get_incoming_moves`, `ascp_reserve_stock`, `ascp_post_comment` |

### Prompt 3 — "The Brain & The Conversation"
Build agents, Purchase Cluster hierarchy, Supervisor routing, and the HITL workflow.

| # | Task | Notes |
|---|------|-------|
| 13 | Planning Manager Agent | PydanticAI, `mcp-ascp-planning` toolset, `PlanningDecision` output |
| 14 | Buyer Agent (`agents/purchase/buyer_agent.py`) | PydanticAI, `mcp-ascp-procurement`, `BuyerDecision` output |
| 15 | Purchase Manager Agent (`agents/purchase/manager_agent.py`) | PydanticAI, `ascp_analyse_rfq_impact`, `ManagerAnalysis` output |
| 16 | Purchase Director Agent (`agents/purchase/director_agent.py`) | PydanticAI, `ascp_confirm_po` + HITL gate, `DirectorDecision` output |
| 17 | Executive Agent | PydanticAI, all 3 servers + sub-agent tools |
| 18 | `ASCPState` TypedDict with `purchase_analysis_logs` | All state fields |
| 19 | Purchase Sub-graph (`orchestrator/purchase_workflow.py`) | Buyer→Manager→Director + HITL checkpoint |
| 20 | Main LangGraph workflow (`orchestrator/workflow.py`) | Supervisor routes shortage → `purchase_cluster` |
| 21 | Integration tests + CI | End-to-end: shortage → HITL → resume → chatter trail |

---

## Development Sequence (Full)

| # | Task | Prompt | Depends On |
|---|------|--------|------------|
| 1 | Project scaffold + `pyproject.toml` | P1 | — |
| 2 | `core/config.py` + `core/odoo_client.py` | P1 | 1 |
| 3 | `core/skills/base_skill.py` | P1 | 2 |
| 4 | `core/skills/communication_skills.py` | P1 | 3 |
| 5 | `core/skills/planning_skills.py` | P1 | 4 |
| 6 | `core/skills/procurement_skills.py` | P1 | 4 |
| 7 | `core/skills/inventory_skills.py` | P1 | 4 |
| 8 | `core/skills/sales_skills.py` | P1 | 4 |
| 9 | `era_ascp_core` Odoo addon | P1 | — |
| 10 | `mcp-ascp-planning` server + tools | P2 | 5, 9 |
| 11 | `mcp-ascp-procurement` server + tools (+ impact tools) | P2 | 6, 9 |
| 12 | `mcp-ascp-inventory` server + tools | P2 | 7, 9 |
| 13 | Planning Manager Agent | P3 | 10 |
| 14 | Buyer Agent (`agents/purchase/`) | P3 | 11 |
| 15 | Purchase Manager Agent (`agents/purchase/`) | P3 | 11, 14 |
| 16 | Purchase Director Agent (`agents/purchase/`) | P3 | 15 |
| 17 | Executive Agent | P3 | 13 |
| 18 | `ASCPState` + `purchase_analysis_logs` | P3 | 13–16 |
| 19 | Purchase Sub-graph (`orchestrator/purchase_workflow.py`) | P3 | 14–16 |
| 20 | Main LangGraph workflow (`orchestrator/workflow.py`) | P3 | 13, 19 |
| 21 | Integration tests + CI | QA | All |

---

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Odoo | Odoo Community 19.4 alpha | System of record |
| Python | CPython 3.12+ | All layers |
| MCP Servers | FastMCP (latest) | SSE transport |
| Agent Framework | PydanticAI 0.x | Reasoning layer |
| Orchestration | LangGraph (latest) | State + workflow |
| LLM (planning) | Anthropic Claude Sonnet 4.6 | Planning Manager + Buyer + Purchase Manager |
| LLM (executive) | Anthropic Claude Opus 4.6 | Executive Agent + Purchase Director |
| Config | pydantic-settings v2 | Env var loading |
| HTTP Client | httpx | Async requests |
| Odoo Connector | xmlrpc.client (stdlib) | No psycopg2 / no SQL |

---

## Environment Variables (`.env`)

```bash
# Odoo HTTP Server
ODOO_URL=http://202.71.1.13:8069
ODOO_DB=odoo_db
ODOO_USER=admin@eraowl.com
ODOO_API_KEY=<from Odoo user preferences>

# AI Models
ANTHROPIC_API_KEY=<your key>
OPENAI_API_KEY=<your key>             # optional fallback

# MCP Server Ports (local dev)
MCP_PLANNING_PORT=8001
MCP_PROCUREMENT_PORT=8002
MCP_INVENTORY_PORT=8003
```

---

## Verification Checklist

### Setup (Skills Layer)
- [ ] `communication_skills.post_ai_reasoning()` posts a note to the Odoo record's Chatter
- [ ] Chatter message is visible in Odoo UI with correct `[AI-ASCP]` prefix
- [ ] `communication_skills.create_activity()` creates a `mail.activity` on the record
- [ ] All skill write methods auto-post chatter without extra calls from MCP tools

### Phase 1 (Odoo Models)
- [ ] `era.ascp.pegging.ledger` installed and visible in Odoo UI
- [ ] `era.ascp.demand.stream` accessible via XML-RPC from Python
- [ ] All `era.ascp.*` models have `mail.thread` — chatter tab visible in UI
- [ ] `tracking=True` fields show change history in chatter automatically
- [ ] Access rights verified for API user

### Phase 2 (MCP Servers)
- [ ] `fastmcp dev mcp_servers/mcp-ascp-planning/server.py` — tools visible in MCP Inspector
- [ ] `ascp_get_pegging_ledger` returns records from live Odoo
- [ ] `ascp_update_allocation` writes back AND posts `[AI-ASCP]` note to chatter
- [ ] `ascp_sync_demand_stream` syncs at least one SO into demand stream
- [ ] `ascp_create_exception` sets status=exception AND creates a `mail.activity` for human review

### Phase 3 (Agents)
- [ ] Planning Manager resolves a test planning scenario end-to-end
- [ ] `PlanningDecision` structured output validates with Pydantic
- [ ] Every tool call by the agent results in a chatter entry on the affected Odoo record
- [ ] Multi-agent delegation to Executive Agent works

### Phase 4 (Orchestration)
- [ ] Full workflow graph executes without errors on test data
- [ ] Human-in-the-loop checkpoint pauses at exception escalation
- [ ] State is persisted across workflow interruptions
- [ ] End-to-end: one planning cycle → multiple Chatter entries on pegging records → human can read full AI reasoning trail

---

## Key Design Decision: AI Reasoning Trail

Every time the AI agent modifies an Odoo record, a **Chatter note** is posted automatically via `communication_skills.post_ai_reasoning()`. This creates a full audit trail that humans can read directly in the Odoo UI — no separate logging system needed.

**Why Chatter (not a separate log table)?**
- Chatter is already attached to every `mail.thread` record — zero extra infrastructure
- Planners and buyers already work in Odoo — they see AI decisions in the same place they work
- Chatter notes are timestamped, linked to the record, and visible in the activity timeline
- `mail.activity` allows the AI to assign a human follow-up task directly from within a planning decision

**Chatter note anatomy**:
```
┌─────────────────────────────────────────────────┐
│ 🤖 AI-ASCP  •  2026-05-06 14:32                │
│─────────────────────────────────────────────────│
│ Updated: allocated_qty=50.0 → 75.0, status=firm │
│                                                  │
│ Reason: SO/2026/0042 confirmed for 75 units.    │
│ Stock available at WH/Stock (100 units on-hand). │
│ Increased allocation to cover full demand.       │
│                                                  │
│ Cycle: CYCLE-2026-05-06-001                     │
│ Confidence: 0.92                                │
└─────────────────────────────────────────────────┘
```

---

*Last updated: 2026-05-06*
