"""
agents — Axon ASCP agent registry.
"""

from __future__ import annotations

from agents.executive import (
    AxonExecutiveDirective,
    AxonExecutiveSummary,
    get_axon_executive_entry_agent,
    get_axon_executive_agent,
)
from agents.supervisor import supervisor_route
from agents.planning import (
    AxonAllocationUpdate,
    AxonPlanningDecision,
    AxonShortageItem,
    get_axon_planning_agent,
)
from agents.purchase.buyer import (
    AxonBuyerDecision,
    AxonProposedLine,
    get_axon_buyer_agent,
)
from agents.purchase.manager import (
    AxonLineAnalysis,
    AxonManagerAnalysis,
    get_axon_purchase_manager_agent,
)
from agents.purchase.director import (
    AxonDirectorDecision,
    get_axon_purchase_director_agent,
)

__all__ = [
    "AxonExecutiveDirective",
    "AxonExecutiveSummary",
    "get_axon_executive_entry_agent",
    "get_axon_executive_agent",
    "supervisor_route",
    "AxonAllocationUpdate",
    "AxonPlanningDecision",
    "AxonShortageItem",
    "get_axon_planning_agent",
    "AxonBuyerDecision",
    "AxonProposedLine",
    "get_axon_buyer_agent",
    "AxonLineAnalysis",
    "AxonManagerAnalysis",
    "get_axon_purchase_manager_agent",
    "AxonDirectorDecision",
    "get_axon_purchase_director_agent",
]
