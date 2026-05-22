"""SAP MCP Connector — MCP client only. Connects to separate mcp-sap project."""

from axon.connectors.mcp_sap.connector import SAPConnector
from axon.connectors.registry import register_connector_class

register_connector_class("sap", SAPConnector)

__all__ = ["SAPConnector"]
