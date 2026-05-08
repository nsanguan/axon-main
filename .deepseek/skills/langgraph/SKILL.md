---
name: langgraph
description: Build stateful, multi-actor agent workflows with LangGraph. Use when building agent orchestrators, multi-step reasoning pipelines, negotiation loops, or any workflow requiring graph-based state management with checkpointing, conditional routing, and human-in-the-loop approval nodes. Covers StateGraph, nodes/edges, ToolNode, sub-graphs, and Postgres/SQLite checkpointer backends.
---

# LangGraph

## Quick start

```python
from langgraph.graph import StateGraph, END
from typing import Annotated, TypedDict
from langgraph.checkpoint.postgres import PostgresSaver

class State(TypedDict):
    messages: list
    next_step: str

graph = StateGraph(State)

def node_a(state: State) -> dict:
    return {"next_step": "b"}

graph.add_node("a", node_a)
graph.set_entry_point("a")

def route(state: State) -> str:
    return state["next_step"] if state["next_step"] != "done" else END

graph.add_conditional_edges("a", route)
compiled = graph.compile(checkpointer=PostgresSaver.from_conn_string(...))
```

## Patterns

### StateGraph construction

Always define State as a TypedDict (or Pydantic model). Use `Annotated[type, reducer]` for fields that merge across parallel branches (`operator.add` is the default list reducer for messages).

**Reducers**: `operator.add` appends (messages); custom reducers for overwrite, merge, or combine.

### Nodes

A node is `(state: State) -> dict[str, Any]` — only return the fields that changed. The graph merges the returned dict into state.

### Edges

- **Normal**: `graph.add_edge("a", "b")` — unconditional
- **Conditional**: `graph.add_conditional_edges("a", route_fn)` — `route_fn` returns node name or `END`
- **Parallel**: multiple edges from one node → nodes execute concurrently

### Tool calling

```python
from langgraph.prebuilt import ToolNode

tools = [tool1, tool2]
graph.add_node("tools", ToolNode(tools))

def should_call_tools(state: State) -> str:
    last = state["messages"][-1]
    return "tools" if last.tool_calls else END
```

### Human-in-the-Loop

Use `interrupt()` to pause execution before critical actions:

```python
graph.add_node("approval", interrupt)
graph.add_edge("approval", "execute")

# Resume after human review:
compiled.invoke(Command(resume={"approved": True}), config)
```

### Checkpointing

- **Postgres**: `PostgresSaver.from_conn_string("postgresql://...")`
- **SQLite**: `SqliteSaver.from_conn_string("sqlite:///checkpoints.db")`
- **Memory**: `MemorySaver()` (dev only, lost on restart)

### Sub-graphs

```python
subgraph = sub_builder.compile()
graph.add_node("sub", subgraph)
```

Parent state keys are passed to the child; child returns a dict merged into parent.

## Common pitfalls

- **State mutation**: never mutate state in a node. Return a new dict with only changed fields.
- **Missing END**: every conditional edge must route to `END` for at least one branch, or the graph runs forever.
- **Parallel node writes**: two parallel nodes writing the same key — use a reducer or guarantee disjoint keys.

## References

- For LangChain primitives used inside nodes, see the `langchain` skill.
- For agent tool definitions, see the `pydantic-ai` skill.
