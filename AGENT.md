# EraOwl Odoo Agent — Policy

This file defines the mandatory policies and operating rules for this AI agent.
All contributors and AI agents working in this project MUST follow these policies.

---

## 1. MANDATORY: Always Check Odoo Skills First

Before writing any code, query, or configuration related to Odoo, you MUST load
and follow the relevant skill(s) from `.github/skills/`. Do NOT rely on general
knowledge alone — always consult the skills to ensure you use the correct
patterns for this specific Odoo instance.

### Available Skills

| Skill | Path | Use When |
|-------|------|----------|
| `odoo-module-development` | `.github/skills/odoo-module-development/SKILL.md` | Creating or modifying a custom Odoo module, `__manifest__.py`, model inheritance |
| `odoo-orm` | `.github/skills/odoo-orm/SKILL.md` | Defining fields, decorators (`@api.depends`, `@api.constrains`), CRUD, domains, recordsets |
| `odoo-views-xml` | `.github/skills/odoo-views-xml/SKILL.md` | Writing form/list/kanban/search views, XPath inheritance, QWeb reports |
| `odoo-security` | `.github/skills/odoo-security/SKILL.md` | Access rights, groups, `ir.model.access.csv`, record rules |
| `odoo-accounting` | `.github/skills/odoo-accounting/SKILL.md` | Invoices, journal entries, payments, account.move, reconciliation |
| `odoo-sales` | `.github/skills/odoo-sales/SKILL.md` | sale.order, quotations, pricelists, CRM, invoicing from sales |
| `odoo-external-api` | `.github/skills/odoo-external-api/SKILL.md` | XML-RPC / JSON-RPC API, external integrations, authentication |
| `odoo-debugging` | `.github/skills/odoo-debugging/SKILL.md` | Tracing errors, Odoo shell, logs, unit tests, SQL debugging, profiling |
| `odoo-data-migration` | `.github/skills/odoo-data-migration/SKILL.md` | Importing/exporting CSV/XML data, migration scripts, bulk loading |
| `odoo-server-management` | `.github/skills/odoo-server-management/SKILL.md` | Starting/stopping Odoo, `odoo-bin` CLI, config file, cron, shell |
| `odoo-extension` | `.github/skills/odoo-extension/SKILL.md` | Creating new Odoo modules from scratch, HTTP controllers, REST endpoints, JSON-2 API for Agentic AI, Odoo MCP server modules (mcp-buyer-agent, mcp-warehouse-agent, mcp-hr-agent) |
| `odoo-upgrade` | `.github/skills/odoo-upgrade/SKILL.md` | Upgrade/migration scripts (pre/post/end phases), upgrade-utils, renaming fields/models |
| `odoo-db-schema` | `.github/skills/odoo-db-schema/SKILL.md` | Writing SQL against the live DB, finding tables/columns/FK relationships |
| `pydantic-ai` | `.github/skills/pydantic-ai/SKILL.md` | Pydantic AI agent framework: Agent, tools, output, dependency injection, capabilities, multi-agent delegation, MCP client/server, streaming, testing with TestModel/FunctionModel, Logfire |

### Skill Loading Rule

1. Identify which skills are relevant to the current task.
2. Read the SKILL.md file(s) using the file reading tool.
3. Follow the patterns, conventions, and examples from the skill exactly.
4. For DB schema queries, also read the relevant reference file under `.github/skills/odoo-db-schema/references/`.

---

## 2. Odoo Version Policy

- **Odoo Version**: `19.4 alpha` (installed at `/u01/erp/Odoo/odoo-server`)
- **Target Documentation**: Always reference [Odoo 19.0 developer docs](https://www.odoo.com/documentation/19.0/developer.html)
- Do NOT use patterns from older Odoo versions (e.g., `<field name="attrs">`, old `_columns` dict, Python 2 syntax)
- Use the current Odoo 19 API: `attrs` replaced by `invisible`/`readonly`/`required` directly on fields

---

## 3. Database Policy

- **Live Database**: `odoo_db` on `202.71.1.13:5435`
- Connection credentials are stored in `.env` — always load from `.env`, never hardcode in source code
- Always check the `odoo-db-schema` skill and its reference files before writing SQL queries
- Use `sslmode=require` for all database connections
- Never run destructive SQL (`DROP`, `DELETE`, `TRUNCATE`) without explicit user confirmation
- Always use parameterized queries — never use string formatting to inject user values into SQL

---

## 4. Module Development Policy

Follow the `odoo-module-development` skill for all module work:

- Module structure must include: `__init__.py`, `__manifest__.py`, `models/`, `views/`, `security/`
- All new fields must have `string=`, and computed fields must declare `compute=` + `@api.depends`
- Use `_inherit` for extending existing models, `_name` + `_inherit` for delegation inheritance
- Never modify core Odoo files — always extend via inheritance
- `__manifest__.py` must list all `depends`, `data` files, and set a proper `version` (e.g. `19.4.0.0.0`)

---

## 5. Security Policy

Follow the `odoo-security` skill:

- Every new model MUST have a corresponding entry in `security/ir.model.access.csv`
- Use Odoo groups for access control — do NOT implement custom authentication
- Record rules must use `[('company_id', 'in', company_ids)]` for multi-company environments
- Never expose sensitive fields (passwords, tokens) through computed fields or API responses
- API keys must be stored as `ir.config_parameter` or environment variables, never in source code

---

## 6. Code Quality Policy

- All Python code must be compatible with Python 3.10+
- Follow [OCA coding guidelines](https://github.com/OCA/maintainer-tools/blob/master/CONTRIBUTING.md) and PEP 8
- Method names: `snake_case`. Model names: `dot.case`. Class names: `PascalCase`
- Use `_logger = logging.getLogger(__name__)` for all logging — never use `print()`
- Avoid `sudo()` unless strictly necessary; document why it is used when you do
- Never use `search([])` on large models without a domain filter — always add a limiting domain

---

## 7. Extension & Integration Policy

Follow the `odoo-extension` skill for new modules, HTTP controllers, and MCP agents.
Follow the `odoo-upgrade` skill for version migrations:

- Upgrade scripts go in `module/migrations/{odoo_version}.{module_version}/`
- Use `pre-` scripts for structural changes (rename fields/models)
- Use `post-` scripts for data migration and recomputing fields
- Always use `odoo.upgrade.util` helper functions — do NOT write raw SQL for rename operations
- Test upgrade scripts on a copy of the production database before applying to production

---

## 8. External API Policy

Follow the `odoo-external-api` skill:

- Always authenticate via API key (`api_key` parameter) — never store user passwords in client code
- Validate all inputs from external systems before passing to the ORM
- Rate-limit API calls in integrations — do not hammer the Odoo RPC endpoint in tight loops
- Use JSON-RPC 2.0 endpoint (`/web/dataset/call_kw`) for all external calls

---

## 9. Server & Deployment Policy

Follow the `odoo-server-management` skill:

- Odoo server: `/u01/erp/Odoo/odoo-server/odoo-bin`
- Config file: `/u01/erp/Odoo/odoo.conf`
- Python venv: `/u01/erp/Odoo/venv`
- Always restart Odoo after modifying Python files or installing modules
- Always upgrade the module (`-u module_name`) after modifying XML views or security files
- Never restart the production server without confirming with the user

---

## 10. Response Policy

When answering any Odoo-related question or implementing any Odoo feature:

1. **Load the skill** — read the relevant SKILL.md before responding
2. **Check the DB schema** — for any SQL or model question, check `odoo-db-schema` references
3. **Cite the skill** — mention which skill you used to form your answer
4. **Follow Odoo conventions** — use standard Odoo patterns, not generic Python/SQL patterns
5. **Test before confirming** — if using the Odoo shell or psql, verify results before declaring done
6. **Confirm destructive actions** — always ask the user before DROP, DELETE, or server restart

---

## 11. MCP Server Policy (ASCP-specific)

This project builds FastMCP servers for Odoo 19.4 alpha. Mandatory rules:

- **Connector**: Use `OdooXMLRPCClient` from `core/odoo_client.py` — never psycopg2, never direct SQL
- **Transport**: SSE (default) for all `mcp-ascp-*` servers
- **Naming**: All ASCP servers use the `mcp-ascp-` prefix
- **Tool I/O**: All tool inputs and outputs must be Pydantic `BaseModel`
- **Field descriptions**: `Field(description=...)` is required on every input parameter
- **ai_context**: Every tool input model must include `ai_context: str = Field(description="Reason why the agent is calling this tool")`
- **Atomicity**: Multi-step Odoo operations must be wrapped in a single custom Odoo method — never multiple sequential API calls for related operations

---

## 12. File Structure Reference

```
/u01/eraowl-ai-system/EraOwl-Agentic-ASCP/
├── .env                                  # Credentials (never commit)
├── .gitignore
├── .github/skills/                       # Odoo skill reference files (read-only)
│   ├── odoo-accounting/SKILL.md
│   ├── odoo-data-migration/SKILL.md
│   ├── odoo-db-schema/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── odoo-debugging/SKILL.md
│   ├── odoo-extension/SKILL.md
│   ├── odoo-external-api/SKILL.md
│   ├── odoo-module-development/SKILL.md
│   ├── odoo-orm/SKILL.md
│   ├── odoo-sales/SKILL.md
│   ├── odoo-security/SKILL.md
│   ├── odoo-server-management/SKILL.md
│   ├── odoo-upgrade/SKILL.md
│   ├── odoo-views-xml/SKILL.md
│   └── pydantic-ai/SKILL.md
├── AGENT.md                              # This file — project policy
├── PROJECT_PLAN.md                       # Development phases & architecture
├── pyproject.toml                        # Root Python project config
│
├── core/                                 # Shared infrastructure
│   ├── __init__.py
│   ├── config.py                         # pydantic-settings BaseSettings
│   └── odoo_client.py                    # OdooXMLRPCClient (XML-RPC wrapper)
│
├── mcp_servers/
│   ├── mcp-ascp-planning/                # Phase 2A — primary planning server
│   │   ├── pyproject.toml
│   │   ├── server.py                     # FastMCP entry point (SSE transport)
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── pegging.py                # Pegging ledger tools
│   │       └── demand.py                 # Demand stream tools
│   ├── mcp-ascp-procurement/             # Phase 2B — procurement server
│   │   ├── pyproject.toml
│   │   ├── server.py
│   │   └── tools/__init__.py
│   └── mcp-ascp-inventory/               # Phase 2C — inventory server
│       ├── pyproject.toml
│       ├── server.py
│       └── tools/__init__.py
│
├── agents/
│   ├── __init__.py
│   ├── planning_manager.py               # Phase 3 — Planning Manager Agent
│   └── executive_agent.py               # Phase 3 — Executive Agent
│
└── orchestrator/
    ├── __init__.py
    ├── state.py                          # Phase 4 — ASCPState TypedDict
    └── workflow.py                       # Phase 4 — LangGraph StateGraph
```


