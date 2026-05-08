"""
agents.finance.budget_validator — Budget Validation Agent.

Evaluates whether a proposed supply chain action (PO confirmation, production
launch, logistics booking) is within the approved budget.

If the budget is exceeded and CFO review is required, the orchestrator fires a
LangGraph interrupt checkpoint.

ERP-agnostic: all ERP calls go through MCP tools.
"""

from __future__ import annotations

from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model
from core.schema.finance import AxonBudgetValidation

BUDGET_VALIDATOR_SYSTEM_PROMPT = """
You are the Budget Validation Agent for Axon.

You are called before any significant ERP write (confirm PO, launch MO, book carrier)
to verify budget compliance.

Your role:
- Call axon_get_budget_status to read current budget utilisation.
- Call axon_validate_budget with the proposed action and cost.
- Evaluate the AxonBudgetValidation outcome:
    * approved              → return validation, orchestrator proceeds
    * warning               → post a Chatter warning and return
    * rejected              → post Chatter rejection note, return with
                              recommendation='reject'
    * needs_cfo_review      → call axon_create_activity for CFO review
                              return with requires_cfo_review=True so the
                              orchestrator fires langgraph.types.interrupt
- Always post the budget analysis to the entity record via axon_post_comment.

Rules:
- Never approve an action that exceeds the budget by > 20 % without CFO review.
- Use ai_context on every tool call to document your reasoning.
"""

_agent: "Agent[None, AxonBudgetValidation] | None" = None


def get_axon_budget_validator_agent() -> "Agent[None, AxonBudgetValidation]":
    global _agent
    if _agent is None:
        registry = AxonAdapterRegistry()
        _agent = Agent(
            build_model(settings.llm_finance_model),
            output_type=AxonBudgetValidation,
            system_prompt=BUDGET_VALIDATOR_SYSTEM_PROMPT,
            toolsets=registry.finance_servers(),
        )
    return _agent
