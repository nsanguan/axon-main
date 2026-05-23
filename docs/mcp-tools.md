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

| Server ID | Port | Description | Axon connector |
|-----------|------|-------------|----------------|
| `ebs_demand` | 8102 | EBS MCP Agent — sales orders, forecasts, ATP | `EBSDemandConnector` |
| `ebs_supply` | 8103 | EBS MCP Agent — inventory, suppliers, costs, POs, PRs | `EBSSupplyConnector` |
| `ebs_production` | 8104 | EBS MCP Agent — WIP, BOM, capacity, routing | `EBSProductionConnector` |
| `ebs_logistics` | 8105 | EBS MCP Agent — shipments, carriers, transit | `EBSLogisticsConnector` |
| `ebs_quality` | 8106 | EBS MCP Agent — inspection plans, defect history | `EBSQualityConnector` |
| `ebs_asset` | 8107 | EBS MCP Agent — asset health, maintenance, downtime | `EBSAssetConnector` |
| `ebs_finance` | 8108 | EBS MCP Agent — budget, GL, profitability | `EBSFinanceConnector` |
| `ebs_engineering` | 8109 | EBS MCP Agent — ECOs, BOM | `EBSEngineeringConnector` |
| `ebs_warehouse` | 8111 | EBS MCP Agent — full warehouse management (14 tools) | `EBSWarehouseConnector` |
| `ebs_auth` | 8101 | EBS MCP Agent — auth server | `EBSAuthConnector` |
| `ebs_demand` | 8102 | EBS MCP Agent — demand server | `EBSDemandConnector` |
| `ebs_supply` | 8103 | EBS MCP Agent — supply server | `EBSSupplyConnector` |
| `sap` | — | SAP MCP connector | `SAPConnector` |
| `odoo` | — | Odoo MCP connector | `OdooConnector` |
| `llmwiki` | 8000 | EraOwl-LLMWiki Company Policy MCP Server (policies, SOPs, compliance) | `PolicyServerClient` |

## Direction semantics

| Direction | Meaning | HITL gating |
|-----------|---------|-------------|
| `READ` | Query-only. No side effects on the ERP. Safe to call without approval. | Never required |
| `WRITE` | Triggers ERP-side mutation (create PO, update schedule, log decision). MCP server executes the operation; Axon never touches ERP tables directly. | Required for high-impact writes (PO > $threshold, schedule changes affecting delivery dates) |

---

## Agent × Tool Matrix

```
                     EBS domain servers                                 LLMWiki
                     ebs_demand   ebs_supply  ebs_prod  ebs_log   ebs_qual  ebs_asset  ebs_fin  ebs_eng  ebs_wh      llmwiki
Agent      ┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
           │   ord atp fct   inv sup cst  wip bom   shp car trn  insp def   hlth sch   bgt gl prf   eco bom   wh   │ sop cmp aud reg │
───────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────────┤
Sales      │   ●   ●   ●     ·   ·   ·    ·   ·    ·   ·   ·    ·   ·     ·   ·     ·   ·   ·    ·   ·    ·    │  ·   ·   ·   ·  │
Production │   ·   ·   ·     ●   ·   ·    ●   ●    ·   ·   ·    ·   ·     ·   ·     ·   ·   ·    ·   ·    ·    │  ·   ·   ·   ·  │
Procurement│   ·   ·   ·     ·   ●   ●    ·   ·    ·   ·   ·    ·   ·     ·   ·     ·   ·   ·    ·   ·    ·    │  ·   ·   ·   ·  │
Warehouse  │   ·   ·   ·     ●   ●   ●    ·   ·    ·   ·   ·    ·   ·     ·   ·     ·   ·   ·    ·   ·    ·    │  ·   ·   ·   ·  │
Logistics  │   ·   ·   ·     ·   ·   ·    ·   ·    ●   ●   ●    ·   ·     ·   ·     ·   ·   ·    ·   ·    ·    │  ·   ·   ·   ·  │
Finance    │   ·   ·   ·     ·   ●   ·    ·   ·    ·   ·   ·    ·   ·     ·   ·     ●   ●   ●    ·   ·    ·    │  ·   ·   ·   ·  │
QA         │   ·   ·   ·     ·   ·   ·    ·   ·    ·   ·   ·    ·   ·     ·   ·     ·   ·   ·    ·   ·    ·    │  ●   ●   ●   ●  │
QC         │   ·   ·   ·     ·   ·   ·    ●   ·    ·   ·   ·    ●   ●     ·   ·     ·   ·   ·    ·   ·    ·    │  ●   ●   ·   ·  │
PD         │   ·   ·   ·     ·   ·   ·    ●   ●    ·   ·   ·    ·   ·     ·   ·     ·   ·   ·    ●   ●    ·    │  ●   ·   ·   ·  │
Maintenance│   ·   ·   ·     ·   ·   ·    ●   ·    ·   ·   ·    ·   ·     ●   ●     ·   ·   ·    ·   ·    ·    │  ●   ·   ·   ·  │
───────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────┴──────────────────┘
● = tool assigned   · = not assigned
```

---

## Tool Definitions

### 1. Sales Agent

**Domain**: Demand forecasting, ATP (Available to Promise), customer allocation.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_available_to_promise` | `ebs_demand` | READ | Return ATP quantity and earliest availability date for an item across a date range. |
| `get_inventory_levels` | `ebs_supply` | READ | Return on-hand, reserved, and available inventory for items at a location. |
| `get_sales_orders` | `ebs_demand` | READ | List open sales orders with item, quantity, customer, requested date, and priority. |
| `get_demand_forecast` | `ebs_demand` | READ | Return statistical or manual forecast for items by period with confidence level. |
| `get_shipments` | `ebs_logistics` | READ | List planned and in-transit shipments with origin, destination, items, and ETA. |

### 2. Production Agent

**Domain**: MPS (Master Production Schedule), finite capacity scheduling.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `list_wip_jobs` | `ebs_production` | READ | List all WIP jobs with status, start/end dates, quantity, and routing. |
| `get_inventory_levels` | `ebs_supply` | READ | Return on-hand inventory for components and raw materials. |
| `get_bom` | `ebs_production` | READ | Return the bill of materials (components + quantities) for an item. |
| `get_work_center_capacity` | `ebs_production` | READ | Return available capacity (hours) per work center per period. |
| `get_routing` | `ebs_production` | READ | Return the manufacturing routing (operations sequence) for an item. |
| `reschedule_wip_job` | `ebs_production` | WRITE | Update start/end dates of a WIP job. Requires HITL if shift ≥ 7 days. |

### 3. Procurement Agent

**Domain**: Automated sourcing, supplier sync, purchase order management.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_suppliers` | `ebs_supply` | READ | Return approved supplier list for an item with lead times, pricing, and MOQ. |
| `get_item_costs` | `ebs_supply` | READ | Return standard and last actual cost for items. |
| `get_purchase_orders` | `ebs_supply` | READ | List open POs with item, quantity, supplier, due date, and status. |
| `get_supplier_performance` | `ebs_supply` | READ | Return on-time delivery %, quality score, and lead time variance per supplier. |
| `create_purchase_requisition` | `ebs_supply` | WRITE | Create a purchase requisition. Requires HITL if amount > threshold. |

### 4. Warehouse Agent

**Domain**: Safety stock, inventory optimization, space planning.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_inventory_levels` | `ebs_supply` | READ | Return on-hand, reserved, and available inventory per item × location. |
| `get_safety_stock` | `ebs_supply` | READ | Return safety stock targets per item × location. |
| `get_storage_capacity` | `ebs_supply` | READ | Return total and available storage capacity (pallet/volume) per warehouse. |
| `get_inventory_aging` | `ebs_supply` | READ | Return inventory aging breakdown (FIFO layers) for items. |

### 5. Logistics Agent

**Domain**: Route planning, distribution, shipment scheduling.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_shipments` | `ebs_logistics` | READ | List planned and in-transit shipments with origin, destination, items, and ETA. |
| `get_carrier_rates` | `ebs_logistics` | READ | Return carrier rate cards by lane, weight, and service level. |
| `get_transit_times` | `ebs_logistics` | READ | Return standard transit time (days) per lane and service level. |
| `get_delivery_constraints` | `ebs_logistics` | READ | Return customer delivery windows, dock constraints, and appointment requirements. |
| `create_shipment` | `ebs_logistics` | WRITE | Create a shipment record. Requires HITL for expedited shipments. |

### 6. Finance Agent

**Domain**: ROI analysis, costing, budget alignment.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_item_costs` | `ebs_supply` | READ | Return standard, actual, and target costs per item. |
| `get_budget` | `ebs_finance` | READ | Return budget allocation per department/cost center per period. |
| `get_gl_accounts` | `ebs_finance` | READ | Return chart of accounts relevant to supply chain (COGS, inventory, variance). |
| `get_profitability` | `ebs_finance` | READ | Return margin analysis per item/customer/channel. |

### 7. QA Agent (Quality Assurance)

**Domain**: Regulatory compliance, SOP enforcement, audit readiness.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_sop` | `llmwiki` | READ | Retrieve the relevant Standard Operating Procedure from the LLMWiki Policy Server. |
| `check_compliance` | `llmwiki` | READ | Verify a proposed plan or change against regulatory constraints and policies. |
| `get_audit_history` | `llmwiki` | READ | Return recent audit findings relevant to a process or item. |
| `get_regulatory_requirements` | `llmwiki` | READ | Return applicable regulations (FDA, ISO, GMP) for a product category. |

### 8. QC Agent (Quality Control)

**Domain**: Inspection planning, rework logic, defect tracking.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_inspection_plan` | `ebs_quality` | READ | Return inspection plan (sampling, criteria) for an item/lot. |
| `get_defect_history` | `ebs_quality` | READ | Return defect rate and Pareto by item, operation, and period. |
| `get_sop` | `llmwiki` | READ | Retrieve QC procedures and acceptance criteria. |
| `check_compliance` | `llmwiki` | READ | Verify inspection plan against regulatory quality standards. |
| `list_wip_jobs` | `ebs_production` | READ | List WIP jobs needing inspection hold or rework. |
| `create_inspection_lot` | `ebs_quality` | WRITE | Create an inspection lot for a received batch. No HITL required. |

### 9. PD Agent (Product Development)

**Domain**: BOM engineering, new product introduction, engineering changes.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_bom` | `ebs_engineering` | READ | Return current and pending BOM revisions for an item. |
| `get_engineering_changes` | `ebs_engineering` | READ | List ECOs (Engineering Change Orders) with status and effective dates. |
| `get_item_master` | `ebs_production` | READ | Return item attributes: make/buy, lead time, lifecycle phase, revision. |
| `get_sop` | `llmwiki` | READ | Retrieve NPI (New Product Introduction) and ECO procedures. |

### 10. Maintenance Agent

**Domain**: Predictive downtime, asset health, maintenance scheduling.

| Tool | Server | Dir | Description |
|------|--------|-----|-------------|
| `get_asset_health` | `ebs_asset` | READ | Return current health score, MTBF, and next scheduled maintenance per asset. |
| `list_wip_jobs` | `ebs_production` | READ | List WIP jobs to identify production dependencies on assets. |
| `get_maintenance_schedule` | `ebs_asset` | READ | Return preventive and predictive maintenance schedule per asset. |
| `get_sop` | `llmwiki` | READ | Retrieve maintenance procedures and safety protocols. |
| `get_downtime_history` | `ebs_asset` | READ | Return downtime events with duration, cause, and affected capacity. |
| `update_work_center_status` | `ebs_asset` | WRITE | Update work center status (available, maintenance, down). No HITL required. |

---

## Shared Tools (cross-cutting)

Tools available to multiple agents use the same name and contract across all
consumers. The tool registry enforces that each agent only sees its assigned subset.

| Tool | Server | Dir | Available to |
|------|--------|-----|-------------|
| `get_inventory_levels` | `ebs_supply` | READ | Sales, Production, Warehouse |
| `get_item_costs` | `ebs_supply` | READ | Finance, Procurement |
| `list_wip_jobs` | `ebs_production` | READ | Production, QC, Maintenance |
| `get_bom` | `ebs_production` | READ | Production (primary); `ebs_engineering` | READ | PD (primary) |
| `get_shipments` | `ebs_logistics` | READ | Logistics, Sales, Warehouse |
| `get_sop` | `llmwiki` | READ | QA, QC, PD, Maintenance |
| `check_compliance` | `llmwiki` | READ | QA, QC |

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

## LLMWiki Integration

The Policy Server is backed by the EraOwl-LLMWiki Company Policy MCP Server
(port 8000). It exposes 24 MCP tools for policy retrieval, compliance checking,
procurement validation, and strategic review against the company's policy vault.
Key tools mapped to Axon's agent API:

| Axon tool | LLMWiki MCP tool | Description |
|-----------|-----------------|-------------|
| `get_sop` | `read_policy` / `search_policy_keywords` | Retrieve policy article with YAML frontmatter metadata |
| `check_compliance` | `policy_consultant` / `compliance_harness` | Check against approval matrix and procurement rules |
| `get_audit_history` | `ask_policy` | Natural-language Q&A over policy vault |
| `get_regulatory_requirements` | `search_policy_keywords` + `get_approval_matrix` | Keyword search + spending limits |

---

## EBS MCP Agent Architecture

The EBS MCP Agent project (`/u01/eraowl-ai-system/EraOwl-EBS-Agent/ebs-mcp-agent`)
deploys 10 domain-specific MCP servers, each exposing a focused set of tools.
Axon's connector layer mirrors this architecture 1:1:

```
EBS MCP Agent Servers (Oracle EBS database via SQLcl subprocess)
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ ebs-auth │ │ebs-demand│ │ebs-supply│ │ebs-prod  │ │ebs-log   │
│  :8101   │ │  :8102   │ │  :8103   │ │  :8104   │ │  :8105   │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ebs-quality│ │ebs-asset │ │ebs-fin   │ │ebs-eng   │ │ebs-wh    │
│  :8106   │ │  :8107   │ │  :8108   │ │  :8109   │ │  :8111   │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

Axon connects to each server via its corresponding domain connector class.
The domain-specific connectors (`ebs_auth:8101` through `ebs_warehouse:8111`)
replace the legacy composite connectors.

---

## Phase 2–3 Integration Notes

- **ERP abstraction**: tools defined against `ebs_*` servers above should have
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
