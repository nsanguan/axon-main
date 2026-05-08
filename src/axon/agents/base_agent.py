"""Base Agent — parent class for all 10 domain agents.

Each specialized agent inherits from this and registers its domain-specific
MCP tools and system prompt.
"""

from pydantic_ai import Agent as PydanticAgent


class DomainAgent:
    """Parent agent with MCP tool-calling capability."""

    agent_id: str = "base"
    domain: str = "base"

    def __init__(self):
        self._agent: PydanticAgent | None = None

    @property
    def tools(self) -> list:
        """MCP tools assigned to this agent."""
        return []

    async def propose(self, context: dict) -> dict:
        """Generate an AgentProposal from the current planning context."""
        raise NotImplementedError
