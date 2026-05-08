"""
Integration smoke tests for Axon — AI-Native Supply Chain Planning Engine.

Run:  .venv/bin/python -m pytest tests/ -v

These tests verify:
  1. All Python imports resolve cleanly (core, schema, adapters, agents, orchestrator)
  2. Odoo XML-RPC connectivity (UID authenticated)
  3. All skill modules can be instantiated
  4. All MCP server modules (Odoo adapter path) import without errors
  5. All agent factory functions return Agent instances without hitting the LLM
  6. Orchestrator modules import cleanly
  7. Universal schema models are well-formed
"""

from __future__ import annotations

import sys
import os

import pytest

# Ensure project root is on the path when running from any cwd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── 1. Core imports ───────────────────────────────────────────────────────────

def test_core_config_imports():
    from core.config import settings
    assert settings.odoo_url.startswith("http")
    assert settings.odoo_db
    # Odoo MCP URLs (always configured)
    assert settings.mcp_odoo_planning_url.startswith("http")
    assert settings.mcp_odoo_procurement_url.startswith("http")
    assert settings.mcp_odoo_inventory_url.startswith("http")
    # Legacy port aliases still present
    assert settings.mcp_planning_port > 0
    assert settings.mcp_procurement_port > 0
    assert settings.mcp_inventory_port > 0
    # Optional ERP adapter URL fields exist (may be empty)
    assert isinstance(settings.mcp_sap_planning_url, str)
    assert isinstance(settings.mcp_ebs_planning_url, str)
    assert isinstance(settings.mcp_d365_planning_url, str)
    assert isinstance(settings.mcp_legacy_db_url, str)
    assert isinstance(settings.mcp_custom_planning_url, str)


def test_core_odoo_client_imports():
    from core.odoo_client import AxonOdooXMLRPCClient
    assert AxonOdooXMLRPCClient is not None


# ── 2. Universal schema imports ───────────────────────────────────────────────

def test_schema_demand_imports():
    from core.schema.demand import AxonDemandItem, AxonDemandStream, AxonDemandSource, AxonDemandStatus
    assert AxonDemandSource.SALE_ORDER
    assert AxonDemandStatus.OPEN


def test_schema_supply_imports():
    from core.schema.supply import AxonSupplyItem, AxonSupplyStream, AxonSupplySource, AxonSupplyStatus
    assert AxonSupplySource.ON_HAND
    assert AxonSupplyStatus.OPEN


def test_schema_allocation_imports():
    from core.schema.allocation import AxonAllocation, AxonPlanningDecision, AxonAllocationAction
    assert AxonAllocationAction.ALLOCATE
    assert AxonAllocationAction.SHORTAGE


def test_schema_package_re_exports():
    from core.schema import (
        AxonDemandItem, AxonDemandStream, AxonDemandSource, AxonDemandStatus,
        AxonSupplyItem, AxonSupplyStream, AxonSupplySource, AxonSupplyStatus,
        AxonAllocation, AxonPlanningDecision, AxonShortageItem, AxonAllocationAction,
    )
    assert AxonDemandItem is not None


# ── 3. Adapter imports ────────────────────────────────────────────────────────

def test_adapter_mcp_client_imports():
    from adapters.mcp_client import (
        # Odoo factories
        get_axon_odoo_planning_mcp,
        get_axon_odoo_procurement_mcp,
        get_axon_odoo_inventory_mcp,
        get_axon_odoo_mcp_servers,
        # SAP factories
        get_axon_sap_planning_mcp,
        get_axon_sap_procurement_mcp,
        get_axon_sap_inventory_mcp,
        # Oracle EBS factories
        get_axon_ebs_planning_mcp,
        get_axon_ebs_procurement_mcp,
        get_axon_ebs_inventory_mcp,
        # Dynamics 365 factories
        get_axon_d365_planning_mcp,
        get_axon_d365_procurement_mcp,
        get_axon_d365_inventory_mcp,
        # Legacy DB factory
        get_axon_legacy_db_mcp,
        # Custom ERP factories
        get_axon_custom_planning_mcp,
        # Registry
        AxonAdapterRegistry,
    )
    assert callable(get_axon_odoo_mcp_servers)
    # SAP/EBS/D365/legacy return None when URL not set (adapter disabled)
    assert get_axon_sap_planning_mcp() is None
    assert get_axon_ebs_planning_mcp() is None
    assert get_axon_d365_planning_mcp() is None
    assert get_axon_legacy_db_mcp() is None


def test_adapter_registry():
    from adapters.mcp_client import AxonAdapterRegistry
    from pydantic_ai.mcp import MCPServerSSE
    registry = AxonAdapterRegistry()
    # Odoo is always enabled — planning_servers must have at least one
    planning = registry.planning_servers()
    assert len(planning) >= 1
    assert all(isinstance(s, MCPServerSSE) for s in planning)
    # enabled_erps always includes 'odoo'
    erps = registry.enabled_erps()
    assert "odoo" in erps
    # all_servers deduplicated
    all_srv = registry.all_servers()
    assert len(all_srv) >= 1


def test_adapter_mapping_odoo_imports():
    from adapters.mapping.odoo import (
        axon_demand_stream_record_to_item,
        axon_supply_stream_record_to_item,
        axon_stock_quant_to_supply_item,
        axon_pegging_ledger_to_allocation,
    )
    assert callable(axon_demand_stream_record_to_item)


def test_adapter_mapping_sap_imports():
    from adapters.mapping.sap import (
        axon_sap_demand_row_to_item,
        axon_sap_supply_row_to_item,
        axon_sap_stock_row_to_item,
        axon_sap_allocation_row_to_allocation,
    )
    assert callable(axon_sap_demand_row_to_item)


def test_adapter_mapping_oracle_ebs_imports():
    from adapters.mapping.oracle_ebs import (
        axon_ebs_demand_row_to_item,
        axon_ebs_po_row_to_item,
        axon_ebs_wip_row_to_item,
        axon_ebs_onhand_row_to_item,
        axon_ebs_requisition_row_to_allocation,
    )
    assert callable(axon_ebs_demand_row_to_item)


def test_adapter_mapping_dynamics365_imports():
    from adapters.mapping.dynamics365 import (
        axon_d365_demand_row_to_item,
        axon_d365_sales_order_line_to_item,
        axon_d365_po_line_to_item,
        axon_d365_production_order_to_item,
        axon_d365_onhand_row_to_item,
        axon_d365_requisition_row_to_allocation,
    )
    assert callable(axon_d365_demand_row_to_item)


def test_adapter_mapping_legacy_db_imports():
    from adapters.mapping.legacy_db import (
        axon_legacy_demand_row_to_item,
        axon_legacy_supply_row_to_item,
        axon_legacy_stock_row_to_item,
        axon_legacy_allocation_row_to_allocation,
    )
    assert callable(axon_legacy_demand_row_to_item)


def test_adapter_mapping_package_re_exports():
    """adapters.mapping.__init__ re-exports all ERP mappers."""
    from adapters.mapping import (
        axon_demand_stream_record_to_item,      # Odoo
        axon_sap_demand_row_to_item,            # SAP
        axon_ebs_demand_row_to_item,            # Oracle EBS
        axon_d365_demand_row_to_item,           # Dynamics 365
        axon_legacy_demand_row_to_item,         # Legacy DB
    )
    assert all(callable(f) for f in [
        axon_demand_stream_record_to_item,
        axon_sap_demand_row_to_item,
        axon_ebs_demand_row_to_item,
        axon_d365_demand_row_to_item,
        axon_legacy_demand_row_to_item,
    ])


# ── Mapping round-trip smoke tests ────────────────────────────────────────────

def test_sap_demand_mapper_round_trip():
    from adapters.mapping.sap import axon_sap_demand_row_to_item
    from core.schema.demand import AxonDemandSource
    row = {
        "SOBKZ": "KU", "MATNR": "MAT-001", "MAKTX": "Widget A",
        "BDMNG": 50.0, "BEDAT": "20260601", "DMDNR": "999",
        "VBELN": "SO-2026-001", "MEINS": "PC",
    }
    item = axon_sap_demand_row_to_item(row)
    assert item.source_type == AxonDemandSource.SALE_ORDER
    assert item.demand_qty == 50.0
    assert item.product_sku == "MAT-001"
    assert item.demand_date.year == 2026
    assert item.id.startswith("sap:demand:")


def test_sap_stock_mapper_round_trip():
    from adapters.mapping.sap import axon_sap_stock_row_to_item
    from core.schema.supply import AxonSupplySource
    row = {"MATNR": "MAT-001", "WERKS": "1000", "LGORT": "0001", "LABST": 120.0, "MEINS": "PC"}
    item = axon_sap_stock_row_to_item(row)
    assert item.source_type == AxonSupplySource.ON_HAND
    assert item.supply_qty == 120.0
    assert "1000" in item.location_ref


def test_ebs_demand_mapper_round_trip():
    from adapters.mapping.oracle_ebs import axon_ebs_demand_row_to_item
    from core.schema.demand import AxonDemandSource
    row = {
        "DEMAND_ID": 42, "ORIGINATION_TYPE": 1, "ORIGINATION_REFERENCE": "SO-789",
        "INVENTORY_ITEM_ID": 1001, "ITEM_NAME": "Gadget B",
        "USING_REQUIREMENT_QUANTITY": 30.0, "USING_ASSEMBLY_DEMAND_DATE": "2026-07-01",
        "UNIT_OF_MEASURE": "Ea",
    }
    item = axon_ebs_demand_row_to_item(row)
    assert item.source_type == AxonDemandSource.SALE_ORDER
    assert item.demand_qty == 30.0
    assert item.id == "ebs:demand:42"


def test_d365_po_mapper_round_trip():
    from adapters.mapping.dynamics365 import axon_d365_po_line_to_item
    from core.schema.supply import AxonSupplySource
    row = {
        "PurchaseOrderNumber": "PO-2026-001", "PurchaseOrderLineNumber": 1,
        "ItemNumber": "ITEM-X", "ProductName": "Component X",
        "OrderedPurchaseQuantity": 200.0, "RemainingPurchaseQuantity": 200.0,
        "ConfirmedDeliveryDate": "2026-08-15", "VendorAccountNumber": "V001",
        "PurchaseOrderLineStatus": "Confirmed", "PurchaseUnitSymbol": "Pcs",
    }
    item = axon_d365_po_line_to_item(row)
    assert item.source_type == AxonSupplySource.PURCHASE_ORDER
    assert item.supply_qty == 200.0
    assert item.vendor_ref == "V001"


def test_legacy_demand_mapper_flexible_keys():
    """Legacy mapper must resolve common column name variants."""
    from adapters.mapping.legacy_db import axon_legacy_demand_row_to_item
    from core.schema.demand import AxonDemandSource
    # Row uses alternate column names (sku, required_qty, need_date, so_number)
    row = {
        "id": 77, "sku": "SKU-999", "description": "Old Part",
        "required_qty": 15.0, "need_date": "2026-09-01",
        "order_type": "sale_order", "so_number": "SO-OLD-001",
        "status": "open",
    }
    item = axon_legacy_demand_row_to_item(row)
    assert item.source_type == AxonDemandSource.SALE_ORDER
    assert item.demand_qty == 15.0
    assert item.product_sku == "SKU-999"
    assert item.id == "legacy:demand:77"


def test_legacy_stock_mapper_round_trip():
    from adapters.mapping.legacy_db import axon_legacy_stock_row_to_item
    from core.schema.supply import AxonSupplySource
    row = {"id": 5, "product_code": "PROD-A", "on_hand_qty": 99.0, "warehouse": "WH-MAIN"}
    item = axon_legacy_stock_row_to_item(row)
    assert item.source_type == AxonSupplySource.ON_HAND
    assert item.supply_qty == 99.0
    assert item.location_ref == "WH-MAIN"


# ── 4. Protocol imports ───────────────────────────────────────────────────────

def test_protocols_import():
    from core.protocols import (
        AxonDemandProvider, AxonSupplyProvider,
        AxonAllocationWriter, AxonActivityWriter, AxonReasoningLogger,
    )
    assert AxonDemandProvider is not None


# ── 5. Odoo connectivity ──────────────────────────────────────────────────────

def test_odoo_authentication():
    """Verify XML-RPC authentication returns a valid UID."""
    from core.odoo_client import AxonOdooXMLRPCClient
    client = AxonOdooXMLRPCClient()
    uid = client.uid
    assert isinstance(uid, int), f"Expected int UID, got {uid!r}"
    assert uid > 0, f"Expected positive UID, got {uid}"


# ── 6. Skills instantiation ───────────────────────────────────────────────────

def test_communication_skills_instantiates():
    from core.skills.communication_skills import AxonCommunicationSkills
    comms = AxonCommunicationSkills()
    assert comms.client is not None


def test_planning_skills_instantiates():
    from core.skills.planning_skills import AxonPlanningSkills
    planning = AxonPlanningSkills()
    assert planning.client is not None


def test_procurement_skills_instantiates():
    from core.skills.procurement_skills import AxonProcurementSkills
    proc = AxonProcurementSkills()
    assert proc.client is not None


def test_inventory_skills_instantiates():
    from core.skills.inventory_skills import AxonInventorySkills
    inv = AxonInventorySkills()
    assert inv.client is not None


def test_sales_skills_instantiates():
    from core.skills.sales_skills import AxonSalesSkills
    sales = AxonSalesSkills()
    assert sales.client is not None


def test_impact_analysis_skill_instantiates():
    from core.skills.impact_analysis_skill import AxonImpactAnalysisSkill
    ia = AxonImpactAnalysisSkill()
    assert ia.price_critical_pct == 10.0
    assert ia.lead_days_critical == 14


# ── 7. Skills — live Odoo reads ───────────────────────────────────────────────

def test_planning_skills_get_ledger_returns_list():
    from core.skills.planning_skills import AxonPlanningSkills
    planning = AxonPlanningSkills()
    result = planning.get_ledger(limit=5)
    assert isinstance(result, list)


def test_planning_skills_get_demand_stream_returns_list():
    from core.skills.planning_skills import AxonPlanningSkills
    planning = AxonPlanningSkills()
    result = planning.get_demand_stream(limit=5)
    assert isinstance(result, list)


def test_planning_skills_get_supply_stream_returns_list():
    from core.skills.planning_skills import AxonPlanningSkills
    planning = AxonPlanningSkills()
    result = planning.get_supply_stream(limit=5)
    assert isinstance(result, list)


def test_procurement_skills_get_rfq_list_returns_list():
    from core.skills.procurement_skills import AxonProcurementSkills
    proc = AxonProcurementSkills()
    result = proc.get_rfq_list(limit=5)
    assert isinstance(result, list)


def test_inventory_skills_get_stock_quant_returns_list():
    from core.skills.inventory_skills import AxonInventorySkills
    inv = AxonInventorySkills()
    result = inv.get_stock_quant(limit=5)
    assert isinstance(result, list)


def test_planning_skills_check_shortage_returns_list():
    from core.skills.planning_skills import AxonPlanningSkills
    planning = AxonPlanningSkills()
    result = planning.check_shortage()
    assert isinstance(result, list)


# ── 8. MCP server modules import cleanly (Odoo adapter path) ─────────────────

def _load_server(relative_path: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mcp_server",
        os.path.join(os.path.dirname(__file__), "..", relative_path),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mcp_odoo_planning_server_imports():
    mod = _load_server("mcp_servers/odoo/planning/server.py")
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "axon_get_ledger")
    assert hasattr(mod, "axon_update_allocation")
    assert hasattr(mod, "axon_check_shortage")
    assert hasattr(mod, "axon_sync_demand_stream")
    assert hasattr(mod, "axon_get_supply_stream")
    assert hasattr(mod, "axon_post_comment")
    assert hasattr(mod, "axon_create_activity")


def test_mcp_odoo_procurement_server_imports():
    mod = _load_server("mcp_servers/odoo/procurement/server.py")
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "axon_get_rfq_list")
    assert hasattr(mod, "axon_create_rfq")
    assert hasattr(mod, "axon_confirm_po")
    assert hasattr(mod, "axon_analyse_rfq_impact")


def test_mcp_odoo_inventory_server_imports():
    mod = _load_server("mcp_servers/odoo/inventory/server.py")
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "axon_get_stock_quant")
    assert hasattr(mod, "axon_get_incoming_moves")


# ── 9. Agent factories return Agent instances ─────────────────────────────────

def test_planning_agent_factory():
    from pydantic_ai import Agent
    from agents.planning import get_axon_planning_agent, AxonPlanningDecision
    agent = get_axon_planning_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_buyer_agent_factory():
    from pydantic_ai import Agent
    from agents.purchase.buyer import get_axon_buyer_agent, AxonBuyerDecision
    agent = get_axon_buyer_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_purchase_manager_agent_factory():
    from pydantic_ai import Agent
    from agents.purchase.manager import get_axon_purchase_manager_agent, AxonManagerAnalysis
    agent = get_axon_purchase_manager_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_purchase_director_agent_factory():
    from pydantic_ai import Agent
    from agents.purchase.director import get_axon_purchase_director_agent, AxonDirectorDecision
    agent = get_axon_purchase_director_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_executive_agent_factory():
    from pydantic_ai import Agent
    from agents.executive import get_axon_executive_agent, AxonExecutiveSummary
    agent = get_axon_executive_agent()
    assert isinstance(agent, Agent)
    # Executive connects to all 3 MCP servers
    assert len(agent.toolsets) >= 3


# ── 10. Orchestrator ──────────────────────────────────────────────────────────

def test_axon_state_fields():
    from orchestrator.state import AxonState
    hints = AxonState.__annotations__
    assert "cycle_id" in hints
    assert "demand_stream" in hints
    assert "supply_stream" in hints
    assert "pegging_ledger" in hints
    assert "planning_decision" in hints
    assert "shortages" in hints


def test_orchestrator_graphs_main_imports():
    from orchestrator.graphs.main import build_axon_workflow
    assert callable(build_axon_workflow)


def test_orchestrator_graphs_purchase_imports():
    from orchestrator.graphs.purchase import axon_purchase_subgraph, AxonPurchaseState
    assert axon_purchase_subgraph is not None  # compiled StateGraph, not a bare callable


# ── 11. Non-Odoo ERP MCP server modules import cleanly ───────────────────────

def test_mcp_sap_server_imports():
    mod = _load_server("mcp_servers/sap/server.py")
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "axon_sap_get_demand")
    assert hasattr(mod, "axon_sap_get_supply")
    assert hasattr(mod, "axon_sap_get_stock")
    assert hasattr(mod, "axon_sap_create_pr")
    assert hasattr(mod, "axon_sap_confirm_po")
    assert hasattr(mod, "axon_sap_post_comment")
    assert hasattr(mod, "axon_sap_create_activity")
    assert hasattr(mod, "axon_sap_check_activity_done")


def test_mcp_oracle_ebs_server_imports():
    mod = _load_server("mcp_servers/oracle_ebs/server.py")
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "axon_ebs_get_demand")
    assert hasattr(mod, "axon_ebs_get_supply")
    assert hasattr(mod, "axon_ebs_get_stock")
    assert hasattr(mod, "axon_ebs_create_requisition")
    assert hasattr(mod, "axon_ebs_confirm_po")
    assert hasattr(mod, "axon_ebs_post_comment")
    assert hasattr(mod, "axon_ebs_create_activity")
    assert hasattr(mod, "axon_ebs_check_activity_done")


def test_mcp_dynamics365_server_imports():
    mod = _load_server("mcp_servers/dynamics365/server.py")
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "axon_d365_get_demand")
    assert hasattr(mod, "axon_d365_get_supply")
    assert hasattr(mod, "axon_d365_get_stock")
    assert hasattr(mod, "axon_d365_create_pr")
    assert hasattr(mod, "axon_d365_confirm_po")
    assert hasattr(mod, "axon_d365_post_comment")
    assert hasattr(mod, "axon_d365_create_activity")
    assert hasattr(mod, "axon_d365_check_activity_done")


def test_mcp_legacy_db_server_imports():
    mod = _load_server("mcp_servers/legacy_db/server.py")
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "axon_legacy_get_demand")
    assert hasattr(mod, "axon_legacy_get_supply")
    assert hasattr(mod, "axon_legacy_get_on_hand")
    assert hasattr(mod, "axon_legacy_write_allocation")
    assert hasattr(mod, "axon_legacy_post_comment")
    assert hasattr(mod, "axon_legacy_create_activity")
    assert hasattr(mod, "axon_legacy_check_activity_done")


def test_mcp_netsuite_server_imports():
    mod = _load_server("mcp_servers/netsuite/server.py")
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "axon_netsuite_get_demand")
    assert hasattr(mod, "axon_netsuite_get_supply")
    assert hasattr(mod, "axon_netsuite_get_stock")
    assert hasattr(mod, "axon_netsuite_create_po")
    assert hasattr(mod, "axon_netsuite_confirm_po")
    assert hasattr(mod, "axon_netsuite_post_comment")
    assert hasattr(mod, "axon_netsuite_create_activity")
    assert hasattr(mod, "axon_netsuite_check_activity_done")


def test_adapter_mapping_netsuite_imports():
    from adapters.mapping.netsuite import (
        axon_netsuite_demand_row_to_item,
        axon_netsuite_supply_row_to_item,
        axon_netsuite_stock_row_to_item,
        axon_netsuite_allocation_row_to_allocation,
    )
    assert callable(axon_netsuite_demand_row_to_item)
    assert callable(axon_netsuite_supply_row_to_item)
    assert callable(axon_netsuite_stock_row_to_item)
    assert callable(axon_netsuite_allocation_row_to_allocation)


def test_adapter_mapping_netsuite_round_trip():
    from adapters.mapping.netsuite import (
        axon_netsuite_demand_row_to_item,
        axon_netsuite_supply_row_to_item,
        axon_netsuite_stock_row_to_item,
    )

    demand_row = {
        "transaction_id": "SO-1001",
        "line_id": "SO-1001-1",
        "transaction_type": "SalesOrd",
        "status": "Pending Fulfillment",
        "item_id": "42",
        "item_name": "Widget A",
        "quantity": 100.0,
        "quantity_fulfilled": 30.0,
        "required_date": "2026-07-01",
        "location_id": "LOC-1",
    }
    demand = axon_netsuite_demand_row_to_item(demand_row)
    assert demand.demand_qty == 70.0
    assert "netsuite" in demand.id

    supply_row = {
        "transaction_id": "PO-2001",
        "line_id": "PO-2001-1",
        "transaction_type": "PurchOrd",
        "status": "Pending Receipt",
        "item_id": "42",
        "item_name": "Widget A",
        "quantity_remaining": 50.0,
        "expected_receipt_date": "2026-06-15",
        "location_id": "LOC-1",
        "vendor_id": "VND-10",
    }
    supply = axon_netsuite_supply_row_to_item(supply_row)
    assert supply.supply_qty == 50.0
    assert "netsuite" in supply.id

    stock_row = {
        "item_id": "42",
        "item_name": "Widget A",
        "location_id": "LOC-1",
        "quantity_on_hand": 200.0,
    }
    stock = axon_netsuite_stock_row_to_item(stock_row)
    assert stock.supply_qty == 200.0


def test_agents_package_exports():
    from agents import (
        get_axon_executive_agent,
        get_axon_executive_entry_agent,
        AxonExecutiveDirective,
        AxonExecutiveSummary,
        supervisor_route,
        get_axon_planning_agent,
        get_axon_buyer_agent,
        get_axon_purchase_manager_agent,
        get_axon_purchase_director_agent,
    )
    assert callable(get_axon_executive_agent)
    assert callable(get_axon_executive_entry_agent)
    assert callable(supervisor_route)


def test_supervisor_route_logic():
    from agents.supervisor import supervisor_route

    # shortage -> purchase_cluster
    state_shortage = {
        "cycle_id": "TEST-001",
        "planning_decision": {"action": "shortage", "confidence": 0.9},
        "shortages": [{"product_id": 1, "shortage_qty": 10}],
        "user_strategy": "",
        "executive_directive": None,
    }
    assert supervisor_route(state_shortage) == "purchase_cluster"

    # hitl_required -> hitl_checkpoint
    state_hitl = {
        "cycle_id": "TEST-002",
        "planning_decision": {"action": "hitl_required", "confidence": 0.8},
        "shortages": [],
        "user_strategy": "",
        "executive_directive": None,
    }
    assert supervisor_route(state_hitl) == "hitl_checkpoint"

    # low confidence -> executive_escalation
    state_low_conf = {
        "cycle_id": "TEST-003",
        "planning_decision": {"action": "allocate", "confidence": 0.5},
        "shortages": [],
        "user_strategy": "",
        "executive_directive": None,
    }
    assert supervisor_route(state_low_conf) == "executive_escalation"

    # no_action, high confidence -> qa_compliance_checkpoint
    state_ok = {
        "cycle_id": "TEST-004",
        "planning_decision": {"action": "allocate", "confidence": 0.95},
        "shortages": [],
        "user_strategy": "",
        "executive_directive": None,
    }
    assert supervisor_route(state_ok) == "qa_compliance_checkpoint"


def test_netsuite_in_config():
    from core.config import settings
    assert hasattr(settings, "mcp_netsuite_planning_url")
    assert hasattr(settings, "mcp_netsuite_procurement_url")
    assert hasattr(settings, "mcp_netsuite_inventory_url")


def test_adapter_registry_netsuite_factories():
    from adapters.mcp_client import (
        get_axon_netsuite_planning_mcp,
        get_axon_netsuite_procurement_mcp,
        get_axon_netsuite_inventory_mcp,
    )
    # URLs are empty by default — should return None
    assert get_axon_netsuite_planning_mcp() is None
    assert get_axon_netsuite_procurement_mcp() is None
    assert get_axon_netsuite_inventory_mcp() is None


# ── 12. New universal schema imports ─────────────────────────────────────────

def test_schema_production_imports():
    from core.schema.production import (
        AxonProductionStatus, AxonProductionPriority,
        AxonWorkCenter, AxonRoutingStep, AxonProductionOrder,
        AxonBOMLine, AxonBOMChange, AxonSequencingEntry, AxonSequencing, AxonMPS,
    )
    assert AxonProductionStatus.DRAFT
    assert AxonMPS is not None


def test_schema_maintenance_imports():
    from core.schema.maintenance import (
        AxonAssetStatus, AxonMaintenanceType, AxonMaintenancePriority,
        AxonAsset, AxonPMOrder, AxonBreakdown, AxonMaintenanceConstraint,
    )
    assert AxonAssetStatus.OPERATIONAL
    assert AxonMaintenanceConstraint is not None


def test_schema_quality_imports():
    from core.schema.quality import (
        AxonInspectionStatus, AxonNGSeverity, AxonComplianceOutcome,
        AxonReworkType, AxonInspection, AxonNGItem, AxonReworkOrder,
        AxonComplianceRule, AxonComplianceViolation, AxonComplianceCheck,
        AxonComplianceDecision,
    )
    assert AxonComplianceOutcome.COMPLIANT
    assert AxonComplianceDecision is not None


def test_schema_logistics_imports():
    from core.schema.logistics import (
        AxonShipmentStatus, AxonCarrier, AxonDeliveryRoute,
        AxonShipmentLine, AxonShipment, AxonATPResult, AxonATP,
    )
    assert AxonShipmentStatus.PLANNED
    assert AxonATP is not None


def test_schema_finance_imports():
    from core.schema.finance import (
        AxonCostCategory, AxonBudgetStatus, AxonBudgetValidationOutcome,
        AxonCashFlowStatus, AxonCostLine, AxonCostRecord,
        AxonBudgetLine, AxonBudget, AxonBudgetValidation,
        AxonCashFlowEntry, AxonCashFlowForecast,
    )
    assert AxonBudgetValidationOutcome.APPROVED
    assert AxonBudgetValidation is not None


# ── 13. New MCP server stubs import cleanly ───────────────────────────────────

def test_mcp_odoo_sales_server_imports():
    from mcp_servers.odoo.sales import mcp
    from mcp_servers.odoo.sales import (
        axon_get_demand_forecast, axon_atp_check, axon_get_confirmed_orders,
        axon_post_comment, axon_create_activity, axon_check_activity_done,
    )
    assert mcp is not None


def test_mcp_odoo_logistics_server_imports():
    from mcp_servers.odoo.logistics import mcp
    from mcp_servers.odoo.logistics import (
        axon_get_delivery_routes, axon_plan_shipment,
        axon_check_carrier_availability, axon_get_atp_by_date,
        axon_get_pending_shipments,
    )
    assert mcp is not None


def test_mcp_odoo_production_server_imports():
    from mcp_servers.odoo.production import mcp
    from mcp_servers.odoo.production import (
        axon_get_mps, axon_get_work_orders, axon_get_work_centres,
        axon_get_sequencing, axon_reschedule_production,
        axon_create_production_order,
    )
    assert mcp is not None


def test_mcp_odoo_pd_server_imports():
    from mcp_servers.odoo.pd import mcp
    from mcp_servers.odoo.pd import (
        axon_get_bom, axon_get_bom_changes, axon_get_routing,
        axon_notify_bom_updated,
    )
    assert mcp is not None


def test_mcp_odoo_maintenance_server_imports():
    from mcp_servers.odoo.maintenance import mcp
    from mcp_servers.odoo.maintenance import (
        axon_get_breakdowns, axon_get_pm_schedule,
        axon_get_asset_status, axon_get_maintenance_summary,
    )
    assert mcp is not None


def test_mcp_odoo_qa_server_imports():
    from mcp_servers.odoo.qa import mcp
    from mcp_servers.odoo.qa import (
        axon_get_compliance_rules, axon_check_compliance,
        axon_flag_violation, axon_request_compliance_review,
        axon_get_quality_alerts,
    )
    assert mcp is not None


def test_mcp_odoo_qc_server_imports():
    from mcp_servers.odoo.qc import mcp
    from mcp_servers.odoo.qc import (
        axon_get_inspections, axon_get_ng_items,
        axon_lock_stock, axon_create_rework_order, axon_get_rework_status,
    )
    assert mcp is not None


def test_mcp_odoo_finance_server_imports():
    from mcp_servers.odoo.finance import mcp
    from mcp_servers.odoo.finance import (
        axon_get_cost_records, axon_validate_budget,
        axon_get_cash_flow_forecast, axon_get_product_cost,
        axon_get_budget_status,
    )
    assert mcp is not None


# ── 14. New agent factories return Agent instances ────────────────────────────

def test_demand_forecast_agent_factory():
    from pydantic_ai import Agent
    from agents.sales.demand_forecasting import get_axon_demand_forecast_agent
    agent = get_axon_demand_forecast_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_atp_agent_factory():
    from pydantic_ai import Agent
    from agents.sales.atp import get_axon_atp_agent
    agent = get_axon_atp_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_distribution_agent_factory():
    from pydantic_ai import Agent
    from agents.logistics.distribution import get_axon_distribution_agent
    agent = get_axon_distribution_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_mps_agent_factory():
    from pydantic_ai import Agent
    from agents.production.mps import get_axon_mps_agent
    agent = get_axon_mps_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_reschedule_agent_factory():
    from pydantic_ai import Agent
    from agents.production.reschedule import get_axon_reschedule_agent
    agent = get_axon_reschedule_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_bom_impact_agent_factory():
    from pydantic_ai import Agent
    from agents.pd.bom_impact import get_axon_bom_impact_agent
    agent = get_axon_bom_impact_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_pm_agent_factory():
    from pydantic_ai import Agent
    from agents.maintenance.pm_scheduler import get_axon_pm_agent
    agent = get_axon_pm_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_breakdown_agent_factory():
    from pydantic_ai import Agent
    from agents.maintenance.breakdown_response import get_axon_breakdown_agent
    agent = get_axon_breakdown_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_qa_agent_factory():
    from pydantic_ai import Agent
    from agents.qa.compliance_guardrail import get_axon_qa_agent
    agent = get_axon_qa_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_qc_agent_factory():
    from pydantic_ai import Agent
    from agents.qc.inspection import get_axon_qc_agent
    agent = get_axon_qc_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_costing_agent_factory():
    from pydantic_ai import Agent
    from agents.finance.costing import get_axon_costing_agent
    agent = get_axon_costing_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_budget_validator_agent_factory():
    from pydantic_ai import Agent
    from agents.finance.budget_validator import get_axon_budget_validator_agent
    agent = get_axon_budget_validator_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


# ── 15. AxonState new fields ──────────────────────────────────────────────────

def test_axon_state_new_fields():
    from orchestrator.state import AxonState
    hints = AxonState.__annotations__
    assert "maintenance_constraints" in hints
    assert "bom_changes" in hints
    assert "ng_items" in hints
    assert "rework_orders" in hints
    assert "production_schedule" in hints
    assert "compliance_decision" in hints
    assert "budget_validation" in hints
    assert "shipments" in hints


# ── 16. Orchestrator sub-graph imports ───────────────────────────────────────

def test_orchestrator_graphs_production_imports():
    from orchestrator.graphs.production import axon_production_subgraph, ProdState
    assert axon_production_subgraph is not None


def test_orchestrator_graphs_qc_imports():
    from orchestrator.graphs.qc import axon_qc_subgraph, QCState
    assert axon_qc_subgraph is not None


def test_orchestrator_main_new_nodes_wired():
    """Verify the compiled workflow contains all new node names."""
    from orchestrator.graphs.main import axon_workflow
    # LangGraph compiled graph exposes .nodes as a mapping
    node_names = set(axon_workflow.nodes.keys())
    assert "sync_constraints" in node_names
    assert "sync_bom_changes" in node_names
    assert "sync_qc" in node_names
    assert "production_planning" in node_names
    assert "qa_compliance_checkpoint" in node_names
    assert "finance_budget_checkpoint" in node_names


# ── 17. Supervisor updated routing ───────────────────────────────────────────

def test_supervisor_route_default_goes_to_qa():
    """Default (no shortage, no hitl, high confidence) routes to qa_compliance_checkpoint."""
    from agents.supervisor import supervisor_route
    state = {
        "cycle_id": "TEST-005",
        "planning_decision": {"action": "allocate", "confidence": 0.95},
        "shortages": [],
        "user_strategy": "",
        "executive_directive": None,
        "maintenance_constraints": [],
        "bom_changes": [],
    }
    assert supervisor_route(state) == "qa_compliance_checkpoint"


# ── 18. New config settings ───────────────────────────────────────────────────

def test_config_new_llm_and_mcp_settings():
    from core.config import settings
    assert hasattr(settings, "llm_sales_model")
    assert hasattr(settings, "llm_production_model")
    assert hasattr(settings, "llm_quality_model")
    assert hasattr(settings, "llm_finance_model")
    assert hasattr(settings, "llm_logistics_model")
    assert settings.mcp_sales_port == 8004
    assert settings.mcp_logistics_port == 8005
    assert settings.mcp_production_port == 8006
    assert settings.mcp_pd_port == 8007
    assert settings.mcp_maintenance_port == 8008
    assert settings.mcp_qa_port == 8009
    assert settings.mcp_qc_port == 8010
    assert settings.mcp_finance_port == 8011

