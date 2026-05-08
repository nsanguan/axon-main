"""
agents.qa.compliance_guardrail — QA Compliance Guardrail Agent.

Acts as the cross-departmental compliance gate. Evaluates any proposed ERP
write action against active compliance rules before the action is committed.

If a violation is found that requires human review, the orchestrator fires a
LangGraph interrupt checkpoint (langgraph.types.interrupt).

ERP-agnostic: all ERP calls go through MCP tools.
"""

from __future__ import annotations

from pydantic_ai import Agent

from adapters.mcp_client import AxonAdapterRegistry
from core.config import settings
from core.model_factory import build_model
from core.schema.quality import AxonComplianceDecision

QA_GUARDRAIL_SYSTEM_PROMPT = """
You are the QA Compliance Guardrail Agent for Axon.

You are called BEFORE every ERP write operation as a gate.

Your role:
- Call axon_get_compliance_rules to retrieve the applicable rules for the
  department and action type.
- Call axon_check_compliance with the proposed action details.
- Evaluate the AxonComplianceDecision:
    * compliant        → return decision, orchestrator proceeds with the write
    * violation_found  → call axon_flag_violation to record it in the ERP
                         if requires_human_review: call axon_request_compliance_review
                         return decision with requires_human_review=True so the
                         orchestrator fires langgraph.types.interrupt
    * needs_human_review → same as violation_found
- Always post the compliance reasoning to the entity Chatter via axon_post_comment.

Rules:
- Never override a 'critical' severity violation — always set
  recommendation='block_and_escalate' and requires_human_review=True.
- Use ai_context on every tool call to document your reasoning.
- You are a guardrail — do not approve actions you cannot verify.
"""

_agent: "Agent[None, AxonComplianceDecision] | None" = None


def get_axon_qa_agent() -> "Agent[None, AxonComplianceDecision]":
    global _agent
    if _agent is None:
        registry = AxonAdapterRegistry()
        _agent = Agent(
            build_model(settings.llm_quality_model),
            output_type=AxonComplianceDecision,
            system_prompt=QA_GUARDRAIL_SYSTEM_PROMPT,
            toolsets=registry.qa_servers(),
        )
    return _agent
