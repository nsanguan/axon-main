"""Procurement Agent — Automated sourcing & supplier sync.

Responsible for: supplier selection, purchase order management, material sourcing.
Tools: get_suppliers, get_item_costs, get_purchase_orders, create_purchase_requisition
"""

from __future__ import annotations

from axon.agents.base_agent import DomainAgent


class ProcurementAgent(DomainAgent):
    agent_id = "procurement"
    domain = "commercial"

    system_prompt = (
        "You are the Procurement agent for Axon ASCP. "
        "Your job is to source materials and components from approved suppliers, "
        "evaluate supplier reliability (on-time %, quality score), "
        "and create purchase requisitions when inventory drops below safety stock. "
        "Always prefer suppliers with reliability > 0.85 and lowest total cost "
        "(price + lead time cost). Flag any supplier with reliability < 0.70 for review."
    )
