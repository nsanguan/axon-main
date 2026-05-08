"""Production Agent — MPS & finite capacity scheduling.

Responsible for: master production scheduling, capacity planning, WIP management.
Tools: list_wip_jobs, get_inventory_levels, get_bom, get_work_center_capacity, reschedule_wip_job
"""

from __future__ import annotations

from axon.agents.base_agent import DomainAgent


class ProductionAgent(DomainAgent):
    agent_id = "production"
    domain = "operations"

    system_prompt = (
        "You are the Production planning agent for Axon ASCP. "
        "Your job is to create and maintain the Master Production Schedule (MPS), "
        "manage finite capacity across work centers, and prioritize WIP jobs. "
        "When capacity is constrained, negotiate with Maintenance for uptime "
        "and with Procurement for material availability. "
        "Always verify BOM completeness before scheduling production. "
        "Reschedule WIP jobs only when capacity or material constraints demand it."
    )
