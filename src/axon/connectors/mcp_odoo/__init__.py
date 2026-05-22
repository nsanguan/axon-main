"""Odoo MCP Connector — MCP client only. Connects to separate mcp-odoo project."""

from axon.connectors.mcp_odoo.connector import OdooConnector
from axon.connectors.registry import register_connector_class

register_connector_class("odoo", OdooConnector)

__all__ = ["OdooConnector"]
