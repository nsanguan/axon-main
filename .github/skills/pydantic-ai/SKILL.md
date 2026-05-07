---
name: pydantic-ai
description: >
  Build, test, and extend AI agents using the Pydantic AI framework.
  Use for: creating Agent objects, registering tools, structured output,
  dependency injection, multi-agent delegation, MCP client/server integration,
  streaming, capabilities, testing with TestModel/FunctionModel, Logfire
  observability, and agent specs (YAML). Covers pydantic_ai 0.x (Python 3.10+).
argument-hint: >
  Describe what you want to build: an agent with tools, structured output,
  multi-agent coordination, MCP integration, streaming, or testing strategy.
---

# Pydantic AI Skill

> **Source docs:** https://ai.pydantic.dev  
> **llms.txt:** https://ai.pydantic.dev/llms.txt  
> **Full text:** https://ai.pydantic.dev/llms-full.txt

Pydantic AI is a Python agent framework — think "FastAPI for GenAI". It is:
- **Model-agnostic**: OpenAI, Anthropic, Google Gemini, Groq, Mistral, Cohere, Bedrock, HuggingFace, …
- **Type-safe**: deps, output, context are all typed and validated via Pydantic
- **Production-ready**: Logfire observability, streaming, MCP, A2A, durable execution

---

## 1. Installation

```bash
# Full install (includes Logfire)
pip install pydantic-ai

# Slim install for a specific model
pip install "pydantic-ai-slim[openai]"
pip install "pydantic-ai-slim[anthropic]"
pip install "pydantic-ai-slim[google]"
pip install "pydantic-ai-slim[openai,google,logfire]"

# With MCP support
pip install "pydantic-ai-slim[mcp]"
pip install "pydantic-ai-slim[fastmcp]"
```

**Requires Python 3.10+**

---

## 2. Hello World

```python
from pydantic_ai import Agent

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    instructions='You are a concise assistant.',
)

result = agent.run_sync('What is the capital of France?')
print(result.output)  # Paris
```

---

## 3. Agent Construction

```python
from pydantic_ai import Agent
from pydantic_ai.models import ModelSettings

agent = Agent(
    'openai:gpt-5.2',           # model string — see §4 for all models
    deps_type=MyDeps,            # type annotation for dependency injection
    output_type=MyOutput,        # structured output type (Pydantic BaseModel)
    instructions='...',          # static system instructions (current agent only)
    capabilities=[...],          # reusable capability bundles (§9)
    tools=[...],                 # function tools list (§6)
    toolsets=[...],              # toolset collections (MCP servers, etc.)
    model_settings=ModelSettings(temperature=0.5),
    retries=1,                   # default retry count for tools
    max_concurrency=10,          # max concurrent runs (queues excess)
    name='my_agent',             # optional agent name for logging
)
```

### Instructions vs System Prompts

| Feature | `instructions=` | `@agent.system_prompt` |
|---|---|---|
| Appears in message history | No (current agent only) | Yes (preserved across turns) |
| Use case | Most agents | Multi-turn conversations |

```python
# Static instructions parameter
agent = Agent('openai:gpt-5.2', instructions='Be concise.')

# Dynamic instructions via decorator
@agent.instructions
def build_instructions(ctx: RunContext[MyDeps]) -> str:
    return f'Help user {ctx.deps.username}.'

# Runtime override
result = agent.run_sync('...', instructions='Override instructions.')

# System prompt — preserved in message history
@agent.system_prompt
async def get_system_prompt(ctx: RunContext[MyDeps]) -> str:
    data = await ctx.deps.http_client.get('https://example.com')
    return f'Context: {data.text}'
```

---

## 4. Model Strings

```python
# OpenAI
'openai:gpt-5.2'
'openai:gpt-4o'

# Anthropic
'anthropic:claude-sonnet-4-6'
'anthropic:claude-opus-4-6'
'anthropic:claude-haiku-3-5'

# Google
'google-gla:gemini-3-flash-preview'
'google-gla:gemini-2.0-flash'

# Groq
'groq:llama-3.3-70b-versatile'

# Programmatic model object
from pydantic_ai.models.openai import OpenAIChatModel
model = OpenAIChatModel('gpt-5.2', settings=ModelSettings(temperature=0.8))
agent = Agent(model)
```

---

## 5. Running Agents

Five run methods — choose based on sync/async/streaming needs:

```python
# 1. Async — main method
result = await agent.run('prompt', deps=my_deps)
print(result.output)

# 2. Sync wrapper — convenience for scripts/tests
result = agent.run_sync('prompt', deps=my_deps)

# 3. Stream text — incremental text output
async with agent.run_stream('prompt', deps=my_deps) as result:
    async for text in result.stream_text():          # cumulative text
        print(text, end='', flush=True)
    async for chunk in result.stream_text(delta=True):  # delta chunks
        print(chunk, end='', flush=True)

# 4. Stream events — raw event objects
async for event in agent.run_stream_events('prompt', deps=my_deps):
    print(type(event).__name__, event)

# 5. Iter — node-by-node graph traversal
async with agent.iter('prompt', deps=my_deps) as run:
    async for node in run:
        print(node)
    print(run.result.output)
```

### Run Result

```python
result.output              # final typed output
result.usage()             # RunUsage(input_tokens, output_tokens, requests)
result.all_messages()      # full message history (ModelRequest + ModelResponse)
result.new_messages()      # only messages from this run
```

### Multi-turn Conversations

```python
result1 = agent.run_sync('Hello')
result2 = agent.run_sync(
    'What did I just say?',
    message_history=result1.new_messages(),
)
```

### Usage Limits

```python
from pydantic_ai.usage import UsageLimits

agent.run_sync(
    'prompt',
    usage_limits=UsageLimits(
        request_limit=3,
        response_tokens_limit=500,
        total_tokens_limit=1000,
        tool_calls_limit=5,
    ),
)
```

### Model Settings (3 levels — later overrides earlier)

```python
# Level 1: model object
model = OpenAIChatModel('gpt-5.2', settings=ModelSettings(temperature=0.8))

# Level 2: agent constructor
agent = Agent(model, model_settings=ModelSettings(temperature=0.5))

# Level 3: run call (highest priority)
agent.run_sync('prompt', model_settings=ModelSettings(temperature=0.0))
```

---

## 6. Function Tools

Tools let the model call Python functions during a run.

### Registration Methods

```python
from pydantic_ai import Agent, RunContext, Tool
import random

agent = Agent('openai:gpt-5.2', deps_type=str)

# Method 1: @agent.tool — receives RunContext (access deps, retry count, etc.)
@agent.tool
async def get_player_name(ctx: RunContext[str]) -> str:
    """Get the player's name."""
    return ctx.deps

# Method 2: @agent.tool_plain — no RunContext
@agent.tool_plain
def roll_dice() -> str:
    """Roll a six-sided die and return the result."""
    return str(random.randint(1, 6))

# Method 3: tools= constructor arg (for reuse across agents)
agent_b = Agent(
    'openai:gpt-5.2',
    deps_type=str,
    tools=[
        roll_dice,                            # plain function, no ctx
        Tool(get_player_name, takes_ctx=True), # explicit ctx flag
    ],
)
```

### Per-tool Retry and ModelRetry

```python
from pydantic_ai import ModelRetry

@agent.tool(retries=3)
async def call_api(ctx: RunContext[MyDeps], endpoint: str) -> str:
    """Call an external API."""
    resp = await ctx.deps.http_client.get(endpoint)
    if resp.status_code == 429:
        raise ModelRetry('Rate limited, please try a different endpoint')
    return resp.text
```

### Tool Schema from Docstrings

Pydantic AI extracts parameter descriptions from docstrings automatically.
Supports Google, NumPy, and Sphinx docstring formats.

```python
@agent.tool_plain(docstring_format='google', require_parameter_descriptions=True)
def foobar(a: int, b: str, c: dict[str, list[float]]) -> str:
    """Get me foobar.

    Args:
        a: apple pie
        b: banana cake
        c: carrot smoothie
    """
    return f'{a} {b} {c}'
```

### RunContext Fields

```python
ctx.deps       # dependency object (typed)
ctx.usage      # RunUsage accumulator — pass to sub-agents
ctx.retry      # current retry attempt number (0-indexed)
ctx.messages   # message history so far
ctx.agent      # the Agent instance
```

---

## 7. Dependency Injection

Dependencies provide external resources (DB connections, HTTP clients, API keys) to tools and system prompts.

```python
from dataclasses import dataclass
import httpx
from pydantic_ai import Agent, RunContext

@dataclass
class MyDeps:
    api_key: str
    http_client: httpx.AsyncClient

agent = Agent('openai:gpt-5.2', deps_type=MyDeps)

@agent.system_prompt
async def get_system_prompt(ctx: RunContext[MyDeps]) -> str:
    resp = await ctx.deps.http_client.get(
        'https://example.com',
        headers={'Authorization': f'Bearer {ctx.deps.api_key}'},
    )
    return f'Context: {resp.text}'

@agent.tool
async def fetch_data(ctx: RunContext[MyDeps], query: str) -> str:
    resp = await ctx.deps.http_client.get(
        'https://example.com/data',
        params={'q': query},
        headers={'Authorization': f'Bearer {ctx.deps.api_key}'},
    )
    return resp.text

async def main():
    async with httpx.AsyncClient() as client:
        deps = MyDeps(api_key='secret', http_client=client)
        result = await agent.run('Tell me a joke.', deps=deps)
        print(result.output)
```

### Sync vs Async Dependencies

Both work — sync functions are run via `run_in_executor` in a thread pool.
`run_sync()` is just a wrapper; agents always run in an async context internally.

### Overriding Dependencies in Tests

```python
with agent.override(deps=test_deps):
    result = await application_code('prompt')
```

---

## 8. Structured Output

```python
from pydantic import BaseModel
from pydantic_ai import Agent

class CityInfo(BaseModel):
    city: str
    country: str
    population: int

agent = Agent('openai:gpt-5.2', output_type=CityInfo)
result = agent.run_sync('Tell me about Paris.')
print(result.output.city)       # Paris
print(result.output.population) # typed int
```

### Output Modes

```python
from pydantic_ai.output import ToolOutput, NativeOutput, PromptedOutput

# Default: use tool calls (most compatible)
agent = Agent('...', output_type=ToolOutput(CityInfo))

# Native structured output (model-specific JSON mode)
agent = Agent('...', output_type=NativeOutput([Fruit, Vehicle]))

# Prompted: inject format instructions into prompt (widest compatibility)
agent = Agent('...', output_type=PromptedOutput([Fruit, Vehicle]))
```

### Multiple Output Types (Union)

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2', output_type=[CityInfo, str])  # list form
# result.output is CityInfo | str
```

### Output Validators

```python
from pydantic_ai import Agent, ModelRetry, RunContext

@agent.output_validator
async def validate(ctx: RunContext[MyDeps], output: CityInfo) -> CityInfo:
    if output.population < 0:
        raise ModelRetry('Population must be positive, please retry.')
    return output
```

### Output Functions (one-way handoff — model calls function, result not returned)

```python
def process_sql(query: str) -> list[dict]:
    """Execute a SQL query and return results."""
    return run_sql(query)

class SQLError(BaseModel):
    message: str

agent = Agent('openai:gpt-5.2', output_type=[process_sql, SQLError])
# When model calls process_sql(), that IS the final result
```

### Streaming Structured Output

```python
async with agent.run_stream(prompt) as result:
    async for partial in result.stream_output():  # yields partial BaseModel
        print(partial)
    final = result.output  # complete object after stream ends
```

---

## 9. Capabilities

Capabilities are reusable bundles of tools, hooks, instructions, and model settings.

### Built-in Capabilities

```python
from pydantic_ai.capabilities import (
    Thinking,            # model thinking/reasoning (Anthropic, Google)
    WebSearch,           # web search (provider builtin or DuckDuckGo fallback)
    WebFetch,            # fetch URL content
    ImageGeneration,     # generate images
    MCP,                 # connect to an MCP server (as builtin tool)
    Hooks,               # lifecycle hooks
    PrepareTools,        # filter/modify tool definitions before model call
    ThreadExecutor,      # custom thread pool for sync tools
    ReinjectSystemPrompt, # re-add system prompt when missing from history
)

agent = Agent(
    'anthropic:claude-sonnet-4-6',
    capabilities=[
        Thinking(effort='high'),
        WebSearch(),
        WebFetch(),
    ],
)
```

### Custom Capability

```python
from dataclasses import dataclass
from typing import Any
from pydantic_ai.capabilities import AbstractCapability

@dataclass
class MyLoggingCapability(AbstractCapability[Any]):
    def get_instructions(self):
        return 'Always respond in bullet points.'

    async def before_model_request(self, ctx, *, request_context):
        print(f'Sending request: {request_context}')
        return request_context

    async def after_model_request(self, ctx, *, request_context, response):
        print(f'Got response: {response}')
        return response
```

### Agent Specs (YAML)

```yaml
# agent.yaml
model: anthropic:claude-opus-4-6
instructions: You are a helpful assistant.
capabilities:
  - WebSearch
  - Thinking:
      effort: high
```

```python
agent = Agent.from_file('agent.yaml')
result = agent.run_sync('Search for Pydantic AI news')
```

---

## 10. Testing

### Block Real LLM Calls (Global)

```python
from pydantic_ai import models
models.ALLOW_MODEL_REQUESTS = False  # raises error if real model called
```

### TestModel — Fastest, Auto-generates Valid Data

```python
from pydantic_ai.models.test import TestModel

# Override for a single test
with agent.override(model=TestModel()):
    result = agent.run_sync('test prompt')
    # TestModel calls ALL registered tools automatically
    # Generates valid data matching tool schemas

# Check what was called
test_model = TestModel()
with agent.override(model=test_model):
    result = agent.run_sync('test')
print(test_model.last_model_request_parameters.function_tools)
```

### FunctionModel — Full Control Over Model Behavior

```python
from pydantic_ai import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

def my_model_logic(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    if len(messages) == 1:
        # First call: invoke a tool
        return ModelResponse(parts=[ToolCallPart('my_tool', {'arg': 'value'})])
    else:
        # Second call: return final answer
        tool_result = messages[-1].parts[0]
        return ModelResponse(parts=[TextPart(f'Result: {tool_result.content}')])

with agent.override(model=FunctionModel(my_model_logic)):
    result = agent.run_sync('test')
```

### pytest Fixture Pattern

```python
import pytest
from pydantic_ai.models.test import TestModel
from myapp import my_agent

@pytest.fixture
def override_agent():
    with my_agent.override(model=TestModel()):
        yield

async def test_something(override_agent):
    result = await my_agent.run('test')
    assert result.output is not None
```

### Capturing Run Messages

```python
from pydantic_ai import capture_run_messages

with capture_run_messages() as messages:
    with agent.override(model=TestModel()):
        result = agent.run_sync('prompt')

# Inspect full message exchange
for msg in messages:
    print(msg)
```

### Override Model, Deps, or Toolsets

```python
with agent.override(model=TestModel(), deps=test_deps):
    result = agent.run_sync('test')
```

---

## 11. Multi-Agent Patterns

Five complexity levels:

| Level | Pattern | When to Use |
|-------|---------|-------------|
| 1 | Single agent | Most cases |
| 2 | Agent delegation | Sub-tasks via tools |
| 3 | Programmatic handoff | Sequential agents in app code |
| 4 | Graph-based (pydantic-graph) | Complex state machines |
| 5 | Deep agents | Autonomous planning + code execution |

### Agent Delegation (agent calls another agent via tool)

```python
from pydantic_ai import Agent, RunContext, UsageLimits

child_agent = Agent('google-gla:gemini-3-flash-preview', output_type=list[str])
parent_agent = Agent(
    'openai:gpt-5.2',
    instructions='Use joke_factory to get jokes, then pick the best one.',
)

@parent_agent.tool
async def joke_factory(ctx: RunContext[None], count: int) -> list[str]:
    result = await child_agent.run(
        f'Generate {count} jokes.',
        usage=ctx.usage,   # IMPORTANT: accumulate usage across agents
    )
    return result.output

result = parent_agent.run_sync(
    'Tell me a joke.',
    usage_limits=UsageLimits(request_limit=5, total_tokens_limit=500),
)
```

**Key rules:**
- Always pass `usage=ctx.usage` to sub-agent runs to track total usage
- Use `UsageLimits` to prevent runaway loops
- Different models are OK in the same run (but cross-model cost tracking won't work)
- One-way handoff (no return to parent): use output functions instead

### Programmatic Handoff (app code calls agents in sequence)

```python
from pydantic_ai import Agent, ModelMessage, RunUsage, UsageLimits
from pydantic import BaseModel

class FlightDetails(BaseModel):
    flight_number: str

flight_agent = Agent('openai:gpt-5.2', output_type=FlightDetails)
seat_agent = Agent('openai:gpt-5.2', output_type=SeatPreference)

usage = RunUsage()
usage_limits = UsageLimits(request_limit=15)

# First agent: find flight
flight_result = await flight_agent.run(
    'Find a flight from NYC to LAX',
    usage=usage,
    usage_limits=usage_limits,
)
flight = flight_result.output

# Second agent: pick seat (independent message history)
seat_result = await seat_agent.run(
    'Window seat please',
    usage=usage,
    usage_limits=usage_limits,
)
seat = seat_result.output
```

---

## 12. MCP Integration

Pydantic AI supports MCP (Model Context Protocol) as both client and server.

### MCP Client — Connecting to MCP Servers

Three transport types:

```python
from pydantic_ai import Agent
from pydantic_ai.mcp import (
    MCPServerStreamableHTTP,  # HTTP Streamable (recommended)
    MCPServerSSE,             # HTTP SSE (deprecated)
    MCPServerStdio,           # subprocess via stdin/stdout
)

# Streamable HTTP (recommended)
server = MCPServerStreamableHTTP('http://localhost:8000/mcp')
agent = Agent('openai:gpt-5.2', toolsets=[server])

# SSE (deprecated but still used)
server = MCPServerSSE('http://localhost:3001/sse')
agent = Agent('openai:gpt-5.2', toolsets=[server])

# stdio subprocess
server = MCPServerStdio('python', args=['mcp_server.py'], timeout=10)
agent = Agent('openai:gpt-5.2', toolsets=[server])

# Run agent — server connection managed automatically
async def main():
    result = await agent.run('What is 7 plus 5?')
    print(result.output)  # The answer is 12.

# Or explicitly manage connection lifetime
async with agent:  # opens/closes all MCP connections
    result = await agent.run('...')
```

### Load MCP Servers from JSON Config

```json
// mcp_config.json
{
  "mcpServers": {
    "python-runner": {
      "command": "uv",
      "args": ["run", "mcp-run-python", "stdio"]
    },
    "weather-api": {
      "url": "http://localhost:3001/sse"
    },
    "calculator": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

```python
from pydantic_ai.mcp import load_mcp_servers

servers = load_mcp_servers('mcp_config.json')  # supports ${ENV_VAR} expansion
agent = Agent('openai:gpt-5.2', toolsets=servers)
```

### Tool Prefix (Avoid Name Conflicts)

```python
weather_server = MCPServerSSE('http://localhost:3001/sse', tool_prefix='weather')
calc_server = MCPServerSSE('http://localhost:3002/sse', tool_prefix='calc')
# Tools exposed as: weather_get_forecast, calc_add, etc.
agent = Agent('openai:gpt-5.2', toolsets=[weather_server, calc_server])
```

### MCP Sampling (Server proxies LLM calls through client)

```python
# Enable sampling on all MCP servers registered with the agent
agent.set_mcp_sampling_model()
# Or pass a specific model
agent.set_mcp_sampling_model('openai:gpt-5.2')
# Disable sampling on a specific server
server = MCPServerStdio('python', args=['server.py'], allow_sampling=False)
```

### MCP Resources

```python
async with server:
    resources = await server.list_resources()
    for r in resources:
        print(r.name, r.uri, r.mime_type)
    content = await server.read_resource('resource://user_name.txt')
    print(content)  # str for text, BinaryContent for binary
```

### MCP Elicitation (Server requests structured input from client)

```python
from mcp.client.session import ClientSession
from mcp.types import ElicitRequestParams, ElicitResult
from pydantic_ai.mcp import MCPServerStdio

async def handle_elicitation(context, params: ElicitRequestParams) -> ElicitResult:
    print(params.message)
    # Collect user input, return ElicitResult
    return ElicitResult(action='accept', content={'restaurant': 'Roma', 'party_size': 2, 'date': '25-12-2025'})

server = MCPServerStdio('python', args=['server.py'], elicitation_callback=handle_elicitation)
agent = Agent('openai:gpt-5.2', toolsets=[server])
```

---

## 13. Logfire Observability

```python
import logfire

logfire.configure()                   # set up Logfire (reads LOGFIRE_TOKEN from env)
logfire.instrument_pydantic_ai()      # traces all agent runs automatically

# Optional: also instrument DB, HTTP
logfire.instrument_sqlite3()
logfire.instrument_httpx()

# Now run agents normally — all runs are traced
result = agent.run_sync('Tell me a joke.')
```

Logfire traces show:
- Messages sent/received
- Tool call names, arguments, return values
- Token usage and latency per step
- Errors and retries
- Full multi-agent delegation trees

For multi-agent systems:
```python
import logfire
logfire.configure()
logfire.instrument_pydantic_ai()

# All agent.run() calls now appear as child spans under the root request
```

---

## 14. Common Patterns

### Agent with Database and HTTP Dependencies

```python
from dataclasses import dataclass
import httpx
from pydantic_ai import Agent, RunContext

@dataclass
class AppDeps:
    db_conn: DatabaseConn
    http_client: httpx.AsyncClient
    api_key: str

agent = Agent('openai:gpt-5.2', deps_type=AppDeps)

@agent.tool
async def query_db(ctx: RunContext[AppDeps], sql: str) -> list[dict]:
    """Query the database."""
    return await ctx.deps.db_conn.fetch(sql)

@agent.tool
async def call_api(ctx: RunContext[AppDeps], endpoint: str) -> str:
    """Call an external API endpoint."""
    resp = await ctx.deps.http_client.get(
        endpoint,
        headers={'Authorization': f'Bearer {ctx.deps.api_key}'},
    )
    resp.raise_for_status()
    return resp.text

async def run(prompt: str):
    async with httpx.AsyncClient() as client:
        deps = AppDeps(db_conn=get_db(), http_client=client, api_key='...')
        return await agent.run(prompt, deps=deps)
```

### Streaming with Progress Updates

```python
import sys

async def stream_response(prompt: str):
    async with agent.run_stream(prompt) as result:
        async for chunk in result.stream_text(delta=True):
            sys.stdout.write(chunk)
            sys.stdout.flush()
    return result.output
```

### Retry on Tool Failure

```python
from pydantic_ai import ModelRetry

@agent.tool(retries=3)
async def flaky_tool(ctx: RunContext[MyDeps], arg: str) -> str:
    """Try to fetch data, retry on transient errors."""
    try:
        return await ctx.deps.fetch(arg)
    except TimeoutError:
        raise ModelRetry(f'Timeout fetching {arg}, please try again')
```

### Model Override for Environment

```python
import os
from pydantic_ai import Agent

MODEL = os.getenv('AI_MODEL', 'openai:gpt-5.2')
agent = Agent(MODEL)
```

---

## 15. API Quick Reference

| Symbol | Purpose |
|--------|---------|
| `Agent(model, ...)` | Create an agent |
| `agent.run(prompt, deps=...)` | Async run |
| `agent.run_sync(prompt, deps=...)` | Sync run |
| `agent.run_stream(prompt)` | Async context manager for streaming |
| `agent.iter(prompt)` | Node-by-node iteration |
| `agent.override(model=..., deps=...)` | Context manager for test overrides |
| `@agent.tool` | Register tool with RunContext |
| `@agent.tool_plain` | Register tool without RunContext |
| `@agent.system_prompt` | Dynamic system prompt (preserved in history) |
| `@agent.instructions` | Dynamic instructions (not in history) |
| `@agent.output_validator` | Validate/transform agent output |
| `RunContext[T]` | Context passed to tools/prompts (`.deps`, `.usage`, `.retry`) |
| `ModelRetry('msg')` | Raise from tool to ask model to retry |
| `UsageLimits(request_limit=N)` | Limit API calls |
| `TestModel()` | Mock model for unit tests |
| `FunctionModel(fn)` | Custom response logic for tests |
| `models.ALLOW_MODEL_REQUESTS = False` | Block real LLM calls in tests |
| `capture_run_messages()` | Capture all messages in a test block |
| `Agent.from_file('agent.yaml')` | Load agent from YAML spec |
| `MCPServerStreamableHTTP(url)` | MCP client over HTTP |
| `MCPServerStdio(cmd, args)` | MCP client over stdio subprocess |
| `load_mcp_servers('config.json')` | Load multiple MCP servers from JSON |
| `logfire.instrument_pydantic_ai()` | Enable Logfire tracing |
