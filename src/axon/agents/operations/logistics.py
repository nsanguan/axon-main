"""Logistics Agent — Route & distribution planning.

Responsible for: shipment scheduling, carrier selection, transit optimization.
Tools: get_shipments, get_carrier_rates, get_transit_times
"""

from __future__ import annotations

from axon.agents.base_agent import DomainAgent


class LogisticsAgent(DomainAgent):
    agent_id = "logistics"
    domain = "operations"

    system_prompt = (
        "You are the Logistics agent for Axon ASCP. "
        "Your job is to plan shipments, select carriers based on rates and transit times, "
        "and ensure on-time delivery to customers. "
        "When a shipment is delayed, notify Sales and propose alternative routing. "
        "Optimize carrier selection for cost vs. delivery speed based on order priority."
    )
