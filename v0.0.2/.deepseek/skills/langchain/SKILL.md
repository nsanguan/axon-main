---
name: langchain
description: Core LLM application framework with runnables, prompt templates, chat models, and output parsers. Use for single-turn LLM calls, prompt construction, structured output parsing, and LCEL (LangChain Expression Language) chains. For multi-step agent orchestration, prefer the langgraph skill.
---

# LangChain

## Quick start

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a supply chain planner."),
    ("human", "Plan production for {product} in {quarter}"),
])
model = ChatOpenAI(model="gpt-4o")
chain = prompt | model | StrOutputParser()

result = chain.invoke({"product": "Widget-A", "quarter": "Q3"})
```

## Core abstractions

### Runnable interface

All LangChain components implement `Runnable`:

```python
runnable.invoke(input)        # Single call
runnable.batch([a, b, c])     # Parallel batch
async for chunk in runnable.astream(input):  # Streaming
    ...
```

### LCEL (LangChain Expression Language)

Chain components with `|` (pipe):

```python
chain = prompt | model | output_parser
chain = RunnableParallel({"summary": chain1, "detail": chain2})
chain = RunnablePassthrough.assign(extra=lambda x: compute(x))
```

### Chat models

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

model = ChatOpenAI(model="gpt-4o", temperature=0)
model = ChatAnthropic(model="claude-3-5-sonnet-20241022")
```

### Tool calling with LangChain

```python
from langchain_core.tools import tool

@tool
def get_inventory(item_id: str) -> int:
    """Return current inventory for an item."""
    return 42

llm_with_tools = model.bind_tools([get_inventory])
result = llm_with_tools.invoke("Check inventory for item X")
# result.tool_calls contains the parsed tool call
```

### Output parsers

```python
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

class Plan(BaseModel):
    steps: list[str]
    deadline: str

parser = PydanticOutputParser(pydantic_object=Plan)
chain = prompt | model | parser
```

### Prompt templates

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

prompt = ChatPromptTemplate.from_messages([
    ("system", "{system_prompt}"),
    MessagesPlaceholder("history"),
    ("human", "{input}"),
])
```

## When to use LangChain vs LangGraph

| Use Case | Framework |
|----------|-----------|
| Single LLM call with parsing | LangChain LCEL |
| Sequential tool calling | LangChain |
| Multi-step agent loop | LangGraph |
| Parallel agent negotiation | LangGraph |
| Human-in-the-loop approval | LangGraph |
| Persistent state across turns | LangGraph |

Rule of thumb: if you need a loop, branching, or persistence, use LangGraph.

## Message format

```python
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

messages = [
    SystemMessage("You are helpful."),
    HumanMessage("Hello"),
    AIMessage("Hi!"),
    HumanMessage("What is 2+2?"),
]
```

## Common pitfalls

- **LCEL functions must be serializable**: Don't use lambdas with closures over external state. Use `RunnableLambda` with a named function instead.
- **Tool binding vs. tool calling**: `bind_tools()` enables the model to request tool calls but doesn't execute them. Use `ToolNode` in LangGraph for execution.
- **Output parser errors**: When the model produces malformed JSON, `PydanticOutputParser` raises. Wrap with `OutputFixingParser` or use `result_type` in PydanticAI instead.

## References

- For graph-based orchestrators, see the `langgraph` skill.
- For type-safe agents with structured results, see the `pydantic-ai` skill.
