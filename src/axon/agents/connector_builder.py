"""Shared connector builder for agent MCP servers.

Provides build_connectors() which creates the full connector registry
from settings — the same logic used by node_reason in the orchestrator.
"""

from __future__ import annotations


def build_connectors() -> dict:
    """Build connector instances from settings for agent tool access."""
    from axon.connectors.mcp_llmwiki.client import PolicyServerClient
    from axon.connectors.mcp_oracle_ebs import (
        EBSAssetConnector,
        EBSAuthConnector,
        EBSDemandConnector,
        EBSEngineeringConnector,
        EBSFinanceConnector,
        EBSLogisticsConnector,
        EBSProductionConnector,
        EBSQualityConnector,
        EBSSupplyConnector,
        EBSWarehouseConnector,
    )
    from axon.connectors.mcp_sap.connector import SAPConnector
    from axon.core.config import settings

    connectors: dict = {}
    if settings.mcp_sap.enabled:
        connectors["sap"] = SAPConnector(settings.mcp_sap)
    if settings.mcp_llmwiki.enabled:
        connectors["llmwiki"] = PolicyServerClient(settings.mcp_llmwiki)
    if settings.mcp_ebs_auth.enabled:
        connectors["ebs_auth"] = EBSAuthConnector(settings.mcp_ebs_auth)
    if settings.mcp_ebs_demand.enabled:
        connectors["ebs_demand"] = EBSDemandConnector(settings.mcp_ebs_demand)
    if settings.mcp_ebs_supply.enabled:
        connectors["ebs_supply"] = EBSSupplyConnector(settings.mcp_ebs_supply)
    if settings.mcp_ebs_production.enabled:
        connectors["ebs_production"] = EBSProductionConnector(settings.mcp_ebs_production)
    if settings.mcp_ebs_logistics.enabled:
        connectors["ebs_logistics"] = EBSLogisticsConnector(settings.mcp_ebs_logistics)
    if settings.mcp_ebs_quality.enabled:
        connectors["ebs_quality"] = EBSQualityConnector(settings.mcp_ebs_quality)
    if settings.mcp_ebs_asset.enabled:
        connectors["ebs_asset"] = EBSAssetConnector(settings.mcp_ebs_asset)
    if settings.mcp_ebs_finance.enabled:
        connectors["ebs_finance"] = EBSFinanceConnector(settings.mcp_ebs_finance)
    if settings.mcp_ebs_engineering.enabled:
        connectors["ebs_engineering"] = EBSEngineeringConnector(settings.mcp_ebs_engineering)
    if settings.mcp_ebs_warehouse.enabled:
        connectors["ebs_warehouse"] = EBSWarehouseConnector(settings.mcp_ebs_warehouse)
    return connectors
