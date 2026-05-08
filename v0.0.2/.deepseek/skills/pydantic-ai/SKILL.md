---
name: pydantic-ai
description: Build type-safe AI agents with PydanticAI. Use when creating LLM-powered agents that need structured input/output validation, dependency injection, tool calling, MCP server integration, streaming, and result type safety. Covers Agent, Tool, RunContext, MCP tool registration, dependency injection patterns, and agent orchestration.
---

# PydanticAI

## Quick start

```python
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

class Result(BaseModel):
    plan: str
    confidence: float

agent = Agent(
    "openai:gpt-4o",
    result_type=Result,
    system_prompt="You are a planner. Return structured results.",
)

result = agent.run_sync("Create a production plan for Q3")
print(result.data.plan, result.data.confidence)
```

## Core patterns

### Agent definition

```python
agent = Agent(
    model="openai:gpt-4o",          # or "anthropic:claude-3-5-sonnet"
    result_type=OutputModel,        # Pydantic model for structured output
    system_prompt="System prompt",
    deps_type=Deps,                 # Dependency type for injection
)
```

Model strings: `openai:`, `anthropic:`, `google-gla:`, `groq:`, `mistral:`, `cohere:`, `ollama:`.

### Tools

```python
@agent.tool
async def get_inventory(ctx: RunContext[Deps], item_id: str) -> int:
    """Return current inventory level for an item."""
    return await ctx.deps.db.fetch_inventory(item_id)

@agent.tool_plain
def add(a: int, b: int) -> int:
    return a + b
```

Tool docstrings are sent to the LLM — write them clearly.

### MCP tools (Model Context Protocol)

```python
from pydantic_ai.mcp import MCPServerStdio, MCPServerHTTP

# Stdio transport (local server):
server = MCPServerStdio("python", ["-m", "mcp_server"])
agent = Agent("openai:gpt-4o", mcp_servers=[server])

# HTTP transport (remote server):
server = MCPServerHTTP("http://localhost:8001/mcp")
agent = Agent("openai:gpt-4o", mcp_servers=[server])
```

All tools exposed by the MCP server become available to the agent automatically.

### Dependency injection

```python
from dataclasses import dataclass

@dataclass
class Deps:
    db: AsyncDatabase
    config: Settings

agent = Agent("openai:gpt-4o", deps_type=Deps)

@agent.tool
async def query(ctx: RunContext[Deps], sql: str) -> list:
    return await ctx.deps.db.execute(sql)
```

Pass deps at runtime: `agent.run("prompt", deps=Deps(db=..., config=...))`

### Result validation

```python
from pydantic_ai import Agent

agent = Agent("openai:gpt-4o", result_type=MyModel)

@agent.result_validator
async def validate_result(ctx: RunContext, result: MyModel) -> MyModel:
    if result.confidence < 0.5:
        raise ModelRetry("Confidence too low, reconsider.")
    return result
```

### Streaming

```python
async with agent.run_stream("prompt") as stream:
    async for chunk in stream:
        print(chunk, end="")
```

## Agent orchestration

```python
from pydantic_ai import Agent

planner = Agent("openai:gpt-4o", result_type=Plan)
executor = Agent("openai:gpt-4o")

plan = await planner.run("Design a solution")
result = await executor.run(f"Execute this plan: {plan.data}")
```

## Common pitfalls

- **Result type validation**: PydanticAI retries on `ValidationError` by default. If your output is ambiguous, add a `result_validator` to guide retries.
- **MCP tool naming**: MCP servers expose tools with names like `get_inventory_levels` — ensure your system prompt references these by their full MCP name.
- **Deps must be hashable**: Dataclasses with `frozen=True` or Pydantic models work. Plain mutable objects will cause issues with caching.

## References

- For agent tool definitions in Axon, see the `mcp` skill for server-side patterns.
- For graph-based orchestration of multiple agents, see the `langgraph` skill.
