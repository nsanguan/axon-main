# Axon (Agentic-ASCP) — Agent Policy

> **Axon** is an open-source, AI-native Supply Chain Planning (ASCP) engine.
> It is ERP-agnostic: the core reasoning layer (agents + orchestrator) never
> speaks directly to any ERP. All ERP interaction goes through MCP servers.
>
> Licensed under the Apache License 2.0.

This file defines the mandatory policies and operating rules for Axon.
All contributors and AI agents working in this repository MUST follow these policies.

---

## 1. MANDATORY: Always Check Odoo Skills First

## 1. Architecture Principle: MCP as the Universal Adapter

**Axon's core reasoning (agents + orchestrator) MUST NOT communicate directly with any ERP.**
All System-of-Record interactions are mediated exclusively through MCP servers.

```
┌─────────────────────────────────────────────┐
│   Agents + Orchestrator (ERP-agnostic)      │
│   PydanticAI  +  LangGraph                  │
└───────────────────┬─────────────────────────┘
                    │  MCP (SSE / stdio)
┌───────────────────▼─────────────────────────┐
│         MCP Servers (adapters)              │
│  mcp-ascp-planning │ mcp-ascp-procurement   │
│  mcp-ascp-inventory  (and future adapters)  │
└───────────────────┬─────────────────────────┘
                    │  XML-RPC / REST / SDK
┌───────────────────▼─────────────────────────┐
│       Systems of Record                     │
│  Odoo  │  SAP  │  Oracle  │  Custom         │
└─────────────────────────────────────────────┘
```

To add support for a new ERP: implement a new MCP server in `mcp_servers/` — the agents never change.

---

## 2. Skill Loading Policy

Before writing any code related to Odoo (the bundled reference adapter), load the relevant skill(s).

### Available Skills

| Skill | Path | Use When |
|-------|------|----------|
| `odoo-module-development` | `.github/skills/odoo-module-development/SKILL.md` | Creating or modifying a custom Odoo module |
| `odoo-orm` | `.github/skills/odoo-orm/SKILL.md` | Fields, decorators, CRUD, domains, recordsets |
| `odoo-views-xml` | `.github/skills/odoo-views-xml/SKILL.md` | Form/list/kanban/search views, XPath, QWeb |
| `odoo-security` | `.github/skills/odoo-security/SKILL.md` | Access rights, groups, record rules |
| `odoo-accounting` | `.github/skills/odoo-accounting/SKILL.md` | Invoices, journal entries, payments |
| `odoo-sales` | `.github/skills/odoo-sales/SKILL.md` | sale.order, quotations, CRM |
| `odoo-external-api` | `.github/skills/odoo-external-api/SKILL.md` | XML-RPC / JSON-RPC, external integrations |
| `odoo-debugging` | `.github/skills/odoo-debugging/SKILL.md` | Tracing errors, Odoo shell, logs, unit tests |
| `odoo-data-migration` | `.github/skills/odoo-data-migration/SKILL.md` | CSV/XML data import, migration scripts |
| `odoo-server-management` | `.github/skills/odoo-server-management/SKILL.md` | odoo-bin CLI, config, cron, shell |
| `odoo-extension` | `.github/skills/odoo-extension/SKILL.md` | HTTP controllers, REST endpoints, MCP server modules |
| `odoo-upgrade` | `.github/skills/odoo-upgrade/SKILL.md` | Upgrade/migration scripts, upgrade-utils |
| `odoo-db-schema` | `.github/skills/odoo-db-schema/SKILL.md` | SQL against live DB, table/column/FK relationships |
| `pydantic-ai` | `.github/skills/pydantic-ai/SKILL.md` | PydanticAI: Agent, tools, output, MCP, streaming, testing |

### Skill Loading Rule

1. Identify which skills are relevant to the current task.
2. Read the SKILL.md file(s) using the file reading tool.
3. Follow the patterns, conventions, and examples from the skill exactly.
4. For DB schema queries, also read the reference file under `.github/skills/odoo-db-schema/references/`.

---

## 3. Odoo Adapter Policy (Reference Implementation)

The bundled Odoo MCP adapter targets Odoo 17+ and is the reference implementation.

- **Connector**: `OdooXMLRPCClient` from `core/odoo_client.py` — XML-RPC only, no direct SQL
- **Version**: Always reference [Odoo 17.0 developer docs](https://www.odoo.com/documentation/17.0/developer.html)
- Do NOT use deprecated patterns (`<field name="attrs">`, `_columns` dict, Python 2 syntax)
- All credentials loaded from `.env` — never hardcoded in source

---

## 4. MCP Server Policy

- **Transport**: SSE (default) for all `mcp-ascp-*` servers
- **Naming**: All Axon ASCP servers use the `mcp-ascp-` prefix
- **Tool I/O**: All tool inputs and outputs must be Pydantic `BaseModel`
- **Field descriptions**: `Field(description=...)` is required on every input parameter
- **`ai_context`**: Every tool input model must include:
  ```python
  ai_context: str = Field(description="Reason why the agent is calling this tool")
  ```
- **Atomicity**: Multi-step operations must be wrapped in a single backend method — never multiple sequential API calls for related operations
- **Explainability**: Every tool that writes or updates a record MUST post the `ai_context` to the record's activity log (Chatter for Odoo) so humans can audit AI decisions

---

## 5. Agent & Orchestrator Policy

- **PydanticAI** is the sole agent framework — do not mix other agent libraries
- **LangGraph** is the sole orchestration framework — do not use raw asyncio graphs
- Agents receive data only through MCP tool calls — no direct imports of skill modules
- `ASCPState` is the single source of truth for the LangGraph workflow — never pass state via globals
- Confidence threshold: Planning Manager confidence < 0.7 → escalate to Executive Agent
- HITL gate: `langgraph.types.interrupt` is the only approved pause mechanism

---

## 6. Code Quality Policy

- All Python code must be compatible with Python 3.12+
- Follow PEP 8 and keep lines ≤ 100 characters
- Method names: `snake_case`. Class names: `PascalCase`
- Use `logging.getLogger(__name__)` for all logging — never `print()`
- No secrets in source code — always load from `.env` via `core/config.py`
- Parameterized queries only — no string-formatted SQL or RPC arguments

---

## 7. Security Policy

- All credentials from `.env` via `pydantic-settings` `BaseSettings`
- Never expose tokens, passwords, or API keys in logs, API responses, or Chatter messages
- Validate all external inputs at system boundaries (MCP tool inputs → Pydantic models)
- Confirm destructive operations with the user before executing

---

## 8. File Structure Reference

```
axon/                                     # Repository root
├── LICENSE                               # Apache 2.0
├── .env                                  # Credentials (never commit)
├── .github/skills/                       # Skill reference docs (read-only)
├── AGENT.md                              # This file — policy document
├── PROJECT_PLAN.md                       # Architecture & development phases
├── pyproject.toml                        # Root Python project (axon-ascp)
│
├── core/                                 # Shared infrastructure
│   ├── config.py                         # pydantic-settings BaseSettings
│   ├── odoo_client.py                    # Odoo XML-RPC adapter
│   └── skills/                           # Executable Python skill modules
│       ├── base_skill.py
│       ├── communication_skills.py
│       ├── planning_skills.py
│       ├── procurement_skills.py
│       ├── inventory_skills.py
│       ├── sales_skills.py
│       └── impact_analysis_skill.py
│
├── mcp_servers/
│   ├── mcp-ascp-planning/                # Planning MCP server (Odoo adapter)
│   ├── mcp-ascp-procurement/             # Procurement MCP server (Odoo adapter)
│   └── mcp-ascp-inventory/              # Inventory MCP server (Odoo adapter)
│
├── agents/
│   ├── planning_manager.py               # Planning Manager (PydanticAI)
│   ├── executive_agent.py                # Executive Agent (PydanticAI)
│   └── purchase/                         # Purchase Cluster (Buyer/Manager/Director)
│
└── orchestrator/
    ├── state.py                          # ASCPState TypedDict (LangGraph)
    ├── purchase_workflow.py              # Purchase sub-graph
    └── workflow.py                       # Main LangGraph StateGraph
```

