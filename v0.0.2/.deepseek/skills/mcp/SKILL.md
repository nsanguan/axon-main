---
name: mcp
description: Build and connect Model Context Protocol (MCP) servers and clients. Use when defining tools for AI agents to call, connecting to external systems via standardized JSON-RPC, or creating MCP server stubs for ERP/API integration. Covers tool registration, FastMCP, stdio/SSE/HTTP transports, resource primitives, and client patterns.
---

# Model Context Protocol (MCP)

## Quick start — Server

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool()
def get_inventory(item_id: str) -> dict:
    """Return current inventory for an item."""
    return {"item_id": item_id, "quantity": 42, "location": "WH-01"}

@mcp.resource("sop://{policy_id}")
def get_policy(policy_id: str) -> str:
    """Return a corporate SOP."""
    return fetch_from_rag(policy_id)

mcp.run(transport="stdio")  # or "sse" for HTTP
```

## Tool definition

```python
@mcp.tool(
    name="get_inventory_levels",       # optional, defaults to function name
    description="Fetch inventory...",  # optional, defaults to docstring
)
async def get_inventory(
    item_id: str,
    location: str | None = None,
) -> list[dict]:
    """Docstring becomes tool description if not explicitly set."""
    ...
```

Parameters are JSON Schema-typed from Python type hints. Supported: `str`, `int`, `float`, `bool`, `list`, `dict`, `BaseModel`, `Path`, `bytes`.

## Transports

| Transport | Use case | Server `run()` |
|-----------|----------|---------------|
| `stdio` | Local processes, subprocess spawn | `mcp.run(transport="stdio")` |
| `sse` | HTTP with Server-Sent Events | `mcp.run(transport="sse", host="0.0.0.0", port=8000)` |
| `streamable-http` | HTTP with streaming | `mcp.run(transport="streamable-http")` |

## Client — connecting to servers

```python
from mcp import ClientSession, StdioServerParameters, SseServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

# Stdio
params = StdioServerParameters(command="python", args=["-m", "my_server"])
async with stdio_client(params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("get_inventory", {"item_id": "X"})

# HTTP/SSE
params = SseServerParameters(url="http://localhost:8001/mcp")
async with sse_client(params) as (read, write):
    ...
```

## Resources

Resources expose read-only data (docs, policies, templates):

```python
@mcp.resource("file://docs/{name}")
def get_doc(name: str) -> str:
    return open(f"docs/{name}").read()

@mcp.resource("db://schema/{table}")
async def get_schema(table: str) -> str:
    return await db.get_schema(table)
```

Clients read resources: `content = await session.read_resource("file://docs/architecture.md")`

## FastMCP utilities

- **Context**: `from mcp.server.fastmcp import Context` — access request metadata, logging, progress reporting
- **Lifespan**: `@mcp.lifespan()` — async context manager for startup/shutdown (DB connections, cache warm)
- **Middleware**: `mcp.add_middleware(...)` — request/response interception

## ERP integration pattern (Axon)

Each ERP gets its own MCP server exposing tools. The Axon connector is a client:

```
ERP MCP Server                    Axon Connector (client)
     │                                    │
     │  tools: get_inventory              │  MCPToolOutput
     │         list_wip_jobs              │       │
     │         get_suppliers              │       ▼
     │         ...                        │  SemanticTransformer
     │                                    │       │
     │◄──── call_tool() ──────────────────│       ▼
     │                                    │  Domain models (Demand, Supply)
```

## Common pitfalls

- **Tool descriptions**: The LLM sees tool names and descriptions. Write them for the LLM, not for humans. Be specific about parameters and return values.
- **Long-running tools**: Use `ctx.report_progress()` for operations >10s, or the client may time out.
- **Schema changes**: When changing tool parameters, bump the server version. Clients using the old schema will get validation errors — handle them gracefully.

## References

- For agent consumption of MCP tools, see the `pydantic-ai` skill (MCPServerStdio, MCPServerHTTP).
- For the Axon error model around MCP unavailability, see `docs/architecture.md`.
