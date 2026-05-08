"""Sales Agent — Demand forecasting & ATP (Available to Promise).

Responsible for: customer demand analysis, ATP checks, sales order prioritization.
Tools: get_available_to_promise, get_inventory_levels, get_sales_orders, get_demand_forecast, get_shipments
"""

from __future__ import annotations

from axon.agents.base_agent import DomainAgent


class SalesAgent(DomainAgent):
    agent_id = "sales"
    domain = "commercial"

    system_prompt = (
        "You are the Sales planning agent for Axon ASCP. "
        "Your job is to analyze customer demand, verify ATP (Available to Promise), "
        "and prioritize sales orders based on customer importance, order value, and deadlines. "
        "When proposing allocations, always consider customer priority (VIP=90+) first, "
        "then order value, then deadline proximity. "
        "If supply is insufficient, clearly state the shortage and recommend alternatives."
    )
