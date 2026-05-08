---
name: logfire
description: Observability and tracing for Python applications with OpenTelemetry. Use when setting up structured logging, distributed tracing, agent call instrumentation, span-based performance monitoring, or integrating with PydanticAI/LangGraph for full agentic workflow visibility. Covers SDK initialization, span/trace logging, PydanticAI integration, and dashboard access.
---

# Logfire

## Quick start

```python
import logfire

logfire.configure(
    token="your-token",           # from logfire.dev
    service_name="axon",
    service_version="0.0.2",
)

logfire.info("Planning cycle started", demand_items=len(demands))

with logfire.span("resolve_conflicts") as span:
    result = negotiate(agents)
    span.set_attribute("rounds", result.rounds)
    span.set_attribute("resolved", result.resolved)
```

## Core patterns

### Spans

```python
# Decorator
@logfire.span("fetch_inventory")
async def fetch(item_id: str) -> dict:
    ...

# Context manager
with logfire.span("mcp_call", tool_name=tool) as span:
    result = await session.call_tool(tool, args)
    span.set_attribute("server", server_name)
    span.record_exception(e)  # on error
```

### Structured logging

```python
logfire.info("Plan approved", plan_id=str(uuid), approved_by=user)
logfire.warn("MCP degraded", server="oracle_ebs", attempts=3)
logfire.error("Negotiation deadlock", rounds=5, agents=10)
```

### PydanticAI integration

```python
import logfire
from pydantic_ai import Agent

logfire.configure(token="...")

# PydanticAI auto-instruments when logfire is configured before Agent creation:
agent = Agent("openai:gpt-4o")

# Manual instrumentation:
@agent.tool
@logfire.span("tool: {tool_name}")
async def my_tool(ctx, tool_name: str) -> str:
    ...
```

### LangGraph integration

```python
from logfire.integrations.langgraph import LogfireCallbackHandler

handler = LogfireCallbackHandler()
compiled = graph.compile(checkpointer=...)
result = compiled.invoke(input, config={"callbacks": [handler]})
```

## Configuration

```python
logfire.configure(
    token="...",                   # Required for cloud
    service_name="axon",
    service_version="0.0.2",
    environment="production",      # "development", "staging", "production"
    send_to_logfire=True,          # Set False for local-only
    console=logfire.ConsoleOptions(  # Pretty console output
        colors="auto",
        verbose=False,
    ),
)
```

## Best practices for Axon

- **Correlation IDs**: Every MCP tool call carries a `correlation_id` — pass it as a span attribute for end-to-end tracing.
- **Agent spans**: Each of the 10 domain agents gets its own top-level span per planning cycle. Tag with `agent_id`.
- **Negotiation rounds**: Each round is a child span. Record `round_number`, `global_utility`, and `resolved` as attributes.
- **Error tracking**: On circuit breaker trips, log at `error` with `server` and `consecutive_failures` attributes.

## Common pitfalls

- **Configure before creating agents**: PydanticAI auto-instruments only if Logfire is configured first. If you create an Agent before `logfire.configure()`, traces from that agent won't appear.
- **Don't log secrets**: Span attributes are stored in the cloud. Never set attributes containing API keys, passwords, or PII.
- **Span nesting**: Deep nesting (>20 levels) degrades dashboard performance. Use top-level spans for major phases, not individual tool calls.

## References

- Logfire dashboard: https://logfire.dev
- PydanticAI + Logfire: https://ai.pydantic.dev/logfire/
