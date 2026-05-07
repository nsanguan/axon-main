"""
Integration smoke tests for EraOwl-Agentic-ASCP.

Run:  .venv/bin/python -m pytest tests/ -v

These tests verify:
  1. All Python imports resolve cleanly
  2. Odoo XML-RPC connectivity (UID authenticated)
  3. All three era.ascp.* models are accessible via XML-RPC
  4. All skill modules can be instantiated
  5. All MCP server modules import without errors
  6. All agent factory functions return Agent instances without hitting the LLM
  7. Orchestrator modules import cleanly
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
    assert settings.mcp_planning_port > 0
    assert settings.mcp_procurement_port > 0
    assert settings.mcp_inventory_port > 0


def test_core_odoo_client_imports():
    from core.odoo_client import OdooXMLRPCClient
    assert OdooXMLRPCClient is not None


# ── 2. Odoo connectivity ──────────────────────────────────────────────────────

def test_odoo_authentication():
    """Verify XML-RPC authentication returns a valid UID."""
    from core.odoo_client import OdooXMLRPCClient
    client = OdooXMLRPCClient()
    uid = client.uid
    assert isinstance(uid, int), f"Expected int UID, got {uid!r}"
    assert uid > 0, f"Expected positive UID, got {uid}"


def test_odoo_era_ascp_pegging_ledger_accessible():
    """Verify era.ascp.pegging.ledger model exists and is queryable."""
    from core.odoo_client import OdooXMLRPCClient
    client = OdooXMLRPCClient()
    count = client.search_count("era.ascp.pegging.ledger", [])
    assert isinstance(count, int)


def test_odoo_era_ascp_demand_stream_accessible():
    """Verify era.ascp.demand.stream model exists and is queryable."""
    from core.odoo_client import OdooXMLRPCClient
    client = OdooXMLRPCClient()
    count = client.search_count("era.ascp.demand.stream", [])
    assert isinstance(count, int)


def test_odoo_era_ascp_supply_stream_accessible():
    """Verify era.ascp.supply.stream model exists and is queryable."""
    from core.odoo_client import OdooXMLRPCClient
    client = OdooXMLRPCClient()
    count = client.search_count("era.ascp.supply.stream", [])
    assert isinstance(count, int)


# ── 3. Skills ─────────────────────────────────────────────────────────────────

def test_communication_skills_instantiates():
    from core.skills.communication_skills import CommunicationSkills
    comms = CommunicationSkills()
    assert comms.client is not None


def test_planning_skills_instantiates():
    from core.skills.planning_skills import PlanningSkills
    planning = PlanningSkills()
    assert planning.client is not None


def test_procurement_skills_instantiates():
    from core.skills.procurement_skills import ProcurementSkills
    proc = ProcurementSkills()
    assert proc.client is not None


def test_inventory_skills_instantiates():
    from core.skills.inventory_skills import InventorySkills
    inv = InventorySkills()
    assert inv.client is not None


def test_sales_skills_instantiates():
    from core.skills.sales_skills import SalesSkills
    sales = SalesSkills()
    assert sales.client is not None


def test_impact_analysis_skill_instantiates():
    from core.skills.impact_analysis_skill import ImpactAnalysisSkill
    ia = ImpactAnalysisSkill()
    assert ia.price_critical_pct == 10.0
    assert ia.lead_days_critical == 14


# ── 4. Skills — live Odoo reads ───────────────────────────────────────────────

def test_planning_skills_get_ledger_returns_list():
    from core.skills.planning_skills import PlanningSkills
    planning = PlanningSkills()
    result = planning.get_ledger(limit=5)
    assert isinstance(result, list)


def test_procurement_skills_get_rfq_list_returns_list():
    from core.skills.procurement_skills import ProcurementSkills
    proc = ProcurementSkills()
    result = proc.get_rfq_list(limit=5)
    assert isinstance(result, list)


def test_inventory_skills_get_stock_quant_returns_list():
    from core.skills.inventory_skills import InventorySkills
    inv = InventorySkills()
    result = inv.get_stock_quant(limit=5)
    assert isinstance(result, list)


def test_planning_skills_check_shortage_returns_list():
    from core.skills.planning_skills import PlanningSkills
    planning = PlanningSkills()
    result = planning.check_shortage()
    assert isinstance(result, list)


# ── 5. MCP server modules import cleanly ──────────────────────────────────────

def test_mcp_planning_server_imports():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mcp_planning",
        os.path.join(os.path.dirname(__file__), "..", "mcp_servers", "mcp-ascp-planning", "server.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "ascp_get_ledger")
    assert hasattr(mod, "ascp_update_allocation")
    assert hasattr(mod, "ascp_create_exception")
    assert hasattr(mod, "ascp_check_shortage")
    assert hasattr(mod, "ascp_sync_demand_stream")
    assert hasattr(mod, "ascp_get_supply_stream")
    assert hasattr(mod, "ascp_post_comment")
    assert hasattr(mod, "ascp_create_activity")
    assert hasattr(mod, "ascp_check_activity_done")


def test_mcp_procurement_server_imports():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mcp_procurement",
        os.path.join(os.path.dirname(__file__), "..", "mcp_servers", "mcp-ascp-procurement", "server.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "ascp_get_rfq_list")
    assert hasattr(mod, "ascp_create_rfq")
    assert hasattr(mod, "ascp_confirm_po")
    assert hasattr(mod, "ascp_analyse_rfq_impact")
    assert hasattr(mod, "ascp_analyse_po_for_approval")


def test_mcp_inventory_server_imports():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "mcp_inventory",
        os.path.join(os.path.dirname(__file__), "..", "mcp_servers", "mcp-ascp-inventory", "server.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "mcp")
    assert hasattr(mod, "ascp_get_stock_quant")
    assert hasattr(mod, "ascp_get_incoming_moves")
    assert hasattr(mod, "ascp_get_outgoing_demand")
    assert hasattr(mod, "ascp_reserve_stock")
    assert hasattr(mod, "ascp_post_comment")
    assert hasattr(mod, "ascp_create_activity")


# ── 6. Agent factories return Agent instances ─────────────────────────────────

def test_planning_manager_agent_factory():
    from pydantic_ai import Agent
    from agents.planning_manager import get_planning_manager_agent, PlanningDecision
    agent = get_planning_manager_agent()
    assert isinstance(agent, Agent)
    # Verify MCPServerSSE toolset is attached
    assert len(agent.toolsets) >= 1


def test_buyer_agent_factory():
    from pydantic_ai import Agent
    from agents.purchase.buyer_agent import get_buyer_agent, BuyerDecision
    agent = get_buyer_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_purchase_manager_agent_factory():
    from pydantic_ai import Agent
    from agents.purchase.manager_agent import get_purchase_manager_agent, ManagerAnalysis
    agent = get_purchase_manager_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_purchase_director_agent_factory():
    from pydantic_ai import Agent
    from agents.purchase.director_agent import get_purchase_director_agent, DirectorDecision
    agent = get_purchase_director_agent()
    assert isinstance(agent, Agent)
    assert len(agent.toolsets) >= 1


def test_executive_agent_factory():
    from pydantic_ai import Agent
    from agents.executive_agent import get_executive_agent, ExecutiveSummary
    agent = get_executive_agent()
    assert isinstance(agent, Agent)
    # Executive connects to all 3 MCP servers
    assert len(agent.toolsets) >= 3


# ── 7. Orchestrator ───────────────────────────────────────────────────────────

def test_ascp_state_fields():
    from orchestrator.state import ASCPState
    hints = ASCPState.__annotations__
    required_fields = [
        "cycle_id", "shortages", "planning_decision",
        "buyer_decision", "manager_analysis", "director_decision",
        "purchase_analysis_logs",
        "hitl_activity_id", "hitl_activity_ids", "hitl_approved",
        "human_approval_required",
        "error", "status",
    ]
    for field in required_fields:
        assert field in hints, f"Missing field '{field}' in ASCPState"


def test_purchase_subgraph_imports():
    from orchestrator.purchase_workflow import purchase_subgraph, run_purchase_cluster
    assert purchase_subgraph is not None
    assert callable(run_purchase_cluster)


def test_main_workflow_imports():
    import orchestrator.workflow
    from orchestrator.workflow import ascp_workflow
    assert ascp_workflow is not None
