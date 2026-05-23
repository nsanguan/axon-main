"""Oracle EBS MCP Connector — MCP clients for the EBS MCP Agent project.

The connector layer mirrors the EBS MCP Agent architecture with one connector
class per domain server.

Domain connectors (matching ebs-mcp-agent servers):
  - EBSAuthConnector        (port 8101) — authentication and session management
  - EBSDemandConnector      (port 8102) — sales orders, forecasts, ATP
  - EBSSupplyConnector      (port 8103) — inventory, suppliers, costs, POs, PRs
  - EBSProductionConnector  (port 8104) — WIP, BOM, capacity, routing, reschedule
  - EBSLogisticsConnector   (port 8105) — shipments, carriers, transit, constraints
  - EBSQualityConnector     (port 8106) — inspection plans, defect history
  - EBSAssetConnector       (port 8107) — asset health, maintenance, downtime
  - EBSFinanceConnector     (port 8108) — budget, GL, profitability
  - EBSEngineeringConnector (port 8109) — ECOs, BOM
  - EBSWarehouseConnector   (port 8111) — full warehouse management (14 tools)
"""

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
from axon.connectors.mcp_oracle_ebs.ebs_auth_connector import EBSAuthConnector
from axon.connectors.registry import register_connector_class

# EBS Auth (port 8101)
register_connector_class("ebs_auth", EBSAuthConnector)

# Domain-specific connectors — one per EBS MCP Agent server
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
    "EBSAuthConnector",
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
