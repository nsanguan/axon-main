"""
adapters.mapping.dynamics365 — Microsoft Dynamics 365 SCM → Axon Universal Schema Mapper.

Translates raw dict records returned by the Dynamics 365 MCP server tools
(axon_d365_get_demand, axon_d365_get_supply, axon_d365_get_stock)
into Axon's universal schema objects.

D365 entity → Axon field mappings:
  ReqPlanOrders (Planned Orders / demands)    → AxonDemandItem
  PurchaseOrderLines                          → AxonSupplyItem (purchase_order)
  ProductionOrders                            → AxonSupplyItem (manufacturing_order)
  InventOnHandMeasurements                    → AxonSupplyItem (on_hand)
  PurchaseRequisitionsLines                   → AxonAllocation

D365 REST/OData property naming:
  Properties follow camelCase OData convention, e.g.:
    ItemNumber, OrderedQuantity, ConfirmedShipDate, PurchaseOrderNumber
"""

from __future__ import annotations

from datetime import date

from core.schema.demand import AxonDemandItem, AxonDemandSource, AxonDemandStatus
from core.schema.supply import AxonSupplyItem, AxonSupplySource, AxonSupplyStatus
from core.schema.allocation import AxonAllocation, AxonAllocationStatus

_ERP = "d365"

# ── Internal helpers ──────────────────────────────────────────────────────────

# D365 ReqPlanOrders.OrderType values
_D365_ORDER_TYPE_TO_DEMAND_SOURCE: dict[str, AxonDemandSource] = {
    "SalesOrder":        AxonDemandSource.SALE_ORDER,
    "Forecast":          AxonDemandSource.FORECAST,
    "MasterPlan":        AxonDemandSource.MPS,
    "PlannedOrder":      AxonDemandSource.MRP,
    "TransferOrder":     AxonDemandSource.TRANSFER,
    "ProductionOrder":   AxonDemandSource.MRP,
    "Kanban":            AxonDemandSource.MRP,
}

_D365_PURCHASE_STATUS_MAP: dict[str, AxonSupplyStatus] = {
    "None":       AxonSupplyStatus.OPEN,
    "Confirmed":  AxonSupplyStatus.OPEN,
    "Received":   AxonSupplyStatus.RECEIVED,
    "Invoiced":   AxonSupplyStatus.RECEIVED,
    "Cancelled":  AxonSupplyStatus.CANCELLED,
}

_D365_PRODUCTION_STATUS_MAP: dict[str, AxonSupplyStatus] = {
    "Created":    AxonSupplyStatus.OPEN,
    "Estimated":  AxonSupplyStatus.OPEN,
    "Scheduled":  AxonSupplyStatus.OPEN,
    "Released":   AxonSupplyStatus.OPEN,
    "Started":    AxonSupplyStatus.PARTIAL,
    "ReportedAsFinished": AxonSupplyStatus.RECEIVED,
    "Ended":      AxonSupplyStatus.RECEIVED,
    "Cancelled":  AxonSupplyStatus.CANCELLED,
}


def _parse_d365_date(value: str | None) -> date:
    """Parse D365 OData date: ISO 8601 datetime string or date string."""
    if not value:
        return date.today()
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return date.today()


def _counter(prefix: str, value: int | str | None) -> str:
    return f"{_ERP}:{prefix}:{value}" if value is not None else f"{_ERP}:{prefix}:unknown"


# ── Demand mappers ────────────────────────────────────────────────────────────

def axon_d365_demand_row_to_item(row: dict) -> AxonDemandItem:
    """
    Map a D365 ReqPlanOrders demand row to AxonDemandItem.

    Expected row keys (ReqPlanOrders OData entity):
      ItemNumber, ProductName, OrderType, ReferenceSalesOrder,
      ReferencePurchaseOrder, RequirementDate, OrderedQuantity,
      CoveredQuantity, UnitSymbol, DataAreaId
    """
    order_type = str(row.get("OrderType") or row.get("order_type") or "PlannedOrder")
    ref = str(
        row.get("ReferenceSalesOrder")
        or row.get("ReferencePurchaseOrder")
        or row.get("source_ref")
        or row.get("PlannedOrderNumber")
        or ""
    )
    item_num = str(row.get("ItemNumber") or row.get("item_number") or "")
    demand_qty = float(row.get("OrderedQuantity") or row.get("demand_qty") or 0.0)
    covered_qty = float(row.get("CoveredQuantity") or row.get("confirmed_qty") or 0.0)
    raw_date = row.get("RequirementDate") or row.get("demand_date")
    row_id = row.get("PlannedOrderNumber") or row.get("id") or ref

    return AxonDemandItem(
        id=_counter("demand", row_id),
        source_type=_D365_ORDER_TYPE_TO_DEMAND_SOURCE.get(order_type, AxonDemandSource.MRP),
        source_ref=ref,
        erp_id=None,
        product_id=_counter("item", item_num),
        product_name=str(row.get("ProductName") or row.get("product_name") or item_num),
        product_sku=item_num,
        demand_qty=demand_qty,
        confirmed_qty=covered_qty,
        uom=str(row.get("UnitSymbol") or row.get("uom") or "ea"),
        demand_date=_parse_d365_date(raw_date),
        status=AxonDemandStatus.OPEN,
        metadata={"_erp": _ERP, "_raw": row},
    )


def axon_d365_sales_order_line_to_item(row: dict) -> AxonDemandItem:
    """
    Map a D365 SalesOrderLines OData row to AxonDemandItem.

    Expected row keys:
      SalesOrderNumber, LineNumber, ItemNumber, OrderedSalesQuantity,
      ShippedSalesQuantity, RequestedShippingDate, SalesOrderStatus,
      SalesUnitSymbol, CustomerAccountNumber
    """
    so_num = str(row.get("SalesOrderNumber") or row.get("source_ref") or "")
    line = str(row.get("LineNumber") or "")
    item_num = str(row.get("ItemNumber") or "")
    demand_qty = float(row.get("OrderedSalesQuantity") or row.get("demand_qty") or 0.0)
    shipped_qty = float(row.get("ShippedSalesQuantity") or row.get("confirmed_qty") or 0.0)
    raw_date = row.get("RequestedShippingDate") or row.get("ConfirmedShipDate") or row.get("demand_date")
    status_raw = str(row.get("SalesOrderStatus") or "Open")
    status_map = {
        "Open": AxonDemandStatus.OPEN,
        "Backorder": AxonDemandStatus.PARTIAL,
        "Delivered": AxonDemandStatus.CLOSED,
        "Cancelled": AxonDemandStatus.CLOSED,
    }
    row_id = f"{so_num}-{line}"

    return AxonDemandItem(
        id=_counter("sol", row_id),
        source_type=AxonDemandSource.SALE_ORDER,
        source_ref=so_num,
        erp_id=None,
        product_id=_counter("item", item_num),
        product_name=str(row.get("ProductName") or row.get("product_name") or item_num),
        product_sku=item_num,
        demand_qty=demand_qty,
        confirmed_qty=shipped_qty,
        uom=str(row.get("SalesUnitSymbol") or row.get("uom") or "ea"),
        demand_date=_parse_d365_date(raw_date),
        customer_ref=str(row.get("CustomerAccountNumber") or ""),
        status=status_map.get(status_raw, AxonDemandStatus.OPEN),
        metadata={"_erp": _ERP, "_raw": row},
    )


# ── Supply mappers ────────────────────────────────────────────────────────────

def axon_d365_po_line_to_item(row: dict) -> AxonSupplyItem:
    """
    Map a D365 PurchaseOrderLines OData row to AxonSupplyItem (purchase_order).

    Expected row keys:
      PurchaseOrderNumber, PurchaseOrderLineNumber, ItemNumber, ProductName,
      OrderedPurchaseQuantity, ReceivedPurchaseQuantity, RemainingPurchaseQuantity,
      ConfirmedDeliveryDate, RequestedDeliveryDate, VendorAccountNumber,
      PurchaseOrderLineStatus, PurchaseUnitSymbol
    """
    po_num = str(row.get("PurchaseOrderNumber") or row.get("source_ref") or "")
    line = str(row.get("PurchaseOrderLineNumber") or "")
    item_num = str(row.get("ItemNumber") or "")
    supply_qty = float(row.get("OrderedPurchaseQuantity") or row.get("supply_qty") or 0.0)
    remaining_qty = float(row.get("RemainingPurchaseQuantity") or row.get("available_qty") or supply_qty)
    raw_date = row.get("ConfirmedDeliveryDate") or row.get("RequestedDeliveryDate") or row.get("supply_date")
    status_raw = str(row.get("PurchaseOrderLineStatus") or "None")
    row_id = f"{po_num}-{line}"

    return AxonSupplyItem(
        id=_counter("po", row_id),
        source_type=AxonSupplySource.PURCHASE_ORDER,
        source_ref=po_num,
        erp_id=None,
        product_id=_counter("item", item_num),
        product_name=str(row.get("ProductName") or row.get("product_name") or item_num),
        product_sku=item_num,
        supply_qty=supply_qty,
        available_qty=remaining_qty,
        uom=str(row.get("PurchaseUnitSymbol") or row.get("uom") or "ea"),
        supply_date=_parse_d365_date(raw_date),
        vendor_ref=str(row.get("VendorAccountNumber") or row.get("vendor_ref") or ""),
        location_ref=str(row.get("WarehouseId") or row.get("location_ref") or ""),
        status=_D365_PURCHASE_STATUS_MAP.get(status_raw, AxonSupplyStatus.OPEN),
        metadata={"_erp": _ERP, "_raw": row},
    )


def axon_d365_production_order_to_item(row: dict) -> AxonSupplyItem:
    """
    Map a D365 ProductionOrders OData row to AxonSupplyItem (manufacturing_order).

    Expected row keys:
      ProductionOrderNumber, ItemNumber, ProductName,
      ProductionOrderQuantity, GoodQuantity, ProductionOrderStatus,
      ScheduledEndDate, InventoryWarehouseId, UnitSymbol
    """
    prod_num = str(row.get("ProductionOrderNumber") or row.get("source_ref") or "")
    item_num = str(row.get("ItemNumber") or "")
    qty = float(row.get("ProductionOrderQuantity") or row.get("supply_qty") or 0.0)
    done_qty = float(row.get("GoodQuantity") or row.get("received_qty") or 0.0)
    available = max(qty - done_qty, 0.0)
    raw_date = row.get("ScheduledEndDate") or row.get("supply_date")
    status_raw = str(row.get("ProductionOrderStatus") or "Created")

    return AxonSupplyItem(
        id=_counter("prod", prod_num),
        source_type=AxonSupplySource.MANUFACTURING_ORDER,
        source_ref=prod_num,
        erp_id=None,
        product_id=_counter("item", item_num),
        product_name=str(row.get("ProductName") or row.get("product_name") or item_num),
        product_sku=item_num,
        supply_qty=qty,
        available_qty=available,
        uom=str(row.get("UnitSymbol") or row.get("uom") or "ea"),
        supply_date=_parse_d365_date(raw_date),
        location_ref=str(row.get("InventoryWarehouseId") or row.get("location_ref") or ""),
        status=_D365_PRODUCTION_STATUS_MAP.get(status_raw, AxonSupplyStatus.OPEN),
        metadata={"_erp": _ERP, "_raw": row},
    )


def axon_d365_onhand_row_to_item(row: dict) -> AxonSupplyItem:
    """
    Map a D365 InventOnHandMeasurements OData row to AxonSupplyItem (on_hand).

    Expected row keys:
      ItemNumber, ProductName, UnitSymbol,
      AvailableOnHandQuantity, PhysicalInventoryQuantity,
      InventoryWarehouseId, InventorySiteId
    """
    item_num = str(row.get("ItemNumber") or row.get("item_number") or "")
    warehouse = str(row.get("InventoryWarehouseId") or row.get("location_ref") or "")
    site = str(row.get("InventorySiteId") or "")
    on_hand = float(
        row.get("AvailableOnHandQuantity")
        or row.get("PhysicalInventoryQuantity")
        or row.get("on_hand_qty")
        or 0.0
    )
    row_id = f"{site}-{warehouse}-{item_num}"

    return AxonSupplyItem(
        id=_counter("stock", row_id),
        source_type=AxonSupplySource.ON_HAND,
        source_ref="stock",
        erp_id=None,
        product_id=_counter("item", item_num),
        product_name=str(row.get("ProductName") or row.get("product_name") or item_num),
        product_sku=item_num,
        supply_qty=on_hand,
        available_qty=on_hand,
        uom=str(row.get("UnitSymbol") or row.get("uom") or "ea"),
        supply_date=date.today(),
        location_ref=f"{site}/{warehouse}" if site else warehouse,
        status=AxonSupplyStatus.OPEN,
        metadata={"_erp": _ERP, "_raw": row},
    )


# ── Allocation mappers ────────────────────────────────────────────────────────

def axon_d365_requisition_row_to_allocation(row: dict) -> AxonAllocation:
    """
    Map a D365 PurchaseRequisitionLines row to AxonAllocation.

    Expected row keys:
      RequisitionNumber, LineNumber, ItemNumber, Quantity,
      UnitSymbol, RequisitionStatus, demand_ref, supply_ref, ai_context
    """
    req_num = str(row.get("RequisitionNumber") or row.get("source_ref") or "")
    line = str(row.get("LineNumber") or "")
    item_num = str(row.get("ItemNumber") or "")
    row_id = f"{req_num}-{line}"
    status_raw = str(row.get("RequisitionStatus") or row.get("status") or "draft").lower()
    try:
        status = AxonAllocationStatus(status_raw)
    except ValueError:
        status = AxonAllocationStatus.DRAFT

    return AxonAllocation(
        id=_counter("alloc", row_id),
        erp_id=None,
        demand_id=_counter("demand", row.get("demand_ref") or row.get("SalesOrderNumber") or row_id),
        supply_id=_counter("po", row.get("supply_ref") or req_num),
        demand_ref=str(row.get("demand_ref") or row.get("SalesOrderNumber") or ""),
        supply_ref=str(row.get("supply_ref") or req_num),
        product_id=_counter("item", item_num),
        product_name=str(row.get("ProductName") or row.get("product_name") or item_num),
        allocated_qty=float(row.get("Quantity") or row.get("allocated_qty") or 0.0),
        uom=str(row.get("UnitSymbol") or row.get("uom") or "ea"),
        status=status,
        ai_context=str(row.get("ai_context") or row.get("PurchaserNotes") or ""),
        metadata={"_erp": _ERP, "_raw": row},
    )
