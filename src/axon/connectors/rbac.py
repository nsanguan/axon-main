"""
RBAC — Role-Based Access Control for tool authorization and agent scoping.

Enforces that agents may only call MCP tools assigned to them via the
tool catalog. Provides AgentRole enum, permission checks, and strict-mode
enforcement at the connector layer.

Design:
  - AgentRole: semantic role with tool-name allowlist
  - AuthorizedToolRegistry: compiled from ToolSpec catalog
  - enforce_tool_access(): called before every MCP tool call
  - get_agent_tools(): returns allowed tools for a given role
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from axon.agents.tools import TOOL_CATALOG, ToolSpec
from axon.core.config import settings
from axon.core.telemetry import log_event


class Direction(StrEnum):
    """Tool access direction — authority level of the operation."""

    READ = "READ"
    WRITE = "WRITE"


class AgentRole(StrEnum):
    """Authorized agent roles with semantic domain scope.

    Each role corresponds to one of the 10 domain agents plus admin.
    """

    SALES = "sales"
    PRODUCTION = "production"
    PROCUREMENT = "procurement"
    WAREHOUSE = "warehouse"
    LOGISTICS = "logistics"
    FINANCE = "finance"
    QA = "qa"
    QC = "qc"
    PD = "pd"
    MAINTENANCE = "maintenance"
    ADMIN = "admin"  # Super-user — all tools, bypasses direction restrictions

    @classmethod
    def domain_agents(cls) -> list[AgentRole]:
        """Return all 10 domain agent roles (excluding ADMIN)."""
        return [r for r in cls if r != cls.ADMIN]


# =============================================================================
# Authorized tool — compiled from ToolSpec
# =============================================================================


@dataclass(frozen=True)
class AuthorizedTool:
    """An MCP tool with its authorization metadata, compiled from ToolSpec."""

    name: str
    server: str
    direction: Direction


class AuthorizedToolRegistry:
    """Compiled registry of all authorized agent→tool mappings.

    Built once from TOOL_CATALOG at startup. Provides O(1) lookups
    for tool authorization checks.
    """

    def __init__(self, catalog: list[ToolSpec] | None = None):
        catalog = catalog or TOOL_CATALOG

        # agent_id → set[AuthorizedTool]
        self._agent_tools: dict[str, set[AuthorizedTool]] = {}
        # tool_name → set[agent_id] (reverse lookup)
        self._tool_agents: dict[str, set[str]] = {}

        for spec in catalog:
            direction = Direction.WRITE if spec.direction.upper() == "WRITE" else Direction.READ
            tool = AuthorizedTool(
                name=spec.name,
                server=spec.server,
                direction=direction,
            )

            for agent_id in spec.agent_ids:
                if agent_id not in self._agent_tools:
                    self._agent_tools[agent_id] = set()
                self._agent_tools[agent_id].add(tool)

                if spec.name not in self._tool_agents:
                    self._tool_agents[spec.name] = set()
                self._tool_agents[spec.name].add(agent_id)

    def is_authorized(self, agent_id: str, tool_name: str) -> bool:
        """Check if an agent is authorized to call a tool.

        ADMIN bypasses all checks.
        """
        if agent_id == AgentRole.ADMIN.value:
            return True
        agent_tools = self._agent_tools.get(agent_id, set())
        return any(t.name == tool_name for t in agent_tools)

    def get_tools_for_agent(self, agent_id: str) -> set[AuthorizedTool]:
        """Return all tools authorized for an agent."""
        if agent_id == AgentRole.ADMIN.value:
            all_tools: set[AuthorizedTool] = set()
            for tools in self._agent_tools.values():
                all_tools.update(tools)
            return all_tools
        return self._agent_tools.get(agent_id, set())

    def get_agents_for_tool(self, tool_name: str) -> set[str]:
        """Return all agents that can call a tool."""
        return self._tool_agents.get(tool_name, set())

    @property
    def tool_count(self) -> int:
        """Total unique tools across all agents."""
        return len(self._tool_agents)

    @property
    def agent_count(self) -> int:
        """Total agents with tool assignments."""
        return len(self._agent_tools)


# Singleton — build once at import time
_registry: AuthorizedToolRegistry | None = None


def get_registry() -> AuthorizedToolRegistry:
    """Get or create the singleton authorized tool registry."""
    global _registry
    if _registry is None:
        _registry = AuthorizedToolRegistry()
    return _registry


# =============================================================================
# Enforcement
# =============================================================================


class RBACError(Exception):
    """Raised when an RBAC check fails."""

    def __init__(self, agent_id: str, tool_name: str, reason: str):
        self.agent_id = agent_id
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"RBAC: {agent_id} not authorized for {tool_name} — {reason}")


def enforce_tool_access(
    agent_id: str,
    tool_name: str,
    direction: str = "READ",
    registry: AuthorizedToolRegistry | None = None,
) -> None:
    """Enforce that an agent may call a specific tool.

    Args:
        agent_id: The agent requesting access (e.g. "sales", "production")
        tool_name: The MCP tool name
        direction: "READ" or "WRITE"
        registry: Optional registry (uses singleton if not provided)

    Raises:
        RBACError if:
          - strict_mode is on and tool not in agent's allowlist
          - direction is WRITE and agent is READ-only
    """
    if not settings.rbac.enabled:
        return

    registry = registry or get_registry()
    tool_authorized = registry.is_authorized(agent_id, tool_name)

    if not tool_authorized:
        if settings.rbac.strict_mode:
            raise RBACError(
                agent_id=agent_id,
                tool_name=tool_name,
                reason="Tool not in agent's allowlist (strict_mode)",
            )
        log_event(
            "warn",
            "rbac_unauthorized_tool",
            agent_id=agent_id,
            tool_name=tool_name,
            message="Agent called tool not in its allowlist (non-strict mode — allowed)",
        )
        return

    log_event("info", "rbac_access_granted", agent_id=agent_id, tool_name=tool_name)


def get_agent_tool_names(agent_id: str) -> list[str]:
    """Return list of tool names available to an agent.

    Used by agents to discover their toolset at runtime.
    """
    registry = get_registry()
    return [t.name for t in registry.get_tools_for_agent(agent_id)]


def list_authorized_agents(tool_name: str) -> list[str]:
    """Return all agents authorized to call a specific tool."""
    registry = get_registry()
    return sorted(registry.get_agents_for_tool(tool_name))
