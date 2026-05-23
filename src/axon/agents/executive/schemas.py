"""Executive Agent Schemas — strict Pydantic contracts for strategic decisions.

Every input and output is type-validated. If the LLM returns invalid data,
PydanticAI retries automatically.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from axon.core.escalation import ActionType, EscalationStep, RiskLevel


class CustomerImpact(BaseModel):
    """Impact on customers from a disruption event."""

    customer_count_at_risk: int = Field(..., ge=0)
    revenue_at_risk_usd: float = Field(..., ge=0)
    delivery_delay_days: int = Field(..., ge=0)
    key_accounts_affected: list[str] = Field(default_factory=list)


class StrategicAction(BaseModel):
    """A recommended action from the Executive Agent.

    The `reversible` flag is critical — it tells the human approver
    whether the action can be undone.
    """

    action_type: ActionType
    target: str = Field(..., description="Target of action (e.g. production_line_A)")
    description: str = Field(..., min_length=10)
    estimated_impact: str = Field(..., description="Expected outcome after executing this action")
    reversible: bool = Field(..., description="True = can undo, False = permanent — caution")
    urgency_hours: int = Field(..., ge=0, description="Must execute within N hours")
    responsible_dept: str = Field(..., description="Department that must execute")


class ExecutiveInput(BaseModel):
    """Context that flows into the Executive Agent for assessment.

    Lower levels (Worker/Manager/Director) summarize and escalate
    — the Executive never sees raw data.
    """

    event_type: str = Field(..., description="Type of disruption event")
    severity_score: float = Field(..., ge=0, description="Computed by SeverityScorer")
    director_summary: str = Field(..., min_length=20, description="Summary from Director")
    affected_departments: list[str] = Field(..., min_length=1)
    financial_exposure_usd: float = Field(..., ge=0)
    customer_impact: CustomerImpact | None = None
    escalation_history: list[EscalationStep] = Field(default_factory=list)
    decision_deadline_utc: str = Field(default="", description="ISO-8601 deadline for decision")

    @field_validator("affected_departments")
    @classmethod
    def must_have_departments(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("Must have at least 1 affected department")
        return v


class ExecutiveOutput(BaseModel):
    """Structured output from the Executive Agent.

    PydanticAI will auto-retry if the LLM returns invalid data.
    `requires_human_approval` is always True at the Executive level.
    """

    risk_level: RiskLevel = Field(..., description="Overall risk level")
    rationale: str = Field(..., min_length=50, description="Reasoning behind the decision")

    recommended_actions: list[StrategicAction] = Field(
        ..., min_length=1, description="At least 1 recommended action"
    )

    requires_human_approval: bool = Field(
        default=True,
        description="Executive level always requires human approval",
    )

    notify_external: bool = Field(..., description="Must notify external stakeholders?")
    external_notify_list: list[str] = Field(
        default_factory=list,
        description="External contacts to notify",
    )

    estimated_resolution_hours: int = Field(..., ge=1, le=720)

    escalate_to_board: bool = Field(
        default=False,
        description="True = must escalate to Board of Directors",
    )
    board_escalation_reason: str = Field(
        default="",
        description="Required if escalate_to_board=True",
    )

    executive_brief: str = Field(
        ...,
        min_length=30,
        description="2-3 sentence summary for human approver",
    )

    @field_validator("board_escalation_reason")
    @classmethod
    def board_reason_required(cls, v: str, info) -> str:
        if info.data.get("escalate_to_board") and not v:
            raise ValueError("board_escalation_reason required when escalate_to_board=True")
        return v

    @field_validator("requires_human_approval")
    @classmethod
    def must_require_approval(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Executive level must requires_human_approval=True")
        return v

    @field_validator("recommended_actions")
    @classmethod
    def all_actions_must_have_reversible(cls, v: list[StrategicAction]) -> list[StrategicAction]:
        """Golden Rule #2: Action Transparency — every action must list reversible."""
        for a in v:
            if not hasattr(a, "reversible"):
                raise ValueError(f"Action '{a.description[:30]}' missing reversible field")
            if a.reversible is None:
                raise ValueError(f"Action '{a.description[:30]}' reversible cannot be None")
        return v

    @field_validator("rationale")
    @classmethod
    def rationale_min_length(cls, v: str) -> str:
        """Golden Rule #2: Rationale must be substantive for human approver."""
        if len(v.strip()) < 50:
            raise ValueError("Rationale must be at least 50 characters for audit purposes")
        return v


class IntentClassification(BaseModel):
    """Output of the Executive in Intent Router mode.

    Classifies incoming requests and routes to the correct workflow.
    """

    intent_id: str = Field(..., description="Unique intent identifier")
    flow_name: str = Field(..., description="Workflow to trigger")
    confidence: float = Field(..., ge=0.0, le=1.0)
    entities: dict = Field(default_factory=dict, description="Extracted entities")
    priority: str = Field(default="normal", pattern="^(urgent|normal|low)$")
    fallback: bool = Field(default=False, description="True = unknown intent, use default")
