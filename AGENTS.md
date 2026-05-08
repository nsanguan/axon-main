# AGENTS.md

## Project overview

Axon is an agentic Supply Chain Planning (ASCP) framework built for the AI era.
It is 100% MCP-native — no direct database connections. Every ERP (Oracle EBS,
SAP, Odoo) and knowledge base (RAG) is accessed through MCP servers. The system
orchestrates 10 domain agents that negotiate to produce optimal supply chain plans.

**Tech stack**: Python 3.11+, Pydantic v2, PydanticAI, LangGraph, MCP, Logfire,
PostgreSQL, Redis.

## Setup commands

```bash
# Create virtual environment
python3 -m venv .venv && source .venv/bin/activate

# Install in dev mode with all dependencies
pip install -e ".[dev]"
# or via requirements files:
pip install -r requirements.txt -r requirements-dev.txt

# Start infrastructure (Postgres + Redis)
docker compose -f infra/docker-compose.yml up -d

# Start MCP server stubs (for integration testing)
docker compose -f infra/docker-compose.yml --profile mcp-stubs up -d
```

## Build and test commands

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_schema.py

# Run with verbose output
pytest -v

# Lint
ruff check src/ tests/

# Format
ruff format src/ tests/

# Type check
mypy src/

# All checks (before committing)
ruff check src/ tests/ && ruff format --check src/ tests/ && mypy src/ && pytest
```

## Code style

- Python 3.11+ with full type annotations (`from __future__ import annotations`)
- Line length: 100 characters (configured in `pyproject.toml`)
- Pydantic v2 models for all structured data (`model_config`, `Field`, `ConfigDict`)
- Docstrings on all public modules, classes, and functions (Google style)
- Imports sorted with `ruff` (I rule): stdlib → third-party → axon
- Async-first: all I/O operations use `async`/`await`
- No bare `except`; always catch specific exception types
- Use `structlog` for application logging, not `print` or `logging`
- Use `logfire.span` for tracing critical operations (MCP calls, agent reasoning, negotiation rounds)

## Package layout

The installable package is `src/axon/`. All imports use the `axon.` prefix:

```python
from axon.core.config import settings
from axon.core.schema import Demand, Supply, Allocation, MCPToolOutput
from axon.agents.base_agent import DomainAgent
from axon.agents.tools import get_tools_for_agent
from axon.orchestrator.master_graph import MasterGraph
from axon.orchestrator.conflict_resolver import ConflictResolver, BusinessWeights
```

Do not use relative imports. The `src/` directory is for hatchling discovery; the
Python package starts at `src/axon/__init__.py`.

## Architecture layers

```
src/axon/
├── core/           # Schema models, config, learning, telemetry
├── connectors/     # MCP clients (oracle_ebs, sap, odoo, external_rag)
├── agents/         # 10 domain agents (commercial, technical, operations)
├── orchestrator/   # LangGraph master graph, conflict resolver, tools
└── dashboard/      # FastAPI backend, Next.js frontend
```

**Data flow**: MCP Server → Connector → MCPToolOutput → SemanticTransformer →
Domain models (Demand/Supply/Allocation) → Agent reasoning → Negotiation → Plan

**Key design invariants**:
- Agents never touch ERP-native IDs directly; they reason through `EntityRef`
- All MCP responses are normalized through `SemanticTransformer.can_handle()` routing
- Conflict resolution always terminates (max N rounds with utility-auction tiebreaker)
- Every MCP call carries a `correlation_id` for auditability

## Testing instructions

- **Unit tests** go in `tests/` matching the source structure (e.g., `tests/test_schema.py`)
- **Integration tests** use MCP server stubs from `tests/stubs/`
- **Simulation scenarios** are YAML files in `tests/scenarios/`
- All tests are async by default (`asyncio_mode = "auto"` in pyproject.toml)
- Test new schema models with round-trip validation (serialize → deserialize → verify)
- Test transformers with known MCPToolOutput inputs and expected domain model outputs
- Circuit breaker tests must verify state transitions: CLOSED → OPEN → HALF_OPEN → CLOSED
- Property-based tests verify invariants: utility monotonicity, supply bounds, demand completeness

## Commit and PR guidelines

- Commit messages: `type(scope): description` — e.g., `feat(schema): add Allocation model`
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`
- Scopes: `schema`, `config`, `agents`, `orchestrator`, `connectors`, `docs`, `infra`
- Run `ruff check && ruff format --check && mypy src/ && pytest` before committing
- PRs should reference the phase from `IMPLEMENT.md` they belong to

## Environment

- Copy `.env.example` to `.env` and fill in API keys and MCP server URLs
- All config is loaded via `pydantic-settings` with `AXON_` prefix
- Nested settings use double-underscore: `AXON_LLM__API_KEY`
- Never commit `.env` to version control (covered by `.gitignore`)

## Key documentation

| File | Purpose |
|------|---------|
| `README.md` | Project overview, features, roadmap |
| `IMPLEMENT.md` | Phased implementation plan with error strategy and KPIs |
| `docs/architecture.md` | System diagram, data flow, error model, negotiation algorithm |
| `docs/adr/001-mcp-only.md` | Architecture Decision Record for MCP-only design |
| `docs/mcp-tools.md` | Complete tool catalog per agent (44 tools across 10 agents) |
| `pyproject.toml` | Build config, dependencies, lint/type/test settings |
