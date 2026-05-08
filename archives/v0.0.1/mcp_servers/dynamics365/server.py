"""
mcp_servers.dynamics365.server — Microsoft Dynamics 365 MCP Adapter (Placeholder).

Exposes Dynamics 365 Supply Chain Management (D365 SCM) planning, procurement,
and inventory data to the Axon reasoning layer via SSE transport.

Implement each tool using the Dynamics 365 OData API or the D365 Business Events
framework.  Authentication uses Azure AD OAuth2 client credentials.

Tools exposed (all prefixed axon_):
  axon_d365_get_demand         — read planned orders / forecast from D365 Master Planning
  axon_d365_get_supply         — read purchase orders / production orders from D365
  axon_d365_get_stock          — on-hand inventory from InventSum / WHSInventOnHand
  axon_d365_create_pr          — create a Purchase Requisition via PurchReqTable
  axon_d365_confirm_po         — approve/confirm a PO via PurchTable workflow
  axon_d365_post_comment       — write AI reasoning as a D365 Note (DocuRef)
  axon_d365_create_activity    — create a workflow approval task (HITL)
  axon_d365_check_activity_done — poll D365 workflow task completion

Authentication (.env):
  D365_TENANT_ID     Azure AD tenant ID
  D365_CLIENT_ID     Azure AD app registration client ID
  D365_CLIENT_SECRET Azure AD app secret
  D365_BASE_URL      D365 environment URL (e.g. https://myorg.operations.dynamics.com)

To activate:
  1. Set MCP_D365_PLANNING_URL=http://<host>:8030/sse in .env
  2. Set MCP_D365_PROCUREMENT_URL and MCP_D365_INVENTORY_URL
  3. Set D365_TENANT_ID, D365_CLIENT_ID, D365_CLIENT_SECRET, D365_BASE_URL
  4. Run: python mcp_servers/dynamics365/server.py

Transport: SSE (FastMCP)
"""

from __future__ import annotations

import os

from fastmcp import FastMCP
from pydantic import BaseModel, Field

mcp = FastMCP(
    "axon-dynamics365",
    instructions=(
        "Microsoft Dynamics 365 Supply Chain Management adapter for Axon. "
        "Tools map D365 master planning, purchase orders, and inventory data "
        "into Axon's universal AxonDemandItem / AxonSupplyItem schema. "
        "Uses D365 OData v4 API with Azure AD OAuth2 authentication."
    ),
)


# ── Input / output models ─────────────────────────────────────────────────────


class D365DemandQuery(BaseModel):
    company: str = Field(description="D365 legal entity / company (e.g. 'USMF')")
    plan_name: str = Field(description="Master plan name (e.g. 'MasterPlan')")
    item_number: str | None = Field(None, description="Item number filter")
    date_from: str | None = Field(None, description="Requirement date from (YYYY-MM-DD)")
    date_to: str | None = Field(None, description="Requirement date to (YYYY-MM-DD)")
    limit: int = Field(500, description="Max records to return")


class D365SupplyQuery(BaseModel):
    company: str = Field(description="D365 legal entity / company")
    item_number: str | None = Field(None, description="Item number filter")
    supply_types: list[str] = Field(
        default_factory=lambda: ["PurchaseOrder", "ProductionOrder", "TransferOrder"],
        description="D365 supply order types to include",
    )
    date_from: str | None = Field(None, description="Delivery date from (YYYY-MM-DD)")
    limit: int = Field(500, description="Max records to return")


class D365StockQuery(BaseModel):
    company: str = Field(description="D365 legal entity / company")
    item_number: str = Field(description="D365 item number")
    site: str | None = Field(None, description="D365 site filter")
    warehouse: str | None = Field(None, description="D365 warehouse filter")


class D365PrInput(BaseModel):
    company: str = Field(description="D365 legal entity / company")
    item_number: str = Field(description="D365 item number")
    quantity: float = Field(description="Required quantity")
    required_date: str = Field(description="Required date (YYYY-MM-DD)")
    procurement_category: str | None = Field(None, description="D365 procurement category")
    vendor_account: str | None = Field(None, description="Preferred vendor account")
    ai_context: str = Field(description="AI reasoning — written to requisition purpose")


class D365PoApprovalInput(BaseModel):
    company: str = Field(description="D365 legal entity / company")
    purchase_order_number: str = Field(description="D365 PO number (e.g. 'PO-000001')")
    action: str = Field("Confirm", description="Workflow action: Confirm or Reject")
    ai_context: str = Field(description="AI reasoning context for D365 notes")


class D365CommentInput(BaseModel):
    entity: str = Field(description="D365 entity name (e.g. 'PurchaseOrders')")
    record_id: str = Field(description="Record ID or PO number")
    subject: str = Field(description="Note subject")
    note_text: str = Field(description="AI reasoning text to post as D365 DocuRef note")


class D365ActivityInput(BaseModel):
    company: str = Field(description="D365 legal entity / company")
    workflow_type: str = Field(description="D365 workflow type (e.g. 'PurchReqWorkflow')")
    record_id: str = Field(description="Record ID to start workflow on")
    subject: str = Field(description="HITL approval task subject")
    instruction: str = Field(description="Instructions for the approver (include AI reasoning)")
    assigned_to: str = Field(description="D365 user or role to assign task to")


class D365ActivityStatusQuery(BaseModel):
    workflow_id: str = Field(description="D365 workflow work item ID to poll")


# ── Tools ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def axon_d365_get_demand(query: D365DemandQuery) -> list[dict]:
    """
    [TODO] Fetch planned orders / demand from D365 Master Planning.

    Implementation guide:
      - Call D365 OData: GET /data/ReqPlanOrders?$filter=...&$top={limit}
      - Map RequirementType to AxonDemandSource (SalesOrder, Forecast, etc.)
      - Return list of dicts matching AxonDemandItem field names:
        {id, source_type, source_ref, product_id, demand_qty, demand_date, status}

    D365 OData entity: ReqPlanOrders, SalesOrders, ForecastPositionDetail
    D365 docs: https://learn.microsoft.com/dynamics365/fin-ops-core/dev-itpro/data-entities/odata
    """
    raise NotImplementedError(
        "D365 demand adapter not implemented. "
        "Call D365 OData API: GET {D365_BASE_URL}/data/ReqPlanOrders"
    )


@mcp.tool()
def axon_d365_get_supply(query: D365SupplyQuery) -> list[dict]:
    """
    [TODO] Fetch open supply (POs, production orders, transfers) from D365.

    Implementation guide:
      - PO supply: GET /data/PurchaseOrders?$filter=PurchaseOrderStatus eq 'Backorder'
      - Production: GET /data/ProductionOrders?$filter=ProductionOrderStatus eq 'Released'
      - Map to AxonSupplyItem field names:
        {id, source_type, source_ref, product_id, supply_qty, available_qty, supply_date}

    D365 OData entities: PurchaseOrders, ProductionOrders, TransferOrderShipments
    """
    raise NotImplementedError(
        "D365 supply adapter not implemented. "
        "Call D365 OData API: GET {D365_BASE_URL}/data/PurchaseOrders"
    )


@mcp.tool()
def axon_d365_get_stock(query: D365StockQuery) -> float:
    """
    [TODO] Fetch on-hand inventory from D365 InventSum / WHSInventOnHand.

    Implementation guide:
      - GET /data/InventOnHandMeasurements?$filter=ItemNumber eq '{item}'
      - Sum AvailablePhysical across site/warehouse
      - Return total on-hand as float

    D365 OData entity: InventOnHandMeasurements
    """
    raise NotImplementedError(
        "D365 stock adapter not implemented. "
        "Call D365 OData API: GET {D365_BASE_URL}/data/InventOnHandMeasurements"
    )


@mcp.tool()
def axon_d365_create_pr(input: D365PrInput) -> dict:
    """
    [TODO] Create a Purchase Requisition in D365.

    Implementation guide:
      - POST /data/PurchaseRequisitionsHeader with requisition header
      - POST /data/PurchaseRequisitionsLines for each line
      - Write ai_context to PurchaseRequisitionsPurpose field
      - Return {requisition_number, status}

    D365 OData entities: PurchaseRequisitionsHeader, PurchaseRequisitionsLines
    """
    raise NotImplementedError(
        "D365 purchase requisition adapter not implemented. "
        "POST to {D365_BASE_URL}/data/PurchaseRequisitionsHeader"
    )


@mcp.tool()
def axon_d365_confirm_po(input: D365PoApprovalInput) -> dict:
    """
    [TODO] Confirm / approve a Purchase Order in D365 via workflow or direct confirm.

    Implementation guide:
      - Option A: POST /data/PurchaseOrders(PurchaseOrderNumber='{po}')/Microsoft.Dynamics.DataEntities.confirm
      - Option B: Use D365 workflow REST endpoint to submit approval action
      - Write ai_context as a D365 note (DocuRef) on the PO
      - Return {po_number, new_status, message}
    """
    raise NotImplementedError(
        "D365 PO approval adapter not implemented. "
        "POST to {D365_BASE_URL}/data/PurchaseOrders({po})/confirm"
    )


@mcp.tool()
def axon_d365_post_comment(input: D365CommentInput) -> dict:
    """
    [TODO] Post AI reasoning to a D365 record as a DocuRef (attached note).

    Implementation guide:
      - POST /data/DocuRef with:
          RefTableName = entity, RefRecId = record_id,
          Notes = note_text, TypeId = 'Note'
      - Return {docuref_id, status}

    D365 OData entity: DocuRef
    """
    raise NotImplementedError(
        "D365 DocuRef note adapter not implemented. "
        "POST to {D365_BASE_URL}/data/DocuRef"
    )


@mcp.tool()
def axon_d365_create_activity(input: D365ActivityInput) -> dict:
    """
    [TODO] Start a D365 workflow and create a HITL approval task.

    Implementation guide:
      - POST to D365 Workflow REST: /api/services/WorkflowServices/WorkflowService/submitToWorkflow
      - Or use D365 Business Events to trigger an external approval flow
      - Return {workflow_id, work_item_id}
    """
    raise NotImplementedError(
        "D365 workflow activity adapter not implemented. "
        "Use D365 Workflow REST API or Business Events."
    )


@mcp.tool()
def axon_d365_check_activity_done(query: D365ActivityStatusQuery) -> dict:
    """
    [TODO] Poll D365 workflow work item to check if HITL approval is complete.

    Implementation guide:
      - GET /data/WorkflowWorkItems?$filter=RecId eq {workflow_id}
      - Check Status field: Pending → not done, Completed/Approved/Rejected → done
      - Return {done: bool, status, completed_by, completed_date}

    D365 OData entity: WorkflowWorkItems
    """
    raise NotImplementedError(
        "D365 workflow status adapter not implemented. "
        "Query {D365_BASE_URL}/data/WorkflowWorkItems"
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("MCP_D365_PLANNING_PORT", "8030"))
    mcp.run(transport="sse", port=port)
