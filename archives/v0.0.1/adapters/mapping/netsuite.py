"""
adapters.mapping.netsuite — Oracle NetSuite → Axon Universal Schema Mapper.

Translates raw dict records returned by the NetSuite MCP server tools
(axon_netsuite_get_demand, axon_netsuite_get_supply, axon_netsuite_get_stock)
into Axon's universal schema objects.

NetSuite SuiteQL aliases assumed:
  TransactionLine (SalesOrd / WorkOrd) → AxonDemandItem
  TransactionLine (PurchOrd / WorkOrd) → AxonSupplyItem
  InventoryBalance                     → AxonSupplyItem (on_hand)
  Allocation write-back                → AxonAllocation
"""

from __future__ import annotations

from datetime import date, datetime

from core.schema.allocation import AxonAllocation, AxonAllocationStatus
from core.schema.demand import AxonDemandItem, AxonDemandSource, AxonDemandStatus
from core.schema.supply import AxonSupplyItem, AxonSupplySource, AxonSupplyStatus

_ERP = "netsuite"


def _id(prefix: str, value: object) -> str:
    return f"{_ERP}:{prefix}:{value}" if value is not None else f"{_ERP}:{prefix}:unknown"


def _parse_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value:
        try:
            return date.fromisoformat(str(value)[:10])
        except (ValueError, TypeError):
            pass
    return date.today()


# ── Demand type / status maps ─────────────────────────────────────────────────

_NS_DEMAND_SOURCE_MAP: dict[str, AxonDemandSource] = {
    "SalesOrd": AxonDemandSource.SALE_ORDER,
    "Forecast": AxonDemandSource.FORECAST,
    "WorkOrd":  AxonDemandSource.MRP,
}

_NS_DEMAND_STATUS_MAP: dict[str, AxonDemandStatus] = {
    "Pending Fulfillment": AxonDemandStatus.OPEN,
    "Pending Approval":    AxonDemandStatus.OPEN,
    "Partially Fulfilled": AxonDemandStatus.PARTIAL,
    "Closed":              AxonDemandStatus.CLOSED,
    "Cancelled":           AxonDemandStatus.CLOSED,
}


def axon_netsuite_demand_row_to_item(row: dict) -> AxonDemandItem:
    """
    Map a raw SuiteQL TransactionLine row (SalesOrd / WorkOrd) to AxonDemandItem.

    Expected keys:
      transaction_id, line_id, transaction_type, status,
      item_id, item_name, quantity, quantity_fulfilled,
      required_date (or ship_date), location_id
    """
    qty = float(row.get("quantity") or 0.0)
    qty_fulfilled = float(row.get("quantity_fulfilled") or 0.0)
    qty_open = max(qty - qty_fulfilled, 0.0)

    raw_type = str(row.get("transaction_type") or "SalesOrd")
    raw_status = str(row.get("status") or "Pending Fulfillment")
    ref = str(row.get("transaction_id") or row.get("line_id") or "")
    item_id = row.get("item_id") or ""

    return AxonDemandItem(
        id=_id("demand", row.get("line_id") or row.get("transaction_id")),
        source_type=_NS_DEMAND_SOURCE_MAP.get(raw_type, AxonDemandSource.SALE_ORDER),
        source_ref=ref,
        erp_id=None,
        product_id=_id("item", item_id),
        product_name=str(row.get("item_name") or ""),
        product_sku=str(item_id),
        demand_qty=qty_open,
        confirmed_qty=qty_fulfilled,
        uom=str(row.get("uom") or "EA"),
        demand_date=_parse_date(row.get("required_date") or row.get("ship_date")),
        status=_NS_DEMAND_STATUS_MAP.get(raw_status, AxonDemandStatus.OPEN),
        location_ref=str(row.get("location_id") or ""),
        metadata={"_erp": _ERP, "_raw": row},
    )


# ── Supply type / status maps ─────────────────────────────────────────────────

_NS_SUPPLY_SOURCE_MAP: dict[str, AxonSupplySource] = {
    "PurchOrd": AxonSupplySource.PURCHASE_ORDER,
    "WorkOrd":  AxonSupplySource.MANUFACTURING_ORDER,
    "TransOrd": AxonSupplySource.TRANSFER,
    "ItemRcpt": AxonSupplySource.PURCHASE_ORDER,
}

_NS_SUPPLY_STATUS_MAP: dict[str, AxonSupplyStatus] = {
    "Pending Receipt":     AxonSupplyStatus.OPEN,
    "Pending Bill":        AxonSupplyStatus.OPEN,
    "Partially Received":  AxonSupplyStatus.PARTIAL,
    "Closed":              AxonSupplyStatus.RECEIVED,
    "Cancelled":           AxonSupplyStatus.CANCELLED,
    "Pending Approval":    AxonSupplyStatus.OPEN,
}


def axon_netsuite_supply_row_to_item(row: dict) -> AxonSupplyItem:
    """
    Map a raw SuiteQL PurchOrd / WorkOrd / TransOrd TransactionLine row to AxonSupplyItem.

    Expected keys:
      transaction_id, line_id, transaction_type, status,
      item_id, item_name, quantity_remaining (or quantity),
      expected_receipt_date (or ship_date),
      location_id, vendor_id, vendor_name
    """
    raw_type = str(row.get("transaction_type") or "PurchOrd")
    raw_status = str(row.get("status") or "Pending Receipt")
    qty = float(row.get("quantity_remaining") or row.get("quantity") or 0.0)
    item_id = row.get("item_id") or ""

    return AxonSupplyItem(
        id=_id("supply", row.get("line_id") or row.get("transaction_id")),
        source_type=_NS_SUPPLY_SOURCE_MAP.get(raw_type, AxonSupplySource.PURCHASE_ORDER),
        source_ref=str(row.get("transaction_id") or ""),
        erp_id=None,
        product_id=_id("item", item_id),
        product_name=str(row.get("item_name") or ""),
        product_sku=str(item_id),
        supply_qty=qty,
        available_qty=qty,
        uom=str(row.get("uom") or "EA"),
        supply_date=_parse_date(row.get("expected_receipt_date") or row.get("ship_date")),
        vendor_ref=str(row.get("vendor_id") or row.get("vendor_name") or ""),
        location_ref=str(row.get("location_id") or ""),
        status=_NS_SUPPLY_STATUS_MAP.get(raw_status, AxonSupplyStatus.OPEN),
        metadata={"_erp": _ERP, "_raw": row},
    )


def axon_netsuite_stock_row_to_item(row: dict) -> AxonSupplyItem:
    """
    Map a raw InventoryBalance SuiteQL row to AxonSupplyItem (on_hand).

    Expected keys:
      item_id, item_name, location_id, quantity_on_hand, uom
    """
    item_id = row.get("item_id") or ""
    qty = float(row.get("quantity_on_hand") or 0.0)

    return AxonSupplyItem(
        id=_id("onhand", f"{item_id}-{row.get('location_id', '')}"),
        source_type=AxonSupplySource.ON_HAND,
        source_ref=_id("item", item_id),
        erp_id=None,
        product_id=_id("item", item_id),
        product_name=str(row.get("item_name") or ""),
        product_sku=str(item_id),
        supply_qty=qty,
        available_qty=qty,
        uom=str(row.get("uom") or "EA"),
        supply_date=date.today(),
        location_ref=str(row.get("location_id") or ""),
        status=AxonSupplyStatus.OPEN,
        metadata={"_erp": _ERP, "_raw": row},
    )


# ── Allocation mapper ─────────────────────────────────────────────────────────

def axon_netsuite_allocation_row_to_allocation(row: dict) -> AxonAllocation:
    """
    Map a NetSuite allocation / pegging row to AxonAllocation.

    Expected keys:
      id (or allocation_id), demand_ref, supply_ref, item_id, item_name,
      allocated_qty, status, ai_context, cycle_id
    """
    item_id = row.get("item_id") or ""
    row_id = row.get("id") or row.get("allocation_id") or item_id
    status_raw = str(row.get("status") or "draft").lower()
    try:
        status = AxonAllocationStatus(status_raw)
    except ValueError:
        status = AxonAllocationStatus.DRAFT

    return AxonAllocation(
        id=_id("alloc", row_id),
        erp_id=None,
        demand_id=_id("demand", row.get("demand_ref") or row_id),
        supply_id=_id("supply", row.get("supply_ref") or row_id),
        demand_ref=str(row.get("demand_ref") or ""),
        supply_ref=str(row.get("supply_ref") or ""),
        product_id=_id("item", item_id),
        product_name=str(row.get("item_name") or ""),
        allocated_qty=float(row.get("allocated_qty") or 0.0),
        uom=str(row.get("uom") or "EA"),
        status=status,
        ai_context=str(row.get("ai_context") or ""),
        cycle_id=str(row.get("cycle_id") or ""),
        metadata={"_erp": _ERP, "_raw": row},
    )
