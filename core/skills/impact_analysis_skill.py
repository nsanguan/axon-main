"""
ImpactAnalysisSkill — analyse cost and time impact of procurement decisions.

Computes deltas between baseline (existing supplier info / current PO price)
and a proposed vendor quote, then classifies the result as:
  - 'acceptable'  — within all thresholds
  - 'warning'     — one threshold breached, manager should review
  - 'critical'    — major breach, director (and possibly human) must approve

All analysis is read-only; results are returned as plain dicts so the calling
agent can decide whether to write to Odoo.  The calling agent is responsible
for posting Chatter via communication_skills after acting on the analysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from core.odoo_client import OdooXMLRPCClient
from core.skills.base_skill import BaseSkill

# ── Threshold defaults ─────────────────────────────────────────────────────
PRICE_WARNING_PCT: float = 5.0    # > 5 % rise → warning
PRICE_CRITICAL_PCT: float = 10.0  # > 10 % rise → critical (HITL required)
LEAD_DAYS_WARNING: int = 7        # > 7 extra days → warning
LEAD_DAYS_CRITICAL: int = 14      # > 14 extra days → critical


@dataclass
class ImpactResult:
    product_id: int
    product_name: str

    # Price impact
    baseline_unit_price: float
    proposed_unit_price: float
    price_delta_pct: float          # positive = more expensive

    # Lead-time impact
    baseline_lead_days: int
    proposed_lead_days: int
    lead_delta_days: int            # positive = slower

    # Totals
    qty: float
    baseline_total_cost: float
    proposed_total_cost: float
    cost_delta: float               # absolute difference

    # Classification
    classification: Literal["acceptable", "warning", "critical"] = "acceptable"
    breach_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "baseline_unit_price": self.baseline_unit_price,
            "proposed_unit_price": self.proposed_unit_price,
            "price_delta_pct": round(self.price_delta_pct, 4),
            "baseline_lead_days": self.baseline_lead_days,
            "proposed_lead_days": self.proposed_lead_days,
            "lead_delta_days": self.lead_delta_days,
            "qty": self.qty,
            "baseline_total_cost": round(self.baseline_total_cost, 4),
            "proposed_total_cost": round(self.proposed_total_cost, 4),
            "cost_delta": round(self.cost_delta, 4),
            "classification": self.classification,
            "breach_reasons": self.breach_reasons,
        }


class ImpactAnalysisSkill(BaseSkill):
    """
    Analyse cost & lead-time impact between a proposed procurement action
    and the historical baseline stored in Odoo (product.supplierinfo).

    This skill is read-only.  No Odoo writes occur here.
    """

    def __init__(
        self,
        client: OdooXMLRPCClient | None = None,
        price_warning_pct: float = PRICE_WARNING_PCT,
        price_critical_pct: float = PRICE_CRITICAL_PCT,
        lead_days_warning: int = LEAD_DAYS_WARNING,
        lead_days_critical: int = LEAD_DAYS_CRITICAL,
    ) -> None:
        super().__init__(client=client)
        self.price_warning_pct = price_warning_pct
        self.price_critical_pct = price_critical_pct
        self.lead_days_warning = lead_days_warning
        self.lead_days_critical = lead_days_critical

    # ── Public API ─────────────────────────────────────────────────────────

    def analyse_rfq_lines(
        self,
        partner_id: int,
        proposed_lines: list[dict],
    ) -> list[dict]:
        """
        Compare proposed RFQ lines against Odoo baseline (product.supplierinfo).

        ``proposed_lines`` elements:
            {
              "product_id": int,
              "product_qty": float,
              "price_unit": float,        # proposed price per unit
              "lead_days": int | None,    # proposed lead time in days (optional)
            }

        Returns a list of ImpactResult.to_dict() — one per line.
        Also populates the aggregate summary key ``"_summary"`` as the last item.
        """
        results: list[ImpactResult] = []

        for line in proposed_lines:
            product_id: int = line["product_id"]
            qty: float = float(line.get("product_qty", 1.0))
            proposed_price: float = float(line.get("price_unit", 0.0))
            proposed_lead: int = int(line.get("lead_days", 0))

            baseline = self._get_baseline(product_id, partner_id)

            baseline_price: float = baseline.get("price", proposed_price)
            baseline_lead: int = int(baseline.get("delay", proposed_lead))
            product_name: str = baseline.get("product_name", str(product_id))

            price_delta_pct = (
                ((proposed_price - baseline_price) / baseline_price * 100)
                if baseline_price > 0
                else 0.0
            )
            lead_delta = proposed_lead - baseline_lead if proposed_lead > 0 else 0

            breach_reasons: list[str] = []
            classification: Literal["acceptable", "warning", "critical"] = "acceptable"

            if price_delta_pct > self.price_critical_pct:
                classification = "critical"
                breach_reasons.append(
                    f"Price +{price_delta_pct:.1f}% (threshold >{self.price_critical_pct}%)"
                )
            elif price_delta_pct > self.price_warning_pct:
                if classification != "critical":
                    classification = "warning"
                breach_reasons.append(
                    f"Price +{price_delta_pct:.1f}% (threshold >{self.price_warning_pct}%)"
                )

            if lead_delta > self.lead_days_critical:
                classification = "critical"
                breach_reasons.append(
                    f"Lead time +{lead_delta} days (threshold >{self.lead_days_critical} days)"
                )
            elif lead_delta > self.lead_days_warning:
                if classification != "critical":
                    classification = "warning"
                breach_reasons.append(
                    f"Lead time +{lead_delta} days (threshold >{self.lead_days_warning} days)"
                )

            results.append(
                ImpactResult(
                    product_id=product_id,
                    product_name=product_name,
                    baseline_unit_price=baseline_price,
                    proposed_unit_price=proposed_price,
                    price_delta_pct=price_delta_pct,
                    baseline_lead_days=baseline_lead,
                    proposed_lead_days=proposed_lead if proposed_lead > 0 else baseline_lead,
                    lead_delta_days=lead_delta,
                    qty=qty,
                    baseline_total_cost=baseline_price * qty,
                    proposed_total_cost=proposed_price * qty,
                    cost_delta=(proposed_price - baseline_price) * qty,
                    classification=classification,
                    breach_reasons=breach_reasons,
                )
            )

        output = [r.to_dict() for r in results]

        # ── aggregate summary ──────────────────────────────────────────────
        total_baseline = sum(r.baseline_total_cost for r in results)
        total_proposed = sum(r.proposed_total_cost for r in results)
        total_delta = total_proposed - total_baseline
        overall_pct = (
            (total_delta / total_baseline * 100) if total_baseline > 0 else 0.0
        )
        worst = max(
            results, key=lambda r: r.price_delta_pct, default=None
        )
        overall_class = "acceptable"
        for r in results:
            if r.classification == "critical":
                overall_class = "critical"
                break
            if r.classification == "warning":
                overall_class = "warning"

        output.append({
            "_summary": True,
            "total_baseline_cost": round(total_baseline, 4),
            "total_proposed_cost": round(total_proposed, 4),
            "total_cost_delta": round(total_delta, 4),
            "overall_price_delta_pct": round(overall_pct, 4),
            "overall_classification": overall_class,
            "critical_items": [r.product_id for r in results if r.classification == "critical"],
            "warning_items": [r.product_id for r in results if r.classification == "warning"],
            "hitl_required": overall_class == "critical",
        })

        return output

    def analyse_po_for_approval(self, po_id: int) -> dict:
        """
        Re-analyse an existing PO (already in Odoo) against the baseline.
        Useful when Director needs to verify before calling ascp_confirm_po.
        """
        po_data = self.client.get(
            "purchase.order",
            po_id,
            ["id", "name", "partner_id", "order_line", "amount_total", "state"],
        )
        if not po_data:
            return {"error": f"purchase.order {po_id} not found"}

        line_ids: list[int] = po_data.get("order_line", [])
        if not line_ids:
            return {"error": "PO has no lines", "po_id": po_id}

        raw_lines = self.client.search_read(
            "purchase.order.line",
            [("id", "in", line_ids)],
            ["id", "product_id", "product_qty", "price_unit", "date_planned"],
        )

        partner_id: int = po_data["partner_id"][0] if po_data.get("partner_id") else 0

        proposed = []
        for line in raw_lines:
            proposed.append({
                "product_id": line["product_id"][0] if line.get("product_id") else 0,
                "product_qty": line.get("product_qty", 1.0),
                "price_unit": line.get("price_unit", 0.0),
            })

        analysis = self.analyse_rfq_lines(partner_id, proposed)
        return {
            "po_id": po_id,
            "po_name": po_data.get("name"),
            "partner_id": partner_id,
            "analysis": analysis,
        }

    # ── Private helpers ────────────────────────────────────────────────────

    def _get_baseline(self, product_id: int, partner_id: int) -> dict:
        """
        Fetch the best (cheapest) supplier info for this product+vendor from Odoo.
        Falls back to empty dict if no info found.
        """
        rows = self.client.search_read(
            "product.supplierinfo",
            [
                ("product_id", "=", product_id),
                ("partner_id", "=", partner_id),
            ],
            ["id", "price", "delay", "product_id", "partner_id"],
            limit=1,
            order="price asc",
        )

        if rows:
            row = rows[0]
            # Resolve product name
            product_name = ""
            prod_rows = self.client.search_read(
                "product.product",
                [("id", "=", product_id)],
                ["id", "display_name"],
                limit=1,
            )
            if prod_rows:
                product_name = prod_rows[0].get("display_name", str(product_id))
            row["product_name"] = product_name
            return row

        # No supplierinfo — fall back to product.product direct
        prod_rows = self.client.search_read(
            "product.product",
            [("id", "=", product_id)],
            ["id", "display_name", "standard_price"],
            limit=1,
        )
        if prod_rows:
            return {
                "price": prod_rows[0].get("standard_price", 0.0),
                "delay": 0,
                "product_name": prod_rows[0].get("display_name", str(product_id)),
            }
        return {"price": 0.0, "delay": 0, "product_name": str(product_id)}
