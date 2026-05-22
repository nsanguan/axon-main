"""Oracle EBS MCP Connector — MCP clients for the 10-server EBS MCP Agent project.

The connector layer mirrors the EBS MCP Agent architecture with one connector
class per domain server, plus legacy composite connectors (OracleEBSConnector,
BuyerAgent, StoreAgent) for backward compatibility.

New domain connectors (matching ebs-mcp-agent servers):
  - EBSDemandConnector      (port 8102) — sales orders, forecasts, ATP
  - EBSSupplyConnector      (port 8103) — inventory, suppliers, costs, POs, PRs
  - EBSProductionConnector  (port 8104) — WIP, BOM, capacity, routing, reschedule
  - EBSLogisticsConnector   (port 8105) — shipments, carriers, transit, constraints
  - EBSQualityConnector     (port 8106) — inspection plans, defect history
  - EBSAssetConnector       (port 8107) — asset health, maintenance, downtime
  - EBSFinanceConnector     (port 8108) — budget, GL, profitability
  - EBSEngineeringConnector (port 8109) — ECOs, BOM
  - EBSWarehouseConnector   (port 8111) — full warehouse management (14 tools)

Legacy connectors (backward compat):
  - OracleEBSConnector      — composite wrapper (port 8003)
  - BuyerAgent              — procurement (port 8001)
  - StoreAgent              — inventory/warehouse (port 8002)
"""

from axon.connectors.mcp_oracle_ebs.connector import OracleEBSConnector
from axon.connectors.mcp_oracle_ebs.domain_connectors import (
    EBSAssetConnector,
    EBSDemandConnector,
    EBSEngineeringConnector,
    EBSFinanceConnector,
    EBSLogisticsConnector,
    EBSProductionConnector,
    EBSQualityConnector,
    EBSSupplyConnector,
    EBSWarehouseConnector,
)
from axon.connectors.mcp_oracle_ebs.mcp_agent_buyer import BuyerAgent
from axon.connectors.mcp_oracle_ebs.mcp_agent_store import StoreAgent
from axon.connectors.registry import register_connector_class

# Legacy composite connectors
register_connector_class("oracle_ebs", OracleEBSConnector)
register_connector_class("mcp_agent_buyer", BuyerAgent)
register_connector_class("mcp_agent_store", StoreAgent)

# New domain-specific connectors — one per EBS MCP Agent server
register_connector_class("ebs_demand", EBSDemandConnector)
register_connector_class("ebs_supply", EBSSupplyConnector)
register_connector_class("ebs_production", EBSProductionConnector)
register_connector_class("ebs_logistics", EBSLogisticsConnector)
register_connector_class("ebs_quality", EBSQualityConnector)
register_connector_class("ebs_asset", EBSAssetConnector)
register_connector_class("ebs_finance", EBSFinanceConnector)
register_connector_class("ebs_engineering", EBSEngineeringConnector)
register_connector_class("ebs_warehouse", EBSWarehouseConnector)

__all__ = [
    # Legacy
    "OracleEBSConnector",
    "BuyerAgent",
    "StoreAgent",
    # Domain-specific (EBS MCP Agent 10-server architecture)
    "EBSDemandConnector",
    "EBSSupplyConnector",
    "EBSProductionConnector",
    "EBSLogisticsConnector",
    "EBSQualityConnector",
    "EBSAssetConnector",
    "EBSFinanceConnector",
    "EBSEngineeringConnector",
    "EBSWarehouseConnector",
]
