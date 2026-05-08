"""
mcp_servers.odoo.qa — Axon FastMCP server for Quality Assurance (SSE transport).

Acts as the compliance guardrail for all inter-departmental actions.
Implement tools via Odoo XML-RPC against:
  quality.alert, quality.check, quality.point (Odoo Quality module)

Inter-departmental data flow:
  QA ↔ Every Dept: evaluates proposed actions before ERP writes
  If violation_found → LangGraph interrupt (human compliance review)

Tools:
  axon_get_compliance_rules      — list active compliance rules
  axon_check_compliance          — evaluate a proposed action against rules
  axon_flag_violation            — record a compliance violation in the ERP
  axon_request_compliance_review — create HITL activity for human compliance review
  axon_get_quality_alerts        — list open quality alerts
  axon_post_comment              — post AI reasoning to Chatter
  axon_check_activity_done       — poll activity completion
"""

from __future__ import annotations

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "axon-qa",
    instructions=(
        "Quality Assurance adapter for Axon. "
        "Acts as the compliance guardrail — evaluates proposed actions against "
        "plant regulations and standards before any ERP write is committed."
    ),
)


# ── Input models ──────────────────────────────────────────────────────────────

class GetComplianceRulesInput(BaseModel):
    department: str | None = Field(
        None,
        description="Filter by department ('procurement', 'production', 'logistics', 'all')",
    )
    severity: str | None = Field(
        None, description="Filter by severity: 'minor' | 'major' | 'critical'"
    )
    active_only: bool = Field(True, description="Only return active rules")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class CheckComplianceInput(BaseModel):
    action_type: str = Field(
        description="Type of action to evaluate: 'confirm_po' | 'release_production' | 'ship_goods' | 'lock_stock' | 'create_rework'"
    )
    action_description: str = Field(
        description="Plain-language description of the proposed action"
    )
    entity_type: str = Field(
        description="ERP entity involved (e.g. 'purchase.order', 'mrp.production')"
    )
    entity_id: str = Field(description="ERP entity ID or reference")
    department: str = Field(
        description="Department initiating the action"
    )
    ai_context: str = Field(
        description="Agent reasoning for why this action is being proposed"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class FlagViolationInput(BaseModel):
    rule_code: str = Field(description="Compliance rule code that was violated")
    violation_description: str = Field(
        description="Detailed description of what was violated and how"
    )
    entity_type: str = Field(description="ERP entity type (e.g. 'purchase.order')")
    entity_id: str = Field(description="ERP entity ID")
    severity: str = Field(
        description="Violation severity: 'minor' | 'major' | 'critical'"
    )
    ai_context: str = Field(
        description="QA Agent reasoning for flagging this violation"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class RequestComplianceReviewInput(BaseModel):
    entity_type: str = Field(description="ERP entity type requiring review")
    entity_id: int = Field(description="ERP entity record ID")
    violations_summary: str = Field(
        description="Summary of violations requiring human review"
    )
    deadline_days: int = Field(
        1, description="Days until the compliance review must be completed"
    )
    ai_context: str = Field(
        description="QA Agent reasoning for why human review is required"
    )
    cycle_id: str | None = Field(None, description="Planning cycle reference")


class GetQualityAlertsInput(BaseModel):
    product_id: int | None = Field(
        None, description="Filter by product.product ID"
    )
    stage_filter: list[str] | None = Field(
        None, description="Filter by alert stage names"
    )
    limit: int = Field(50, description="Maximum records to return")
    ai_context: str = Field(description="Reason why the agent is calling this tool")


class QAPostCommentInput(BaseModel):
    model: str = Field(description="Odoo model name (e.g. 'quality.alert')")
    record_id: int = Field(description="Record ID to post the comment on")
    message: str = Field(description="AI reasoning message to post to Chatter")
    ai_context: str = Field(description="Reason why the agent is posting this comment")


class QACheckActivityInput(BaseModel):
    activity_id: int = Field(description="mail.activity ID to poll")
    ai_context: str = Field(description="Reason why the agent is checking this activity")


# ── Tool definitions ──────────────────────────────────────────────────────────

@mcp.tool()
def axon_get_compliance_rules(params: GetComplianceRulesInput) -> list[dict]:
    """
    List active compliance rules from the ERP.
    Returns AxonComplianceRule-compatible dicts.

    Implement via: quality.point (check points) + custom compliance rule model.
    """
    raise NotImplementedError(
        "axon_get_compliance_rules: implement in Phase 6 using AxonQASkills"
    )


@mcp.tool()
def axon_check_compliance(params: CheckComplianceInput) -> dict:
    """
    Evaluate a proposed action against all applicable compliance rules.
    Returns AxonComplianceDecision-compatible dict.

    Triggered before every ERP write operation by the orchestrator.
    If outcome='violation_found' and requires_human_review=True,
    the orchestrator fires a LangGraph interrupt checkpoint.

    Implement via: quality.point evaluation + custom rule engine.
    """
    raise NotImplementedError(
        "axon_check_compliance: implement in Phase 6 using AxonQASkills"
    )


@mcp.tool()
def axon_flag_violation(params: FlagViolationInput) -> dict:
    """
    Record a compliance violation in the ERP (creates quality.alert).
    Returns the created quality.alert ID and audit reference.

    Implement via: quality.alert create().
    """
    raise NotImplementedError(
        "axon_flag_violation: implement in Phase 6 using AxonQASkills"
    )


@mcp.tool()
def axon_request_compliance_review(params: RequestComplianceReviewInput) -> dict:
    """
    Create a HITL mail.activity for human compliance sign-off.
    Returns the activity ID that the orchestrator will use as interrupt trigger.

    Implement via: mail.activity create() on the flagged entity.
    """
    raise NotImplementedError(
        "axon_request_compliance_review: implement in Phase 6 using AxonQASkills"
    )


@mcp.tool()
def axon_get_quality_alerts(params: GetQualityAlertsInput) -> list[dict]:
    """
    List open quality alerts from the ERP.
    Returns quality.alert records in AxonComplianceViolation-compatible format.

    Implement via: quality.alert search_read().
    """
    raise NotImplementedError(
        "axon_get_quality_alerts: implement in Phase 6 using AxonQASkills"
    )


@mcp.tool()
def axon_post_comment(params: QAPostCommentInput) -> dict:
    """Post AI reasoning to any ERP record's Chatter for audit trail."""
    raise NotImplementedError(
        "axon_post_comment: implement in Phase 6 using AxonCommunicationSkills"
    )


@mcp.tool()
def axon_check_activity_done(params: QACheckActivityInput) -> dict:
    """Poll whether a compliance review mail.activity has been marked Done."""
    raise NotImplementedError(
        "axon_check_activity_done: implement in Phase 6 using AxonCommunicationSkills"
    )


if __name__ == "__main__":
    import uvicorn
    from core.config import settings
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=settings.mcp_qa_port)
