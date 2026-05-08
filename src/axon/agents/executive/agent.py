"""Executive Agent — PydanticAI implementation.

Two modes:
  1. Intent Router — classifies every incoming request
  2. Crisis Decider — strategic assessment of escalated events (HITL)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic_ai import Agent, RunContext

from axon.agents.executive.prompts import (
    CRISIS_DECIDER_PROMPT,
    INTENT_ROUTER_PROMPT,
    RETRY_HINT,
)
from axon.agents.executive.schemas import (
    ExecutiveInput,
    ExecutiveOutput,
    IntentClassification,
    RiskLevel,
)
from axon.core.escalation import ActionType, StrategicAction

logger = logging.getLogger(__name__)


# =============================================================================
# Dependencies
# =============================================================================


@dataclass
class ExecutiveDeps:
    """Injected dependencies for the Executive Agent."""
    model_name:  str   = "gpt-4o"
    max_retries: int   = 3
    temperature: float = 0.1


# =============================================================================
# Lazy agent initialisation — agents created on first use to avoid
# import-time model validation failures (e.g. missing API key).
# =============================================================================

_intent_router: Agent[ExecutiveDeps, IntentClassification] | None = None
_crisis_decider: Agent[ExecutiveDeps, ExecutiveOutput] | None = None


def _get_intent_router() -> Agent[ExecutiveDeps, IntentClassification]:
    global _intent_router
    if _intent_router is None:
        _intent_router = Agent(
            model="openai:gpt-4o",
            result_type=IntentClassification,
            system_prompt=INTENT_ROUTER_PROMPT + "\n\n" + RETRY_HINT,
            retries=3,
            result_retries=2,
        )

        @_intent_router.system_prompt
        def _inject_timestamp(ctx: RunContext[ExecutiveDeps]) -> str:
            return f"Current time: {datetime.now(UTC).isoformat()}"

    return _intent_router


def _get_crisis_decider() -> Agent[ExecutiveDeps, ExecutiveOutput]:
    global _crisis_decider
    if _crisis_decider is None:
        _crisis_decider = Agent(
            model="openai:gpt-4o",
            result_type=ExecutiveOutput,
            system_prompt=RETRY_HINT,
            retries=3,
            result_retries=3,
        )
    return _crisis_decider


# =============================================================================
# Public API — Intent Router
# =============================================================================


async def classify_intent(
    user_message: str,
    deps: ExecutiveDeps | None = None,
) -> IntentClassification:
    """Classify a user message and route to the correct workflow."""
    if deps is None:
        deps = ExecutiveDeps()

    logger.info(f"Executive:IntentRouter classifying: {user_message[:80]}...")
    router = _get_intent_router()
    result = await router.run(user_message, deps=deps)

    logger.info(
        f"Executive:IntentRouter → flow={result.data.flow_name} "
        f"confidence={result.data.confidence:.2f}"
    )
    return result.data


# =============================================================================
# Public API — Crisis Decider
# =============================================================================


async def assess_crisis(
    executive_input: ExecutiveInput,
    deps: ExecutiveDeps | None = None,
) -> ExecutiveOutput:
    """Assess an escalated business-critical event and recommend actions."""
    if deps is None:
        deps = ExecutiveDeps()

    # Build escalation trail
    trail = "\n".join(
        f"  [{s.level}] {s.agent}: {s.summary}"
        for s in executive_input.escalation_history
    ) or "  (no prior escalation)"

    # Build context-rich prompt
    context = (
        f"Event type: {executive_input.event_type}\n"
        f"Severity score: {executive_input.severity_score:,.0f}\n"
        f"Financial exposure: ${executive_input.financial_exposure_usd:,.0f}\n"
        f"Affected departments: {executive_input.affected_departments}\n"
        f"Director summary: {executive_input.director_summary}\n"
        f"Decision deadline: {executive_input.decision_deadline_utc}\n"
        f"Escalation trail:\n{trail}"
    )

    logger.info(
        f"Executive:CrisisDecider assessing {executive_input.event_type} "
        f"score={executive_input.severity_score:,.0f}"
    )

    prompt = CRISIS_DECIDER_PROMPT + "\n\n## Context\n" + context + "\n\n" + RETRY_HINT

    decider = _get_crisis_decider()
    result = await decider.run(
        executive_input.model_dump_json(indent=2),
        deps=deps,
        model_settings={"temperature": deps.temperature},
        system_prompt=prompt,
    )

    assessment = result.data
    logger.info(
        f"Executive:CrisisDecider → risk={assessment.risk_level} "
        f"actions={len(assessment.recommended_actions)} "
        f"board={assessment.escalate_to_board}"
    )
    return assessment


# =============================================================================
# Mock factory for testing
# =============================================================================


def make_mock_assessment(event_type: str = "po_delay") -> ExecutiveOutput:
    """Create a mock ExecutiveOutput for testing without LLM calls."""
    return ExecutiveOutput(
        risk_level=RiskLevel.HIGH,
        rationale=(
            "Directors were unable to resolve the cross-departmental impact. "
            "The delay affects production commitments to VIP customers. "
            "Emergency procurement and production rescheduling are required."
        ),
        recommended_actions=[
            StrategicAction(
                action_type=ActionType.NOTIFY,
                target="key_customers",
                description="Notify affected customers of the delay and revised delivery schedule",
                estimated_impact="Maintains customer trust through proactive communication",
                reversible=True,
                urgency_hours=2,
                responsible_dept="sales",
            ),
            StrategicAction(
                action_type=ActionType.APPROVE,
                target="emergency_procurement_budget",
                description="Approve emergency budget for expedited shipping and overtime",
                estimated_impact="Enables immediate recovery actions",
                reversible=False,
                urgency_hours=1,
                responsible_dept="finance",
            ),
        ],
        requires_human_approval=True,
        notify_external=True,
        external_notify_list=["customer_primary_contact"],
        estimated_resolution_hours=48,
        escalate_to_board=False,
        executive_brief=(
            f"Critical {event_type} event. Recommended: customer notification + "
            "emergency budget approval. Estimated 48h resolution."
        ),
    )


# =============================================================================
# Convenience: ExecutiveAgent wrapper class
# =============================================================================


class ExecutiveAgent:
    """High-level wrapper around the Executive Agent's capabilities."""

    def __init__(self, deps: ExecutiveDeps | None = None):
        self._deps = deps or ExecutiveDeps()

    async def assess(self, event_type: str, severity_score: float, summary: str) -> ExecutiveOutput:
        """Run a full crisis assessment.

        Args:
            event_type: Type of disruption event.
            severity_score: Severity score from SeverityScorer.
            summary: Director-level summary of the situation.

        Returns:
            ExecutiveOutput with recommended actions.
        """
        inp = ExecutiveInput(
            event_type=event_type,
            severity_score=severity_score,
            director_summary=summary,
            affected_departments=["operations"],
            financial_exposure_usd=severity_score * 1.5,
            decision_deadline_utc=datetime.now(UTC).isoformat(),
        )
        return await assess_crisis(inp, deps=self._deps)

    async def route(self, message: str) -> IntentClassification:
        """Classify and route a message to the correct workflow."""
        return await classify_intent(message, deps=self._deps)
