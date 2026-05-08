# Axon MCP Tool Catalog

> Each of the 10 domain agents consumes MCP tools from one or more MCP servers.
> Tools are discovered at runtime via MCP's `list_tools`, but this catalog
> serves as the authoritative design-time reference for which agents need which
> tools, and what each tool's contract looks like.
>
> **All data access is through MCP only — no direct database connections.**
> READ tools query ERP state; WRITE tools trigger ERP-side operations (create
> orders, update schedules, log decisions) through the MCP server. Axon never
> executes SQL or ORM calls against ERP databases.

## Tool naming convention

Tools exposed by MCP servers follow the pattern: `{verb}_{noun_phrase}`.
Tool names are global across all MCP servers; the agent's tool registry maps
them to the correct server at call time via `SemanticTransformer.can_handle()`.

## Servers

| Server ID | Description | Axon connector (client only) |
|-----------|-------------|------------------------------|
| `oracle_ebs` | mcp-oracle-ebs — separate project (inventory, WIP, orders, suppliers) | `src/axon/connectors/mcp_oracle_ebs/` |
| `mcp_agent_buyer` | BuyerAgent — procurement sub-agent of oracle_ebs (suppliers, POs, costs, requisitions) | `src/axon/connectors/mcp_oracle_ebs/mcp_agent_buyer.py` |
| `mcp_agent_store` | StoreAgent — inventory/warehouse sub-agent of oracle_ebs (stock levels, ATP, orders, shipments) | `src/axon/connectors/mcp_oracle_ebs/mcp_agent_store.py` |
| `sap` | mcp-sap — separate project (production orders, MRP, finance) | `src/axon/connectors/mcp_sap/` |
| `odoo` | mcp-odoo — separate project (alternative ERP) | `src/axon/connectors/mcp_odoo/` |
| `external_rag` | mcp-policy-server (port 8021) — separate project (SOPs, policies, compliance) | `src/axon/connectors/mcp_external_rag/` |

## Direction semantics

| Direction | Meaning | HITL gating |
|-----------|---------|-------------|
| `READ` | Query-only. No side effects on the ERP. Safe to call without approval. | Never required |
| `WRITE` | Triggers ERP-side mutation (create PO, update schedule, log decision). MCP server executes the operation; Axon never touches ERP tables directly. | Required for high-impact writes (PO > $threshold, schedule changes affecting delivery dates) |

---

## Agent × Tool Matrix

```
                     oracle_ebs          mcp_agent_buyer   mcp_agent_store    external_rag
Agent      ┌──────────────────────┐    ┌────────────────┐┌───────────────┐ ┌──────────────────┐
           │ wip  bom  insp  mfg  │    │ supp cost po   ││ inv atp ship  │ │ sop  compliance   │
───────────┼──────────────────────┼────┼────────────────┼┼───────────────┼─┼──────────────────┤
Sales      │  ·    ·    ·    ·   │    │  ·    ·   ·    ││  ●    ●   ●   │ │  ·       ·        │
Production │  ●    ●    ·    ·   │    │  ·    ·   ·    ││  ●    ·   ·   │ │  ·       ·        │
Procurement│  ·    ·    ·    ·   │    │  ●    ●   ●    ││  ·    ·   ·   │ │  ·       ·        │
Warehouse  │  ·    ·    ·    ·   │    │  ·    ·   ·    ││  ●    ·   ·   │ │  ·       ·        │
Logistics  │  ·    ·    ·    ·   │    │  ·    ·   ·    ││  ·    ·   ●   │ │  ·       ·        │
Finance    │  ·    ·    ·    ·   │    │  ·    ●   ·    ││  ·    ·   ·   │ │  ·       ·        │
QA         │  ·    ·    ·    ·   │    │  ·    ·   ·    ││  ·    ·   ·   │ │  ●       ●        │
QC         │  ·    ·    ●    ·   │    │  ·    ·   ·    ││  ·    ·   ·   │ │  ●       ●        │
PD         │  ·    ●    ·    ·   │    │  ·    ·   ·    ││  ·    ·   ·   │ │  ●       ·        │
Maintenance│  ·    ·    ·    ●   │    │  ·    ·   ·    ││  ·    ·   ·   │ │  ●       ·        │
───────────┴──────────────────────┴────┴────────────────┴┴───────────────┴─┴──────────────────┘
● = tool assigned   · = not assigned
```

---

## Tool Definitions

### 1. Sales Agent

**Domain**: Demand forecasting, ATP (Available to Promise), customer allocation.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_available_to_promise` | `mcp_agent_store` | READ | Return ATP quantity and earliest availability date for an item across a date range. |
| `get_inventory_levels` | `mcp_agent_store` | READ | Return on-hand, reserved, and available inventory for items at a location. |
| `get_sales_orders` | `mcp_agent_store` | READ | List open sales orders with item, quantity, customer, requested date, and priority. |
| `get_demand_forecast` | `mcp_agent_store` | READ | Return statistical or manual forecast for items by period with confidence level. |

### 2. Production Agent

**Domain**: MPS (Master Production Schedule), finite capacity scheduling.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `list_wip_jobs` | `oracle_ebs` | READ | List all WIP jobs with status, start/end dates, quantity, and routing. |
| `get_inventory_levels` | `mcp_agent_store` | READ | Return on-hand inventory for components and raw materials. |
| `get_bom` | `oracle_ebs` | READ | Return the bill of materials (components + quantities) for an item. |
| `get_work_center_capacity` | `oracle_ebs` | READ | Return available capacity (hours) per work center per period. |
| `get_routing` | `oracle_ebs` | READ | Return the manufacturing routing (operations sequence) for an item. |
| `reschedule_wip_job` | `oracle_ebs` | WRITE | Update start/end dates of a WIP job. Requires HITL if shift ≥ 7 days. |

### 3. Procurement Agent

**Domain**: Automated sourcing, supplier sync, purchase order management.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_suppliers` | `mcp_agent_buyer` | READ | Return approved supplier list for an item with lead times, pricing, and MOQ. |
| `get_item_costs` | `mcp_agent_buyer` | READ | Return standard and last actual cost for items. |
| `get_purchase_orders` | `mcp_agent_buyer` | READ | List open POs with item, quantity, supplier, due date, and status. |
| `get_supplier_performance` | `mcp_agent_buyer` | READ | Return on-time delivery %, quality score, and lead time variance per supplier. |
| `create_purchase_requisition` | `mcp_agent_buyer` | WRITE | Create a purchase requisition. Requires HITL if amount > threshold. |

### 4. Warehouse Agent

**Domain**: Safety stock, inventory optimization, space planning.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_inventory_levels` | `mcp_agent_store` | READ | Return on-hand, reserved, and available inventory per item × location. |
| `get_safety_stock` | `mcp_agent_store` | READ | Return safety stock targets per item × location. |
| `get_storage_capacity` | `mcp_agent_store` | READ | Return total and available storage capacity (pallet/volume) per warehouse. |
| `get_inventory_aging` | `mcp_agent_store` | READ | Return inventory aging breakdown (FIFO layers) for items. |

### 5. Logistics Agent

**Domain**: Route planning, distribution, shipment scheduling.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_shipments` | `mcp_agent_store` | READ | List planned and in-transit shipments with origin, destination, items, and ETA. |
| `get_carrier_rates` | `mcp_agent_store` | READ | Return carrier rate cards by lane, weight, and service level. |
| `get_transit_times` | `mcp_agent_store` | READ | Return standard transit time (days) per lane and service level. |
| `get_delivery_constraints` | `mcp_agent_store` | READ | Return customer delivery windows, dock constraints, and appointment requirements. |
| `create_shipment` | `mcp_agent_store` | WRITE | Create a shipment record. Requires HITL for expedited shipments. |

### 6. Finance Agent

**Domain**: ROI analysis, costing, budget alignment.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_item_costs` | `mcp_agent_buyer` | READ | Return standard, actual, and target costs per item. |
| `get_budget` | `oracle_ebs` | READ | Return budget allocation per department/cost center per period. |
| `get_gl_accounts` | `oracle_ebs` | READ | Return chart of accounts relevant to supply chain (COGS, inventory, variance). |
| `get_profitability` | `oracle_ebs` | READ | Return margin analysis per item/customer/channel. |

### 7. QA Agent (Quality Assurance)

**Domain**: Regulatory compliance, SOP enforcement, audit readiness.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_sop` | `external_rag` | READ | Retrieve the relevant Standard Operating Procedure for a given process code. |
| `check_compliance` | `external_rag` | READ | Verify a proposed plan or change against regulatory constraints and SOPs. |
| `get_audit_history` | `external_rag` | READ | Return recent audit findings relevant to a process or item. |
| `get_regulatory_requirements` | `external_rag` | READ | Return applicable regulations (FDA, ISO, GMP) for a product category. |

### 8. QC Agent (Quality Control)

**Domain**: Inspection planning, rework logic, defect tracking.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_inspection_plan` | `oracle_ebs` | READ | Return inspection plan (sampling, criteria) for an item/lot. |
| `get_defect_history` | `oracle_ebs` | READ | Return defect rate and Pareto by item, operation, and period. |
| `get_sop` | `external_rag` | READ | Retrieve QC procedures and acceptance criteria. |
| `check_compliance` | `external_rag` | READ | Verify inspection plan against regulatory quality standards. |
| `list_wip_jobs` | `oracle_ebs` | READ | List WIP jobs needing inspection hold or rework. |
| `create_inspection_lot` | `oracle_ebs` | WRITE | Create an inspection lot for a received batch. No HITL required. |

### 9. PD Agent (Product Development)

**Domain**: BOM engineering, new product introduction, engineering changes.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_bom` | `oracle_ebs` | READ | Return current and pending BOM revisions for an item. |
| `get_engineering_changes` | `oracle_ebs` | READ | List ECOs (Engineering Change Orders) with status and effective dates. |
| `get_item_master` | `oracle_ebs` | READ | Return item attributes: make/buy, lead time, lifecycle phase, revision. |
| `get_sop` | `external_rag` | READ | Retrieve NPI (New Product Introduction) and ECO procedures. |

### 10. Maintenance Agent

**Domain**: Predictive downtime, asset health, maintenance scheduling.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_asset_health` | `oracle_ebs` | READ | Return current health score, MTBF, and next scheduled maintenance per asset. |
| `list_wip_jobs` | `oracle_ebs` | READ | List WIP jobs to identify production dependencies on assets. |
| `get_maintenance_schedule` | `oracle_ebs` | READ | Return preventive and predictive maintenance schedule per asset. |
| `get_sop` | `external_rag` | READ | Retrieve maintenance procedures and safety protocols. |
| `get_downtime_history` | `oracle_ebs` | READ | Return downtime events with duration, cause, and affected capacity. |
| `update_work_center_status` | `oracle_ebs` | WRITE | Update work center status (available, maintenance, down). No HITL required. |

---

## Shared Tools (cross-cutting)

Tools available to multiple agents use the same name and contract across all
consumers. The tool registry enforces that each agent only sees its assigned subset.

| Tool | Server | Dir | Available to |
|------|--------|-----|-------------|
| `get_inventory_levels` | `mcp_agent_store` | READ | Sales, Production, Warehouse |
| `get_item_costs` | `mcp_agent_buyer` | READ | Finance, Procurement |
| `list_wip_jobs` | `oracle_ebs` | READ | Production, QC, Maintenance |
| `get_bom` | `oracle_ebs` | READ | Production, PD |
| `get_sop` | `external_rag` | READ | QA, QC, PD, Maintenance |
| `check_compliance` | `external_rag` | READ | QA, QC |

---

## Write tool gating rules

All WRITE tools go through MCP — Axon sends the tool call, the ERP's MCP server
executes it. No direct SQL/ORM access. HITL gating applies in these cases:

| Condition | Gate |
|-----------|------|
| Purchase requisition amount > `$threshold` | Human approval required before MCP call |
| Schedule change shifting delivery > 7 days | Human approval required |
| All other WRITE tools | Agent may execute without HITL; logged to Experience Ledger for audit |

---

## Phase 2–3 Integration Notes

- **ERP abstraction**: tools defined against `oracle_ebs` above should have
  equivalent implementations in the `sap` and `odoo` MCP servers. The
  `SemanticTransformer` handles mapping; agents never see which ERP a tool
  comes from.
- **Tool discovery**: on startup, each connector calls `list_tools()` on its
  MCP server and registers results in `TOOL_CATALOG`. Missing tools are
  logged at WARN but do not block startup (graceful degradation).
- **Tool versioning**: MCP servers should include a `version` field in tool
  definitions. If a tool's signature changes, the transformer logs a
  `TRANSFORM_FAILED` error and the connector marks that tool as stale.
- **Write tool audit**: every WRITE tool call is recorded in the Experience
  Ledger with correlation_id, agent_id, tool name, parameters, and MCP
  server response. This provides a full audit trail without needing direct
  ERP database access.
