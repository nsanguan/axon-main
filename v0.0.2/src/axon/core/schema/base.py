"""
Axon Core Schema — Base Models

All data flowing through Axon is normalized into these Pydantic v2 models.
MCP tool outputs are transformed into instances of these types before any
agent reasoning or orchestration occurs.

Design principles:
  1. No ERP-native terminology leaks past this layer. The schema is the
     universal language — connectors translate into it, agents reason in it.
  2. Every model carries a correlation_id for full-trace observability.
  3. The SemanticTransformer protocol is the contract every connector must
     fulfill. It maps MCPToolOutput → domain models.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Primitives
# =============================================================================


class MCPToolOutput(BaseModel):
    """Generic wrapper for raw MCP tool responses before transformation.

    This is the single entry point for all external data. Every MCP
    connector returns one of these, and a SemanticTransformer maps it
    into domain models.
    """

    model_config = ConfigDict(extra="allow")

    server_name: str
    tool_name: str
    raw_payload: dict[str, Any]
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: UUID = Field(default_factory=uuid4)


class EntityRef(BaseModel):
    """Lightweight reference to an ERP-native entity.

    Agents never touch native IDs directly — they reason about EntityRefs.
    The connector layer resolves these to actual MCP tool calls when needed.
    """

    system: str  # "oracle_ebs", "sap", "odoo"
    entity_type: str  # "inventory_item", "wip_job", "production_order"
    native_id: str
    display_name: str | None = None


class Period(BaseModel):
    """A time bucket for planning data."""

    start: datetime
    end: datetime
    granularity: str = "day"  # "day", "week", "month"


# =============================================================================
# Domain Models
# =============================================================================


class Demand(BaseModel):
    """Forecast or sales-order demand for a given item and period."""

    id: UUID = Field(default_factory=uuid4)
    item: EntityRef
    quantity: Decimal
    period: Period
    source: str  # "forecast", "sales_order", "safety_stock"
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    priority: int = 0
    customer: EntityRef | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Supply(BaseModel):
    """Available or planned supply for a given item and period."""

    id: UUID = Field(default_factory=uuid4)
    item: EntityRef
    quantity: Decimal
    period: Period
    source: str  # "on_hand", "wip", "purchase_order", "planned"
    location: EntityRef | None = None
    lead_time_days: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Allocation(BaseModel):
    """A binding of demand to supply — the core planning atom."""

    id: UUID = Field(default_factory=uuid4)
    demand: Demand
    supply: Supply
    allocated_quantity: Decimal
    allocated_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "proposed"  # "proposed", "approved", "rejected", "executed"


# =============================================================================
# Negotiation Models
# =============================================================================


class ProposalStatus(StrEnum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AMENDED = "amended"


class AgentProposal(BaseModel):
    """A single agent's position in a negotiation round."""

    agent_id: str  # "sales", "production", "maintenance", ...
    round_number: int
    allocations: list[Allocation]
    utility_score: float | None = None
    justification: str | None = None
    status: ProposalStatus = ProposalStatus.PROPOSED
    amendments: list[str] = Field(default_factory=list)


class NegotiationRound(BaseModel):
    """Snapshot of one round of multi-agent negotiation."""

    round_number: int
    proposals: dict[str, AgentProposal]  # agent_id -> proposal
    global_utility: float | None = None
    resolved: bool = False
    resolution: str | None = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


# =============================================================================
# Semantic Transformation Protocol
# =============================================================================


class SemanticTransformer(BaseModel):
    """Protocol for mapping MCP tool outputs into Core Schema types.

    Each ERP connector implements a subclass of this. The orchestrator
    routes each MCPToolOutput to the correct transformer based on
    `can_handle()`.

    Concrete subclasses must override:
        transform(output: MCPToolOutput) -> list[Demand | Supply]
    """

    source_system: ClassVar[str] = ""
    supported_tools: ClassVar[list[str]] = []

    def can_handle(self, output: MCPToolOutput) -> bool:
        """Return True if this transformer handles the given MCP output."""
        return output.server_name == self.source_system and output.tool_name in self.supported_tools
