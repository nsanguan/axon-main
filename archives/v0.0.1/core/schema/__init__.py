"""
core.schema — Axon Universal Data Schema.

This package defines the ERP-agnostic data models that all agents and the
orchestrator use. These are the "universal language" of Axon.

Agents ONLY speak these schemas. MCP adapters translate ERP-native records
into these models before they reach the reasoning layer.

Modules
-------
demand      AxonDemandItem, AxonDemandStream, AxonDemandSource, AxonDemandStatus
supply      AxonSupplyItem, AxonSupplyStream, AxonSupplySource, AxonSupplyStatus
allocation  AxonAllocation, AxonShortageItem, AxonPlanningDecision, AxonAllocationStatus, AxonAllocationAction
"""

from core.schema.demand import (
    AxonDemandItem,
    AxonDemandSource,
    AxonDemandStatus,
    AxonDemandStream,
)
from core.schema.supply import (
    AxonSupplyItem,
    AxonSupplySource,
    AxonSupplyStatus,
    AxonSupplyStream,
)
from core.schema.allocation import (
    AxonAllocation,
    AxonAllocationAction,
    AxonAllocationStatus,
    AxonPlanningDecision,
    AxonShortageItem,
)

__all__ = [
    "AxonDemandItem",
    "AxonDemandSource",
    "AxonDemandStatus",
    "AxonDemandStream",
    "AxonSupplyItem",
    "AxonSupplySource",
    "AxonSupplyStatus",
    "AxonSupplyStream",
    "AxonAllocation",
    "AxonAllocationAction",
    "AxonAllocationStatus",
    "AxonPlanningDecision",
    "AxonShortageItem",
]
