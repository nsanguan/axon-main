"""Base Agent — parent class for all 10 domain agents.

Each specialized agent inherits from this and registers its domain-specific
MCP tools and system prompt.  The base class provides the full propose()
implementation via PydanticAI — subclasses only need to set agent_id,
domain, and system_prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent as PydanticAgent

from axon.core.schema import AgentProposal, ProposalStatus
from axon.core.telemetry import log_event

# =============================================================================
# Structured result the LLM must return
# =============================================================================


class ProposalResult(BaseModel):
    """Structured output every domain agent must return for each planning cycle."""

    model_config = ConfigDict(extra="ignore")

    utility_score: float = Field(
        ge=0.0,
        le=1.0,
        description="How well this proposal satisfies domain requirements (0=worst, 1=best).",
    )
    justification: str = Field(
        min_length=10,
        max_length=1000,
        description="Concise reasoning for the utility score and proposed allocations.",
    )
    allocation_summaries: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Each entry: {demand_id, supply_id, quantity, item_name, status}. "
            "Leave empty if no specific allocations can be determined."
        ),
    )
    constraints_flagged: list[str] = Field(
        default_factory=list,
        description="Supply/demand constraints or compliance risks identified during analysis.",
    )


# =============================================================================
# Runtime dependencies injected into the PydanticAI agent
# =============================================================================


@dataclass
class AgentDeps:
    """Runtime dependencies injected into a PydanticAI domain agent."""

    agent_id: str
    correlation_id: str = ""
    connectors: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# DomainAgent base class
# =============================================================================


class DomainAgent:
    """Parent agent with MCP tool-calling capability via PydanticAI.

    Subclasses set class-level attributes:
        agent_id:      unique identifier, e.g. "sales"
        domain:        group name, e.g. "commercial"
        system_prompt: domain expertise injected as the LLM system prompt

    The base class provides a complete propose() implementation.
    Subclasses that need custom behaviour can override propose() but should
    call super().propose(context) for the LLM reasoning step.
    """

    agent_id: str = "base"
    domain: str = "base"
    system_prompt: str = "You are a domain expert in supply chain planning."

    def __init__(self, connectors: dict[str, Any] | None = None) -> None:
        self._connectors: dict[str, Any] = connectors or {}
        self._pydantic_agent: PydanticAgent[AgentDeps, ProposalResult] | None = None

    @property
    def tools(self) -> list[Any]:
        """MCP tools assigned to this agent (PydanticAI Tool objects)."""
        return []

    # =========================================================================
    # Internal helpers
    # =========================================================================

    def _resolve_model(self) -> str:
        """Return the pydantic-ai model string from settings."""
        try:
            from axon.core.config import settings

            model = str(settings.llm.model)
        except Exception:
            model = "claude-3-5-sonnet-20241022"

        if ":" not in model:
            if "claude" in model:
                return f"anthropic:{model}"
            if "gpt" in model or "o1" in model or "o3" in model:
                return f"openai:{model}"
            if "gemini" in model:
                return f"google-gla:{model}"
        return model

    def _build_agent(self) -> PydanticAgent[AgentDeps, ProposalResult]:
        """Lazy-initialize the PydanticAI agent with domain MCP tools."""
        from axon.agents.tools import build_pydantic_tools  # avoid circular at module top

        mcp_tools = build_pydantic_tools(self.agent_id, self._connectors)
        return PydanticAgent(
            model=self._resolve_model(),
            result_type=ProposalResult,
            system_prompt=self.system_prompt,
            deps_type=AgentDeps,
            tools=mcp_tools,
            retries=2,
            result_retries=2,
        )

    def _build_prompt(self, context: dict[str, Any]) -> str:
        """Build a planning context prompt string from the state dict."""
        demands: list[dict[str, Any]] = context.get("demands", [])
        supplies: list[dict[str, Any]] = context.get("supplies", [])
        past_insights: list[dict[str, Any]] = context.get("past_insights", [])
        correlation_id: str = context.get("correlation_id", "unknown")

        lines: list[str] = [
            f"=== Planning Cycle: {correlation_id} ===",
            f"Active demands ({len(demands)} items):",
        ]
        for d in demands[:10]:
            item = d.get("item") or {}
            if isinstance(item, dict):
                item_id = item.get("native_id", "unknown")
            else:
                item_id = str(item)
            lines.append(
                f"  • {item_id}  qty={d.get('quantity', 0)}"
                f"  priority={d.get('priority', 0)}"
                f"  source={d.get('source', '?')}"
            )

        lines.append(f"Supply positions ({len(supplies)} items):")
        for s in supplies[:5]:
            item = s.get("item") or {}
            if isinstance(item, dict):
                item_id = item.get("native_id", "unknown")
            else:
                item_id = str(item)
            lines.append(
                f"  • {item_id}  qty={s.get('quantity', 0)}  source={s.get('source', '?')}"
            )

        if past_insights:
            lines.append(f"[{len(past_insights)} similar past plans available for reference]")

        lines.append(
            "\nAnalyse the above from your domain perspective. "
            "Call your MCP tools to gather any additional data you need. "
            "Return a utility_score (0.0–1.0), a clear justification, "
            "allocation_summaries if you can determine them, "
            "and flag any constraints or risks."
        )
        return "\n".join(lines)

    # =========================================================================
    # Public API
    # =========================================================================

    async def propose(self, context: dict[str, Any]) -> dict[str, Any]:
        """Generate an AgentProposal from the current planning context.

        Calls the PydanticAI agent, which may invoke MCP tools, then wraps
        the result in an AgentProposal.  On failure returns a minimal
        best-effort proposal so the orchestrator can continue.

        Args:
            context: The current PlanningState as a plain dict.

        Returns:
            AgentProposal serialised to a plain dict (model_dump mode="json").
        """
        if self._pydantic_agent is None:
            self._pydantic_agent = self._build_agent()

        correlation_id: str = context.get("correlation_id", str(uuid4()))
        user_prompt = self._build_prompt(context)
        deps = AgentDeps(
            agent_id=self.agent_id,
            correlation_id=correlation_id,
            connectors=self._connectors,
        )

        try:
            log_event(
                "info",
                "agent_reasoning_start",
                agent_id=self.agent_id,
                correlation_id=correlation_id,
            )
            result = await self._pydantic_agent.run(user_prompt, deps=deps)
            data: ProposalResult = result.data
            log_event(
                "info",
                "agent_reasoning_done",
                agent_id=self.agent_id,
                utility_score=data.utility_score,
            )
        except Exception as exc:
            log_event(
                "warn",
                "agent_reasoning_failed",
                agent_id=self.agent_id,
                error=str(exc),
            )
            data = ProposalResult(
                utility_score=0.25,
                justification=(
                    f"Agent {self.agent_id} reasoning failed: {exc!s}. "
                    "Returning best-effort fallback."
                ),
            )

        proposal = AgentProposal(
            agent_id=self.agent_id,
            round_number=context.get("round_number", 1),
            allocations=[],
            utility_score=data.utility_score,
            justification=data.justification,
            status=ProposalStatus.PROPOSED,
            amendments=data.constraints_flagged,
        )
        return proposal.model_dump(mode="json")
