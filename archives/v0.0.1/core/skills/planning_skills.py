"""
AxonPlanningSkills — operations on era.ascp.pegging.ledger, demand.stream, supply.stream.

Every write method auto-posts to Chatter via self.post_ai_reasoning().
MCP tools in mcp_servers/ are thin wrappers over these methods.
"""

from __future__ import annotations

from core.odoo_client import AxonOdooXMLRPCClient
from core.skills.base_skill import AxonBaseSkill

# ── Domain-level data classes (no Pydantic — plain dicts at skill boundary) ──

LEDGER_FIELDS = [
    "id", "name", "demand_source_ref", "supply_source_ref",
    "product_id", "allocated_qty", "uom_id", "status",
    "plan_date", "demand_date", "ai_last_action",
]

DEMAND_STREAM_FIELDS = [
    "id", "name", "source_type", "source_ref", "product_id",
    "demand_qty", "confirmed_qty", "demand_date", "state",
]

SUPPLY_STREAM_FIELDS = [
    "id", "name", "source_type", "source_ref", "product_id",
    "supply_qty", "available_qty", "supply_date", "state",
]


class AxonPlanningSkills(AxonBaseSkill):
    def __init__(self, client: AxonOdooXMLRPCClient | None = None) -> None:
        super().__init__(client=client)

    # ── Pegging Ledger ────────────────────────────────────────────────────────

    def get_ledger(
        self,
        product_id: int | None = None,
        status_filter: list[str] | None = None,
        demand_date_from: str | None = None,
        demand_date_to: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Read-only — no Chatter post needed."""
        domain: list = []
        if product_id:
            domain.append(("product_id", "=", product_id))
        if status_filter:
            domain.append(("status", "in", status_filter))
        if demand_date_from:
            domain.append(("demand_date", ">=", demand_date_from))
        if demand_date_to:
            domain.append(("demand_date", "<=", demand_date_to))

        return self.client.search_read(
            "era.ascp.pegging.ledger", domain, LEDGER_FIELDS, limit=limit
        )

    def update_allocation(
        self,
        pegging_id: int,
        allocated_qty: float,
        status: str,
        ai_context: str,
        cycle_id: str | None = None,
        confidence: float | None = None,
    ) -> dict:
        """Write allocated_qty + status, then auto-post to Chatter."""
        # Capture old values for Chatter message
        old = self.client.get(
            "era.ascp.pegging.ledger", pegging_id, ["allocated_qty", "status"]
        )
        old_qty = old["allocated_qty"] if old else "?"
        old_status = old["status"] if old else "?"

        self.client.write(
            "era.ascp.pegging.ledger",
            [pegging_id],
            {
                "allocated_qty": allocated_qty,
                "status": status,
                "ai_last_action": ai_context,
            },
        )

        action_taken = (
            f"Updated allocated_qty={old_qty} → {allocated_qty}, "
            f"status={old_status} → {status}"
        )
        self.post_ai_reasoning(
            model="era.ascp.pegging.ledger",
            record_id=pegging_id,
            action_taken=action_taken,
            ai_context=ai_context,
            cycle_id=cycle_id,
            confidence=confidence,
        )

        return {"pegging_id": pegging_id, "allocated_qty": allocated_qty, "status": status}

    def create_exception(
        self,
        pegging_id: int,
        ai_context: str,
        cycle_id: str | None = None,
    ) -> dict:
        """Set status=exception + post Chatter note."""
        self.client.write(
            "era.ascp.pegging.ledger",
            [pegging_id],
            {"status": "exception", "ai_last_action": ai_context},
        )
        self.post_ai_reasoning(
            model="era.ascp.pegging.ledger",
            record_id=pegging_id,
            action_taken="Status set to EXCEPTION",
            ai_context=ai_context,
            cycle_id=cycle_id,
        )
        return {"pegging_id": pegging_id, "status": "exception"}

    # ── Demand Stream ─────────────────────────────────────────────────────────

    def get_demand_stream(
        self,
        product_id: int | None = None,
        state_filter: list[str] | None = None,
        demand_date_from: str | None = None,
        demand_date_to: str | None = None,
        limit: int = 80,
    ) -> list[dict]:
        domain: list = []
        if product_id:
            domain.append(("product_id", "=", product_id))
        if state_filter:
            domain.append(("state", "in", state_filter))
        if demand_date_from:
            domain.append(("demand_date", ">=", demand_date_from))
        if demand_date_to:
            domain.append(("demand_date", "<=", demand_date_to))

        return self.client.search_read(
            "era.ascp.demand.stream", domain, DEMAND_STREAM_FIELDS, limit=limit
        )

    def sync_demand_from_so(
        self,
        ai_context: str,
        cycle_id: str | None = None,
    ) -> dict:
        """
        Pull confirmed sale.order lines and upsert into era.ascp.demand.stream.
        Returns summary: {created, updated}.
        """
        so_lines = self.client.search_read(
            "sale.order.line",
            [("order_id.state", "in", ["sale", "done"])],
            ["id", "product_id", "product_uom_qty", "qty_delivered",
             "order_id", "price_unit"],
            limit=500,
        )

        created = 0
        updated = 0

        for line in so_lines:
            source_ref = f"SOL/{line['id']}"
            existing = self.client.search_read(
                "era.ascp.demand.stream",
                [("source_ref", "=", source_ref)],
                ["id"],
                limit=1,
            )
            demand_qty = line["product_uom_qty"]
            product_id = line["product_id"][0] if isinstance(line["product_id"], list) else line["product_id"]

            if existing:
                self.client.write(
                    "era.ascp.demand.stream",
                    [existing[0]["id"]],
                    {"demand_qty": demand_qty},
                )
                updated += 1
            else:
                self.client.create(
                    "era.ascp.demand.stream",
                    {
                        "source_type": "sale_order",
                        "source_ref": source_ref,
                        "product_id": product_id,
                        "demand_qty": demand_qty,
                        "confirmed_qty": 0.0,
                        "state": "open",
                    },
                )
                created += 1

        return {"created": created, "updated": updated, "total_lines": len(so_lines)}

    # ── Supply Stream ─────────────────────────────────────────────────────────

    def get_supply_stream(
        self,
        product_id: int | None = None,
        supply_date_from: str | None = None,
        supply_date_to: str | None = None,
        limit: int = 80,
    ) -> list[dict]:
        domain: list = []
        if product_id:
            domain.append(("product_id", "=", product_id))
        if supply_date_from:
            domain.append(("supply_date", ">=", supply_date_from))
        if supply_date_to:
            domain.append(("supply_date", "<=", supply_date_to))

        return self.client.search_read(
            "era.ascp.supply.stream", domain, SUPPLY_STREAM_FIELDS, limit=limit
        )

    # ── Shortage Check ────────────────────────────────────────────────────────

    def check_shortage(
        self,
        product_ids: list[int] | None = None,
        demand_date_from: str | None = None,
        demand_date_to: str | None = None,
    ) -> list[dict]:
        """
        Compare open demand stream vs stock.quant for each product.
        Returns a list of shortage dicts for products where demand > available.
        """
        demand_domain: list = [("state", "=", "open")]
        if product_ids:
            demand_domain.append(("product_id", "in", product_ids))
        if demand_date_from:
            demand_domain.append(("demand_date", ">=", demand_date_from))
        if demand_date_to:
            demand_domain.append(("demand_date", "<=", demand_date_to))

        demand_records = self.client.search_read(
            "era.ascp.demand.stream",
            demand_domain,
            ["product_id", "demand_qty", "demand_date", "id"],
            limit=500,
        )

        shortages: list[dict] = []
        for rec in demand_records:
            prod_id = rec["product_id"][0] if isinstance(rec["product_id"], list) else rec["product_id"]
            prod_name = rec["product_id"][1] if isinstance(rec["product_id"], list) else str(prod_id)

            quants = self.client.search_read(
                "stock.quant",
                [("product_id", "=", prod_id), ("location_id.usage", "=", "internal")],
                ["qty_available"],
                limit=1,
            )
            available = quants[0]["qty_available"] if quants else 0.0
            demand = rec["demand_qty"]

            if demand > available:
                shortages.append({
                    "product_id": prod_id,
                    "product_name": prod_name,
                    "demand_qty": demand,
                    "available_qty": available,
                    "shortage_qty": demand - available,
                    "demand_date": rec["demand_date"],
                    "demand_stream_id": rec["id"],
                })

        return shortages

    # ── Cycle Audit Log ───────────────────────────────────────────────────────

    def log_cycle_summary(
        self,
        record_id: int,
        cycle_id: str,
        summary_text: str,
    ) -> None:
        """
        Post a cycle-completion summary to a pegging ledger record's audit trail.

        The orchestrator calls this without knowing which ERP model is involved
        — that detail stays in this Odoo skill.
        """
        self.post_ai_reasoning(
            model="era.ascp.pegging.ledger",
            record_id=record_id,
            action_taken=f"Cycle {cycle_id} completed",
            ai_context=summary_text,
            cycle_id=cycle_id,
        )
