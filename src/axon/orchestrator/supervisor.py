"""Supervisor Node — routes between specialist agents in the planning cycle.

Implements the hierarchy from Escalate_Tech spec:
  Worker (sensors) → Manager (specialists) → Director (coordinator) → Executive

Pattern:
  Supervisor = collection of conditional edges.
  Uses Command(goto=..., update=...) for atomic route + state update.
  Safety: MAX_SUPERVISOR_ROUNDS = 6 prevents infinite loops.

Anti-pattern — No "Mesh Coupling":
  Agents NEVER call each other directly. All coordination is mediated
  through the Supervisor (hub-and-spoke model).
  See: docs/escalation-architecture.md

Node Function → Subgraph Transition:
  When an agent's internal logic exceeds 3 steps
  (fetch → validate → analyze → summarize), upgrade it to a subgraph
  without modifying the parent flow. This is seamless — the parent
  flow calls the same node name regardless of whether it's a function
  or a compiled subgraph.

Agents routed by the supervisor:
  - commercial (sales, procurement, finance)  → port 8101
  - operations (production, logistics, warehouse) → port 8102
  - technical (qa, qc, maintenance, pd) → port 8103
"""

from __future__ import annotations

from typing import Any, Literal

from axon.core.telemetry import log_event

MAX_SUPERVISOR_ROUNDS = 6


def classify_agents_needed(state: dict[str, Any]) -> list[str]:
    """Determine which agents should be consulted based on the state.

    Analyzes the planning context to decide which agent groups are needed.
    Returns list of agent IDs in priority order.
    """
    agents: list[str] = []
    demands = state.get("demands", []) or state.get("raw_demands", [])
    supplies = state.get("supplies", []) or state.get("raw_supplies", [])

    # If there are demands, sales agent is needed
    if demands:
        agents.append("commercial")

    # If there are supply constraints, operations agent is needed
    if (supplies or state.get("deadlock", False)) and "operations" not in agents:
        agents.append("operations")

    # If quality or compliance flags exist, technical agent is needed
    policies = state.get("raw_policies", [])
    if policies:
        agents.append("technical")

    # If VIP demands exist, prioritise commercial
    if any(d.get("priority", 0) > 80 for d in demands):
        agents = sorted(agents, key=lambda x: 0 if x == "commercial" else 1)

    return agents or ["commercial"]


def supervisor_dispatch(
    state: dict[str, Any],
    round_number: int,
) -> tuple[
    Literal["agent_commercial", "agent_operations", "agent_technical", "response_node", "__end__"],
    dict[str, Any],
]:
    """Supervisor routing logic.

    Analyzes current state and decides which agent to call next,
    or if the planning cycle has enough information to proceed.

    Args:
        state: Current planning state.
        round_number: Which supervisor round this is.

    Returns:
        Tuple of (next_node, update_dict)
    """
    # Safety ceiling — prevent infinite loops
    if round_number >= MAX_SUPERVISOR_ROUNDS:
        log_event("warn", "supervisor_max_rounds", rounds=round_number)
        return "response_node", {"supervisor_done": True}

    # Determine which agents are still needed
    needed = classify_agents_needed(state)
    consulted = state.get("_supervisor_consulted", [])

    # Find the first needed agent that hasn't been consulted yet
    for agent_type in needed:
        if agent_type not in consulted:
            agent_map = {
                "commercial": "agent_commercial",
                "operations": "agent_operations",
                "technical": "agent_technical",
            }
            target = agent_map[agent_type]

            log_event(
                "info",
                "supervisor_dispatch",
                agent=target,
                round=round_number,
                needed=needed,
            )

            return target, {
                "_supervisor_consulted": consulted + [agent_type],
                "_supervisor_round": round_number + 1,
                "_supervisor_history": state.get("_supervisor_history", [])
                + [{"round": round_number, "agent": target}],
            }

    # All needed agents consulted — done
    log_event("info", "supervisor_done", rounds=round_number, agents=consulted)
    return "response_node", {"supervisor_done": True}


async def supervisor_node(state: dict[str, Any]) -> dict[str, Any]:
    """Supervisor LangGraph node.

    Reads current state, decides next agent to call, injects the agent's
    context into the state, and routes via conditional edge.

    This is designed to be called from a LangGraph conditional edge.
    """
    round_number = state.get("_supervisor_round", 0)
    log_event("info", "supervisor_enter", round=round_number)

    target, updates = supervisor_dispatch(state, round_number)
    state.update(updates)

    return {
        "_supervisor_target": target,
        "_supervisor_round": round_number + 1,
    }


def route_after_supervisor(state: dict[str, Any]) -> str:
    """Conditional edge after supervisor node.

    Returns the next node name based on supervisor's dispatch decision.
    """
    return state.get("_supervisor_target", "response_node")
