"""QC Agent (Quality Control) — Inspection & rework logic.

Responsible for: inspection planning, defect tracking, rework decisions.
Tools: get_sop, check_compliance, list_wip_jobs
"""

from __future__ import annotations

from axon.agents.base_agent import DomainAgent


class QCAgent(DomainAgent):
    agent_id = "qc"
    domain = "technical"

    system_prompt = (
        "You are the Quality Control agent for Axon ASCP. "
        "Your job is to plan inspections for received materials and WIP, "
        "track defect rates by item and operation, and decide whether rework is needed. "
        "When defect rate exceeds 2%, flag the lot for 100% inspection. "
        "Coordinate with Production to schedule inspection holds on WIP jobs."
    )
