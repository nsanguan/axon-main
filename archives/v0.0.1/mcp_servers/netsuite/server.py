"""
mcp_servers.netsuite.server — Oracle NetSuite MCP Adapter.

Exposes NetSuite Supply Chain, Procurement, and Inventory data to the Axon
reasoning layer via SSE transport.

Tools are implemented using the NetSuite SuiteQL / REST API.  Authentication
uses OAuth 1.0a (Token-Based Authentication) or the newer OAuth 2.0 client
credentials flow.

Tools exposed (all prefixed axon_netsuite_):
  axon_netsuite_get_demand      — sales orders / work orders from NetSuite demand
  axon_netsuite_get_supply      — purchase orders / work orders (supply side)
  axon_netsuite_get_stock       — inventory summary (InventoryItem / ItemLocation)
  axon_netsuite_create_po       — create a NetSuite Purchase Order record
  axon_netsuite_confirm_po      — approve a NetSuite PO (submit workflow approval)
  axon_netsuite_post_comment    — append a Memo / Note to any record
  axon_netsuite_create_activity — create a reminder / task for HITL approval
  axon_netsuite_check_activity_done — check whether a HITL task is resolved

Authentication (.env):
  NETSUITE_ACCOUNT_ID     NetSuite account ID (e.g. 1234567)
  NETSUITE_CONSUMER_KEY   OAuth 1.0a consumer key
  NETSUITE_CONSUMER_SECRET OAuth 1.0a consumer secret
  NETSUITE_TOKEN_ID       OAuth 1.0a access token ID
  NETSUITE_TOKEN_SECRET   OAuth 1.0a access token secret
  NETSUITE_BASE_URL       REST API base URL (e.g. https://1234567.suitetalk.api.netsuite.com)

To activate:
  1. Set MCP_NETSUITE_PLANNING_URL=http://<host>:8050/sse in .env
  2. Set MCP_NETSUITE_PROCUREMENT_URL and MCP_NETSUITE_INVENTORY_URL
  3. Configure the NETSUITE_* credentials above
  4. Run: python mcp_servers/netsuite/server.py

Transport: SSE (FastMCP) — default port 8050
"""

from __future__ import annotations

import os

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "axon-netsuite",
    instructions=(
        "Oracle NetSuite ERP adapter for Axon ASCP. "
        "Tools translate NetSuite SuiteQL / REST API responses into Axon's "
        "universal AxonDemandItem / AxonSupplyItem schema for planning, "
        "procurement, and inventory operations. "
        "Uses OAuth 1.0a Token-Based Authentication."
    ),
)

# ─────────────────────────────────────────────────────────────────────────────
# I/O models
# ─────────────────────────────────────────────────────────────────────────────


class NetSuiteGetDemandInput(BaseModel):
    subsidiary_id: int | None = Field(
        None,
        description="Filter by NetSuite subsidiary (internal ID). Omit for all subsidiaries.",
    )
    location_id: int | None = Field(
        None,
        description="Filter by NetSuite location/warehouse (internal ID).",
    )
    date_from: str | None = Field(
        None,
        description="ISO date (YYYY-MM-DD) — return demand from this date forward.",
    )
    limit: int = Field(100, description="Maximum number of records to return (max 500).")


class NetSuiteGetSupplyInput(BaseModel):
    subsidiary_id: int | None = Field(
        None,
        description="Filter by NetSuite subsidiary (internal ID).",
    )
    location_id: int | None = Field(
        None,
        description="Filter by NetSuite location/warehouse (internal ID).",
    )
    date_from: str | None = Field(
        None,
        description="ISO date — return supply arriving from this date.",
    )
    limit: int = Field(100, description="Maximum number of records to return.")


class NetSuiteGetStockInput(BaseModel):
    item_ids: list[int] = Field(
        default_factory=list,
        description="NetSuite item internal IDs to query. Empty = all items.",
    )
    location_id: int | None = Field(None, description="Filter by warehouse/location ID.")


class NetSuiteCreatePOInput(BaseModel):
    vendor_id: int = Field(description="NetSuite vendor (entity) internal ID.")
    subsidiary_id: int = Field(description="NetSuite subsidiary internal ID.")
    location_id: int = Field(description="Receiving location internal ID.")
    lines: list[dict] = Field(
        description=(
            "List of PO lines: [{item_id, quantity, rate, expected_receipt_date}]"
        )
    )
    memo: str = Field(default="", description="PO header memo / AI reasoning note.")


class NetSuiteConfirmPOInput(BaseModel):
    po_internal_id: str = Field(description="NetSuite Purchase Order internal ID to approve.")
    ai_context: str = Field(
        default="",
        description="AI reasoning text recorded on the approval action.",
    )


class NetSuitePostCommentInput(BaseModel):
    record_type: str = Field(
        description="NetSuite record type (e.g. 'purchaseorder', 'salesorder')."
    )
    record_id: str = Field(description="NetSuite record internal ID.")
    comment: str = Field(description="Memo / note text to append to the record.")
    author: str = Field(default="Axon AI", description="Author attribution for the note.")


class NetSuiteCreateActivityInput(BaseModel):
    record_type: str = Field(description="NetSuite record type to attach the task to.")
    record_id: str = Field(description="NetSuite record internal ID.")
    title: str = Field(description="Task title — brief HITL instructions for the approver.")
    message: str = Field(description="Full task message with AI reasoning context.")
    assigned_to: str | None = Field(
        None,
        description="NetSuite employee email or internal ID to assign the task to.",
    )
    due_date: str | None = Field(
        None,
        description="Task due date (ISO YYYY-MM-DD).",
    )


class NetSuiteCheckActivityInput(BaseModel):
    task_internal_id: str = Field(description="NetSuite task internal ID to poll.")


# ─────────────────────────────────────────────────────────────────────────────
# Tools
# ─────────────────────────────────────────────────────────────────────────────


@mcp.tool()
def axon_netsuite_get_demand(params: NetSuiteGetDemandInput) -> list[dict]:
    """
    Retrieve demand records from NetSuite (Sales Orders, Work Orders, Forecasts).

    Uses SuiteQL to query TransactionLine joined with Transaction where
    transaction type IN ('SalesOrd', 'WorkOrd') and status is open/pending.

    Returns a list of raw dicts to be mapped by adapters.mapping.netsuite.
    """
    # TODO: implement using NetSuite REST API (SuiteQL endpoint)
    # POST https://{NETSUITE_ACCOUNT_ID}.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql
    # with OAuth 1.0a header
    raise NotImplementedError(
        "NetSuite demand sync not yet implemented. "
        "Set NETSUITE_* credentials and implement SuiteQL query."
    )


@mcp.tool()
def axon_netsuite_get_supply(params: NetSuiteGetSupplyInput) -> list[dict]:
    """
    Retrieve supply records from NetSuite (Purchase Orders, Work Orders, Transfers).

    Uses SuiteQL to query TransactionLine WHERE type IN ('PurchOrd', 'WorkOrd',
    'TransOrd') AND status in open/pending fulfillment states.

    Returns raw dicts for mapping via adapters.mapping.netsuite.
    """
    raise NotImplementedError(
        "NetSuite supply sync not yet implemented."
    )


@mcp.tool()
def axon_netsuite_get_stock(params: NetSuiteGetStockInput) -> list[dict]:
    """
    Retrieve on-hand inventory from NetSuite (InventoryBalance / ItemLocation).

    Uses SuiteQL:
        SELECT item, location, quantityOnHand, quantityOnOrder, quantityCommitted
        FROM InventoryBalance WHERE ...
    """
    raise NotImplementedError(
        "NetSuite stock query not yet implemented."
    )


@mcp.tool()
def axon_netsuite_create_po(params: NetSuiteCreatePOInput) -> dict:
    """
    Create a Purchase Order in NetSuite via the REST Record API (POST /purchaseorder).

    Returns the new PO's internal ID and document number on success.
    """
    raise NotImplementedError(
        "NetSuite PO creation not yet implemented."
    )


@mcp.tool()
def axon_netsuite_confirm_po(params: NetSuiteConfirmPOInput) -> dict:
    """
    Approve / confirm a NetSuite Purchase Order by triggering its workflow approval.

    Uses the NetSuite REST Record PATCH endpoint or SuiteScript workflow action.
    Returns the updated PO status.
    """
    raise NotImplementedError(
        "NetSuite PO confirmation not yet implemented."
    )


@mcp.tool()
def axon_netsuite_post_comment(params: NetSuitePostCommentInput) -> dict:
    """
    Append a Memo / Note to a NetSuite record using the REST Record API
    (POST /note or PATCH record memo field).

    Returns {"ok": true, "record_id": ...} on success.
    """
    raise NotImplementedError(
        "NetSuite comment posting not yet implemented."
    )


@mcp.tool()
def axon_netsuite_create_activity(params: NetSuiteCreateActivityInput) -> dict:
    """
    Create a NetSuite Task record (type='task') to gate human-in-the-loop approval.

    Returns the new task's internal ID so it can be stored in hitl_activity_ids.
    """
    raise NotImplementedError(
        "NetSuite HITL task creation not yet implemented."
    )


@mcp.tool()
def axon_netsuite_check_activity_done(params: NetSuiteCheckActivityInput) -> dict:
    """
    Poll whether a NetSuite Task has been completed (status == 'COMPLETE').

    Returns {"done": bool, "status": str, "task_id": str}.
    """
    raise NotImplementedError(
        "NetSuite task completion check not yet implemented."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("MCP_NETSUITE_PORT", "8050"))
    mcp.run(transport="sse", port=port)
