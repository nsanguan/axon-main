"""
core.protocols — Axon Adapter Protocol Contracts.

Defines the abstract interfaces (Python Protocols) that every ERP adapter
must implement. By coding to these protocols, the orchestrator and agents
remain fully ERP-agnostic.

Any MCP adapter or data mapper that satisfies these protocols can be plugged
into Axon without modifying the core reasoning layer.

Protocols
---------
AxonDemandProvider      Read demand from any ERP
AxonSupplyProvider      Read supply from any ERP
AxonAllocationWriter    Write pegging/allocation records back to any ERP
AxonActivityWriter      Write human-approval requests (HITL) to any ERP
AxonReasoningLogger     Log AI reasoning to the ERP's audit trail (e.g. Chatter)
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from core.schema.allocation import AxonAllocation, AxonPlanningDecision
from core.schema.demand import AxonDemandItem, AxonDemandStream
from core.schema.supply import AxonSupplyItem, AxonSupplyStream


@runtime_checkable
class AxonDemandProvider(Protocol):
    """
    Read demand data from a System of Record and return universal AxonDemandStream.

    Implementations: adapters/odoo/demand.py, adapters/sap/demand.py, etc.
    """

    def get_demand_stream(self, cycle_id: str, **filters: Any) -> AxonDemandStream:
        """
        Fetch open demand records and return them as universal AxonDemandItem objects.

        Args:
            cycle_id: Planning cycle identifier.
            **filters: Provider-specific filters (e.g. date_from, product_ids).

        Returns:
            AxonDemandStream with universal AxonDemandItem objects.
        """
        ...

    def sync_demand(self, cycle_id: str, ai_context: str) -> int:
        """
        Pull demand from the source system and upsert into the ERP's demand buffer.

        Returns the number of records synced.
        """
        ...


@runtime_checkable
class AxonSupplyProvider(Protocol):
    """
    Read supply data from a System of Record and return universal AxonSupplyStream.

    Implementations: adapters/odoo/supply.py, adapters/sap/supply.py, etc.
    """

    def get_supply_stream(self, cycle_id: str, **filters: Any) -> AxonSupplyStream:
        """
        Fetch available and incoming supply records as universal AxonSupplyItem objects.
        """
        ...

    def get_on_hand(self, product_id: str, location_ref: str | None = None) -> float:
        """Return total on-hand quantity for a product."""
        ...


@runtime_checkable
class AxonAllocationWriter(Protocol):
    """
    Write allocation (pegging) records back to the System of Record.

    Implementations: adapters/odoo/allocation.py, adapters/sap/allocation.py, etc.
    """

    def write_allocation(self, allocation: AxonAllocation, ai_context: str) -> int:
        """
        Persist an AxonAllocation to the ERP.

        Returns the native ERP record ID.
        """
        ...

    def update_allocation(
        self,
        erp_id: int,
        allocated_qty: float,
        status: str,
        ai_context: str,
    ) -> bool:
        """Update an existing allocation record. Returns True on success."""
        ...


@runtime_checkable
class AxonActivityWriter(Protocol):
    """
    Create and query Human-in-the-Loop (HITL) approval tasks in the ERP.

    Implementations: adapters/odoo/activity.py, adapters/sap/workflow.py, etc.
    """

    def create_hitl_activity(
        self,
        model: str,
        record_id: int,
        summary: str,
        note: str,
        deadline: str,
        ai_context: str,
    ) -> int:
        """
        Create an approval task for a human.

        Returns the native ERP activity/task ID.
        """
        ...

    def is_activity_done(self, activity_id: int) -> bool:
        """Return True if the HITL activity has been completed by a human."""
        ...


@runtime_checkable
class AxonReasoningLogger(Protocol):
    """
    Post AI reasoning to the ERP's audit trail (e.g. Odoo Chatter, SAP workflow log).

    Every write operation in Axon must call a AxonReasoningLogger so humans can
    always read why the AI made a decision, directly in their ERP UI.

    Implementations: adapters/odoo/chatter.py, adapters/sap/auditlog.py, etc.
    """

    def log_reasoning(
        self,
        model: str,
        record_id: int,
        action_taken: str,
        ai_context: str,
        cycle_id: str | None = None,
        confidence: float | None = None,
    ) -> int:
        """
        Post a structured AI reasoning note to the ERP record's activity log.

        Returns the native ERP log entry ID.
        """
        ...
