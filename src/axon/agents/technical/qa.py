"""QA Agent (Quality Assurance) — Regulatory & SOP compliance.

Responsible for: SOP enforcement, regulatory compliance, audit readiness.
Tools: get_sop, check_compliance
"""

from __future__ import annotations

from axon.agents.base_agent import DomainAgent


class QAAgent(DomainAgent):
    agent_id = "qa"
    domain = "technical"

    system_prompt = (
        "You are the Quality Assurance agent for Axon ASCP. "
        "Your job is to verify every plan against applicable SOPs and regulatory requirements "
        "(FDA, ISO, GMP). Retrieve relevant SOPs via mcp-policy-server and check each "
        "proposed allocation for compliance violations. "
        "If a plan violates any SOP, block it with a detailed violation report. "
        "Never allow a plan to proceed with unresolved compliance issues."
    )
