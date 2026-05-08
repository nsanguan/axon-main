"""
adapters.mapping.odoo — Odoo → Axon Universal Schema Mapper.

Translates Odoo XML-RPC record dicts (from search_read) into Axon's
universal schema models (AxonDemandItem, AxonSupplyItem, AxonAllocation).

This is the "translation layer" — Agents only ever see universal schema
objects, never raw Odoo field names.

Odoo field → Axon field mappings:
  era.ascp.demand.stream  → AxonDemandItem
  era.ascp.supply.stream  → AxonSupplyItem
  era.ascp.pegging.ledger → AxonAllocation
  stock.quant             → AxonSupplyItem (on_hand)
  sale.order.line         → AxonDemandItem (sale_order source)
"""

from __future__ import annotations

from datetime import date

from core.schema.demand import AxonDemandItem, AxonDemandSource, AxonDemandStatus
from core.schema.supply import AxonSupplyItem, AxonSupplySource, AxonSupplyStatus
from core.schema.allocation import AxonAllocation, AxonAllocationStatus

_ERP = "odoo"


# ── Demand mappers ────────────────────────────────────────────────────────────

def _odoo_state_to_demand_status(state: str) -> AxonDemandStatus:
    return {
        "open": AxonDemandStatus.OPEN,
        "pegged": AxonDemandStatus.PEGGED,
        "partial": AxonDemandStatus.PARTIAL,
        "exception": AxonDemandStatus.EXCEPTION,
        "closed": AxonDemandStatus.CLOSED,
    }.get(state, AxonDemandStatus.OPEN)


def _odoo_source_type_to_demand_source(source_type: str) -> AxonDemandSource:
    return {
        "sale_order": AxonDemandSource.SALE_ORDER,
        "forecast": AxonDemandSource.FORECAST,
        "mps": AxonDemandSource.MPS,
        "mrp": AxonDemandSource.MRP,
        "manual": AxonDemandSource.MANUAL,
        "transfer": AxonDemandSource.TRANSFER,
    }.get(source_type, AxonDemandSource.MANUAL)


def axon_demand_stream_record_to_item(record: dict) -> AxonDemandItem:
    """Map an era.ascp.demand.stream Odoo record to a universal AxonDemandItem."""
    product = record.get("product_id") or [None, "Unknown"]
    return AxonDemandItem(
        id=f"odoo:demand:{record['id']}",
        source_type=_odoo_source_type_to_demand_source(record.get("source_type", "manual")),
        source_ref=record.get("source_ref") or record.get("name", ""),
        erp_id=record["id"],
        product_id=f"odoo:product:{product[0]}",
        product_name=product[1] if isinstance(product, list) else str(product),
        demand_qty=float(record.get("demand_qty") or 0.0),
        confirmed_qty=float(record.get("confirmed_qty") or 0.0),
        demand_date=_parse_date(record.get("demand_date")),
        status=_odoo_state_to_demand_status(record.get("state", "open")),
        metadata={"_raw": record},
    )


def axon_sale_order_line_to_demand_item(sol: dict) -> AxonDemandItem:
    """Map a sale.order.line Odoo record to a universal AxonDemandItem."""
    product = sol.get("product_id") or [None, "Unknown"]
    return AxonDemandItem(
        id=f"odoo:sol:{sol['id']}",
        source_type=AxonDemandSource.SALE_ORDER,
        source_ref=sol.get("order_id", ["", ""])[1] if isinstance(sol.get("order_id"), list) else "",
        erp_id=sol["id"],
        product_id=f"odoo:product:{product[0]}",
        product_name=product[1] if isinstance(product, list) else str(product),
        demand_qty=float(sol.get("product_uom_qty") or 0.0),
        confirmed_qty=float(sol.get("qty_delivered") or 0.0),
        demand_date=_parse_date(sol.get("commitment_date") or sol.get("date_order")),
        customer_ref=sol.get("order_id", ["", ""])[1] if isinstance(sol.get("order_id"), list) else None,
        metadata={"_raw": sol},
    )


# ── Supply mappers ────────────────────────────────────────────────────────────

def axon_supply_stream_record_to_item(record: dict) -> AxonSupplyItem:
    """Map an era.ascp.supply.stream Odoo record to a universal AxonSupplyItem."""
    product = record.get("product_id") or [None, "Unknown"]
    return AxonSupplyItem(
        id=f"odoo:supply:{record['id']}",
        source_type=AxonSupplySource.PURCHASE_ORDER,
        source_ref=record.get("source_ref") or record.get("name", ""),
        erp_id=record["id"],
        product_id=f"odoo:product:{product[0]}",
        product_name=product[1] if isinstance(product, list) else str(product),
        supply_qty=float(record.get("supply_qty") or 0.0),
        available_qty=float(record.get("available_qty") or 0.0),
        supply_date=_parse_date(record.get("supply_date")),
        status=AxonSupplyStatus.OPEN,
        metadata={"_raw": record},
    )


def axon_stock_quant_to_supply_item(quant: dict) -> AxonSupplyItem:
    """Map a stock.quant Odoo record to a universal AxonSupplyItem (on_hand)."""
    product = quant.get("product_id") or [None, "Unknown"]
    location = quant.get("location_id") or [None, ""]
    return AxonSupplyItem(
        id=f"odoo:quant:{quant['id']}",
        source_type=AxonSupplySource.ON_HAND,
        source_ref="stock",
        erp_id=quant["id"],
        product_id=f"odoo:product:{product[0]}",
        product_name=product[1] if isinstance(product, list) else str(product),
        supply_qty=float(quant.get("quantity") or 0.0),
        available_qty=float(quant.get("quantity") or 0.0),
        supply_date=date.today(),
        location_ref=location[1] if isinstance(location, list) else None,
        status=AxonSupplyStatus.OPEN,
        metadata={"_raw": quant},
    )


# ── AxonAllocation mappers ────────────────────────────────────────────────────────

def axon_pegging_ledger_to_allocation(record: dict) -> AxonAllocation:
    """Map an era.ascp.pegging.ledger Odoo record to a universal AxonAllocation."""
    product = record.get("product_id") or [None, "Unknown"]
    return AxonAllocation(
        id=f"odoo:pegging:{record['id']}",
        erp_id=record["id"],
        demand_id=f"odoo:demand:{record.get('demand_source_ref', record['id'])}",
        supply_id=f"odoo:supply:{record.get('supply_source_ref', record['id'])}",
        demand_ref=record.get("demand_source_ref", ""),
        supply_ref=record.get("supply_source_ref", ""),
        product_id=f"odoo:product:{product[0]}",
        product_name=product[1] if isinstance(product, list) else str(product),
        allocated_qty=float(record.get("allocated_qty") or 0.0),
        demand_date=_parse_date(record.get("demand_date")),
        plan_date=_parse_date(record.get("plan_date") or record.get("demand_date")),
        status=AxonAllocationStatus(record.get("status", "draft")),
        ai_context=record.get("ai_last_action", ""),
        metadata={"_raw": record},
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return date.today()
