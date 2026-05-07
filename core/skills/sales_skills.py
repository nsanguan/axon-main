"""
SalesSkills — sale.order and sale.order.line read operations.

This module is READ-ONLY. It is the demand sync source.
No writes, no Chatter posts.
"""

from __future__ import annotations

from core.odoo_client import OdooXMLRPCClient
from core.skills.base_skill import BaseSkill

SO_FIELDS = [
    "id", "name", "partner_id", "state", "date_order",
    "commitment_date", "amount_total", "currency_id",
]

SO_LINE_FIELDS = [
    "id", "order_id", "product_id", "product_uom_qty",
    "qty_delivered", "price_unit", "product_uom",
    "customer_lead",
]


class SalesSkills(BaseSkill):
    def __init__(self, client: OdooXMLRPCClient | None = None) -> None:
        super().__init__(client=client)

    def get_confirmed_orders(
        self,
        partner_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Return confirmed/done sale orders."""
        domain: list = [("state", "in", ["sale", "done"])]
        if partner_id:
            domain.append(("partner_id", "=", partner_id))
        if date_from:
            domain.append(("date_order", ">=", date_from))
        if date_to:
            domain.append(("date_order", "<=", date_to))
        return self.client.search_read("sale.order", domain, SO_FIELDS, limit=limit)

    def get_order_lines(
        self,
        order_ids: list[int] | None = None,
        product_id: int | None = None,
        limit: int = 200,
    ) -> list[dict]:
        """Return sale.order.line records."""
        domain: list = [("order_id.state", "in", ["sale", "done"])]
        if order_ids:
            domain.append(("order_id", "in", order_ids))
        if product_id:
            domain.append(("product_id", "=", product_id))
        return self.client.search_read("sale.order.line", domain, SO_LINE_FIELDS, limit=limit)

    def get_open_demand_by_product(self, limit: int = 500) -> list[dict]:
        """
        Return a flat list of {product_id, product_name, total_demand_qty}
        aggregated from confirmed SO lines. Used by planning_skills.sync_demand_from_so().
        """
        lines = self.client.search_read(
            "sale.order.line",
            [("order_id.state", "in", ["sale", "done"])],
            ["product_id", "product_uom_qty"],
            limit=limit,
        )

        aggregated: dict[int, dict] = {}
        for line in lines:
            prod = line["product_id"]
            prod_id = prod[0] if isinstance(prod, list) else prod
            prod_name = prod[1] if isinstance(prod, list) else str(prod_id)
            qty = line["product_uom_qty"]

            if prod_id not in aggregated:
                aggregated[prod_id] = {
                    "product_id": prod_id,
                    "product_name": prod_name,
                    "total_demand_qty": 0.0,
                }
            aggregated[prod_id]["total_demand_qty"] += qty

        return list(aggregated.values())
