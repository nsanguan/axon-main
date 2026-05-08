"""Warehouse Agent — Safety stock & inventory optimization.

Responsible for: inventory levels, safety stock targets, storage capacity.
Tools: get_inventory_levels, get_shipments
"""

from __future__ import annotations

from axon.agents.base_agent import DomainAgent


class WarehouseAgent(DomainAgent):
    agent_id = "warehouse"
    domain = "operations"

    system_prompt = (
        "You are the Warehouse agent for Axon ASCP. "
        "Your job is to monitor inventory levels across all locations, "
        "maintain safety stock targets, and optimize storage utilization. "
        "When inventory drops below safety stock, alert Procurement immediately. "
        "When storage capacity exceeds 85%, recommend inventory redistribution or expedited shipments."
    )
