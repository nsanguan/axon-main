"""
AxonInventorySkills — stock.quant, stock.move, and custom reservation ops.

Every write method auto-posts to Chatter via self.post_ai_reasoning().
"""

from __future__ import annotations

from core.odoo_client import AxonOdooXMLRPCClient
from core.skills.base_skill import AxonBaseSkill

QUANT_FIELDS = [
    "id", "product_id", "location_id", "quantity",
    "reserved_quantity", "available_quantity",
]

MOVE_FIELDS = [
    "id", "name", "product_id", "product_uom_qty", "quantity",
    "state", "date", "location_id", "location_dest_id",
    "picking_id", "origin",
]


class AxonInventorySkills(AxonBaseSkill):
    def __init__(self, client: AxonOdooXMLRPCClient | None = None) -> None:
        super().__init__(client=client)

    # ── Stock Queries ─────────────────────────────────────────────────────────

    def get_stock_quant(
        self,
        product_id: int | None = None,
        location_id: int | None = None,
        limit: int = 80,
    ) -> list[dict]:
        """Read-only — query on-hand stock quantities."""
        domain: list = [("location_id.usage", "=", "internal")]
        if product_id:
            domain.append(("product_id", "=", product_id))
        if location_id:
            domain.append(("location_id", "=", location_id))
        return self.client.search_read("stock.quant", domain, QUANT_FIELDS, limit=limit)

    def get_incoming_moves(
        self,
        product_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 80,
    ) -> list[dict]:
        """Incoming stock moves (state = confirmed / assigned)."""
        domain: list = [
            ("state", "in", ["confirmed", "assigned", "partially_available"]),
            ("location_dest_id.usage", "=", "internal"),
        ]
        if product_id:
            domain.append(("product_id", "=", product_id))
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        return self.client.search_read("stock.move", domain, MOVE_FIELDS, limit=limit)

    def get_outgoing_demand(
        self,
        product_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 80,
    ) -> list[dict]:
        """Outgoing stock moves (confirmed/assigned, leaving internal locations)."""
        domain: list = [
            ("state", "in", ["confirmed", "assigned", "partially_available"]),
            ("location_id.usage", "=", "internal"),
            ("location_dest_id.usage", "!=", "internal"),
        ]
        if product_id:
            domain.append(("product_id", "=", product_id))
        if date_from:
            domain.append(("date", ">=", date_from))
        if date_to:
            domain.append(("date", "<=", date_to))
        return self.client.search_read("stock.move", domain, MOVE_FIELDS, limit=limit)

    # ── Stock Reservation ─────────────────────────────────────────────────────

    def reserve_stock(
        self,
        picking_id: int,
        ai_context: str,
        cycle_id: str | None = None,
    ) -> dict:
        """
        Call action_assign on a stock.picking to reserve stock.
        Posts Chatter on the picking after reservation.
        """
        self.client.call_method("stock.picking", "action_assign", [picking_id])

        self.post_ai_reasoning(
            model="stock.picking",
            record_id=picking_id,
            action_taken="Stock reserved (action_assign called)",
            ai_context=ai_context,
            cycle_id=cycle_id,
        )

        return {"picking_id": picking_id, "action": "reserved"}
