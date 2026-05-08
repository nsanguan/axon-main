"""
AxonProcurementSkills — purchase.order, purchase.order.line, product.supplierinfo ops.

Every write method auto-posts to Chatter via self.post_ai_reasoning().
"""

from __future__ import annotations

from core.odoo_client import AxonOdooXMLRPCClient
from core.skills.base_skill import AxonBaseSkill

PO_FIELDS = [
    "id", "name", "partner_id", "state", "date_order",
    "date_planned", "amount_total", "currency_id",
    "order_line", "note",
]

PO_LINE_FIELDS = [
    "id", "product_id", "product_qty", "price_unit",
    "date_planned", "product_uom", "order_id",
]

SUPPLIER_INFO_FIELDS = [
    "id", "partner_id", "product_id", "product_tmpl_id",
    "min_qty", "price", "delay", "currency_id",
]


class AxonProcurementSkills(AxonBaseSkill):
    def __init__(self, client: AxonOdooXMLRPCClient | None = None) -> None:
        super().__init__(client=client)

    # ── RFQ / PO Queries ──────────────────────────────────────────────────────

    def get_rfq_list(
        self,
        partner_id: int | None = None,
        state_filter: list[str] | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Read-only — no Chatter post needed."""
        domain: list = [("state", "in", state_filter or ["draft", "sent"])]
        if partner_id:
            domain.append(("partner_id", "=", partner_id))
        return self.client.search_read("purchase.order", domain, PO_FIELDS, limit=limit)

    def get_vendor_lead_time(
        self,
        product_id: int,
        limit: int = 10,
    ) -> list[dict]:
        """Return vendor price/lead-time from product.supplierinfo."""
        return self.client.search_read(
            "product.supplierinfo",
            [("product_id", "=", product_id)],
            SUPPLIER_INFO_FIELDS,
            limit=limit,
            order="price asc",
        )

    # ── RFQ Creation ──────────────────────────────────────────────────────────

    def create_rfq(
        self,
        partner_id: int,
        lines: list[dict],
        ai_context: str,
        cycle_id: str | None = None,
        notes: str | None = None,
    ) -> dict:
        """
        Create a purchase.order (RFQ) with lines.
        Each line dict: {product_id, product_qty, price_unit, date_planned}

        Auto-posts Chatter on the created PO.
        """
        po_values: dict = {
            "partner_id": partner_id,
            "order_line": [
                (0, 0, {
                    "product_id": line["product_id"],
                    "product_qty": line["product_qty"],
                    "price_unit": line.get("price_unit", 0.0),
                    "date_planned": line.get("date_planned"),
                })
                for line in lines
            ],
        }
        if notes:
            po_values["notes"] = notes

        po_id = self.client.create("purchase.order", po_values)

        product_names = [str(line["product_id"]) for line in lines]
        action_taken = (
            f"Created RFQ for vendor_id={partner_id} "
            f"with {len(lines)} line(s): {', '.join(product_names)}"
        )
        self.post_ai_reasoning(
            model="purchase.order",
            record_id=po_id,
            action_taken=action_taken,
            ai_context=ai_context,
            cycle_id=cycle_id,
        )

        return {"po_id": po_id}

    # ── PO Confirmation ───────────────────────────────────────────────────────

    def confirm_po(
        self,
        po_id: int,
        ai_context: str,
        cycle_id: str | None = None,
    ) -> dict:
        """Confirm a PO (RFQ → Purchase Order) and post Chatter."""
        self.client.call_method("purchase.order", "button_confirm", [po_id])

        self.post_ai_reasoning(
            model="purchase.order",
            record_id=po_id,
            action_taken="PO confirmed (RFQ → Purchase Order)",
            ai_context=ai_context,
            cycle_id=cycle_id,
        )

        return {"po_id": po_id, "state": "purchase"}
