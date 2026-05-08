"""Finance Agent — ROI, costing & budget alignment.

Responsible for: cost analysis, budget tracking, profitability assessment.
Tools: get_item_costs
"""

from __future__ import annotations

from axon.agents.base_agent import DomainAgent


class FinanceAgent(DomainAgent):
    agent_id = "finance"
    domain = "commercial"

    system_prompt = (
        "You are the Finance agent for Axon ASCP. "
        "Your job is to evaluate plan costs against budgets, "
        "calculate ROI for procurement decisions, and flag any allocation "
        "that exceeds budget thresholds. "
        "When costs exceed standard, recommend alternative suppliers or defer non-critical demand. "
        "Track COGS impact across all planning decisions."
    )
