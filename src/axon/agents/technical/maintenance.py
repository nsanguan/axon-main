"""Maintenance Agent — Predictive downtime & asset health.

Responsible for: asset health monitoring, maintenance scheduling, capacity impact.
Tools: list_wip_jobs, get_sop, update_work_center_status
"""

from __future__ import annotations

from axon.agents.base_agent import DomainAgent


class MaintenanceAgent(DomainAgent):
    agent_id = "maintenance"
    domain = "technical"

    system_prompt = (
        "You are the Maintenance agent for Axon ASCP. "
        "Your job is to monitor asset health scores, predict downtime events, "
        "and schedule preventive maintenance to minimize production impact. "
        "When an asset health score drops below 60%, flag it for maintenance "
        "and coordinate with Production to reschedule affected WIP jobs. "
        "Update work center status (available/maintenance/down) as conditions change."
    )
