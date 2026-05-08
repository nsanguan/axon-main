"""
adapters.mcp_client — Remote MCP connection factory and adapter registry for Axon.

Each ERP system has its own set of MCP servers (planning / procurement /
inventory).  All connections use SSE transport so they can run on the same
host as the agents or on a completely separate server — the agent code never
changes; only the URL in .env changes.

Supported ERP adapters (configure via .env):
    Odoo          MCP_ODOO_PLANNING_URL / MCP_ODOO_PROCUREMENT_URL / MCP_ODOO_INVENTORY_URL
    SAP           MCP_SAP_PLANNING_URL  / MCP_SAP_PROCUREMENT_URL  / MCP_SAP_INVENTORY_URL
    Oracle EBS    MCP_EBS_PLANNING_URL  / MCP_EBS_PROCUREMENT_URL  / MCP_EBS_INVENTORY_URL
    MS Dynamics   MCP_D365_PLANNING_URL / MCP_D365_PROCUREMENT_URL / MCP_D365_INVENTORY_URL
    Legacy SQL DB MCP_LEGACY_DB_URL     (single server, all domains)
    Custom ERP    MCP_CUSTOM_PLANNING_URL / MCP_CUSTOM_PROCUREMENT_URL / MCP_CUSTOM_INVENTORY_URL

Usage — per-ERP factories:
    from adapters.mcp_client import get_axon_odoo_planning_mcp
    agent = Agent(model, toolsets=[get_axon_odoo_planning_mcp()])

Usage — adapter registry (all enabled adapters):
    from adapters.mcp_client import AxonAdapterRegistry
    registry = AxonAdapterRegistry()
    planning_mcps = registry.planning_servers()   # list[MCPServerSSE]
"""

from __future__ import annotations

from pydantic_ai.mcp import MCPServerSSE

from core.config import settings


# ─────────────────────────────────────────────────────────────────────────────
# Primitives
# ─────────────────────────────────────────────────────────────────────────────


def get_axon_mcp_server(url: str) -> MCPServerSSE:
    """Create a single MCPServerSSE from a full SSE URL."""
    return MCPServerSSE(url)


def _optional_mcp(url: str) -> MCPServerSSE | None:
    """Return MCPServerSSE if URL is configured, else None (adapter disabled)."""
    return MCPServerSSE(url) if url.strip() else None


# ─────────────────────────────────────────────────────────────────────────────
# Odoo adapter  (reference implementation — always available)
# ─────────────────────────────────────────────────────────────────────────────


def get_axon_odoo_planning_mcp() -> MCPServerSSE:
    """Connect to the Odoo Planning MCP server (remote-ready via MCP_ODOO_PLANNING_URL)."""
    return MCPServerSSE(settings.mcp_odoo_planning_url)


def get_axon_odoo_procurement_mcp() -> MCPServerSSE:
    """Connect to the Odoo Procurement MCP server (remote-ready via MCP_ODOO_PROCUREMENT_URL)."""
    return MCPServerSSE(settings.mcp_odoo_procurement_url)


def get_axon_odoo_inventory_mcp() -> MCPServerSSE:
    """Connect to the Odoo Inventory MCP server (remote-ready via MCP_ODOO_INVENTORY_URL)."""
    return MCPServerSSE(settings.mcp_odoo_inventory_url)


def get_axon_odoo_sales_mcp() -> MCPServerSSE:
    """Connect to the Odoo Sales MCP server (remote-ready via MCP_ODOO_SALES_URL)."""
    return MCPServerSSE(settings.mcp_odoo_sales_url)


def get_axon_odoo_logistics_mcp() -> MCPServerSSE:
    """Connect to the Odoo Logistics MCP server (remote-ready via MCP_ODOO_LOGISTICS_URL)."""
    return MCPServerSSE(settings.mcp_odoo_logistics_url)


def get_axon_odoo_production_mcp() -> MCPServerSSE:
    """Connect to the Odoo Production MCP server (remote-ready via MCP_ODOO_PRODUCTION_URL)."""
    return MCPServerSSE(settings.mcp_odoo_production_url)


def get_axon_odoo_pd_mcp() -> MCPServerSSE:
    """Connect to the Odoo PD (Product Development) MCP server (MCP_ODOO_PD_URL)."""
    return MCPServerSSE(settings.mcp_odoo_pd_url)


def get_axon_odoo_maintenance_mcp() -> MCPServerSSE:
    """Connect to the Odoo Maintenance MCP server (MCP_ODOO_MAINTENANCE_URL)."""
    return MCPServerSSE(settings.mcp_odoo_maintenance_url)


def get_axon_odoo_qa_mcp() -> MCPServerSSE:
    """Connect to the Odoo QA MCP server (MCP_ODOO_QA_URL)."""
    return MCPServerSSE(settings.mcp_odoo_qa_url)


def get_axon_odoo_qc_mcp() -> MCPServerSSE:
    """Connect to the Odoo QC MCP server (MCP_ODOO_QC_URL)."""
    return MCPServerSSE(settings.mcp_odoo_qc_url)


def get_axon_odoo_finance_mcp() -> MCPServerSSE:
    """Connect to the Odoo Finance MCP server (MCP_ODOO_FINANCE_URL)."""
    return MCPServerSSE(settings.mcp_odoo_finance_url)


def get_axon_odoo_mcp_servers() -> tuple[MCPServerSSE, MCPServerSSE, MCPServerSSE]:
    """Return the three core Odoo MCP servers as a tuple (planning, procurement, inventory)."""
    return (
        get_axon_odoo_planning_mcp(),
        get_axon_odoo_procurement_mcp(),
        get_axon_odoo_inventory_mcp(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# SAP adapter  (set MCP_SAP_*_URL in .env to enable)
# ─────────────────────────────────────────────────────────────────────────────


def get_axon_sap_planning_mcp() -> MCPServerSSE | None:
    """Connect to the SAP Planning MCP server, or None if MCP_SAP_PLANNING_URL is unset."""
    return _optional_mcp(settings.mcp_sap_planning_url)


def get_axon_sap_procurement_mcp() -> MCPServerSSE | None:
    """Connect to the SAP Procurement MCP server, or None if MCP_SAP_PROCUREMENT_URL is unset."""
    return _optional_mcp(settings.mcp_sap_procurement_url)


def get_axon_sap_inventory_mcp() -> MCPServerSSE | None:
    """Connect to the SAP Inventory MCP server, or None if MCP_SAP_INVENTORY_URL is unset."""
    return _optional_mcp(settings.mcp_sap_inventory_url)


# ─────────────────────────────────────────────────────────────────────────────
# Oracle EBS adapter  (set MCP_EBS_*_URL in .env to enable)
# ─────────────────────────────────────────────────────────────────────────────


def get_axon_ebs_planning_mcp() -> MCPServerSSE | None:
    """Connect to the Oracle EBS Planning MCP server, or None if MCP_EBS_PLANNING_URL is unset."""
    return _optional_mcp(settings.mcp_ebs_planning_url)


def get_axon_ebs_procurement_mcp() -> MCPServerSSE | None:
    """Connect to the Oracle EBS Procurement MCP server, or None if MCP_EBS_PROCUREMENT_URL is unset."""
    return _optional_mcp(settings.mcp_ebs_procurement_url)


def get_axon_ebs_inventory_mcp() -> MCPServerSSE | None:
    """Connect to the Oracle EBS Inventory MCP server, or None if MCP_EBS_INVENTORY_URL is unset."""
    return _optional_mcp(settings.mcp_ebs_inventory_url)


# ─────────────────────────────────────────────────────────────────────────────
# Microsoft Dynamics 365 adapter  (set MCP_D365_*_URL in .env to enable)
# ─────────────────────────────────────────────────────────────────────────────


def get_axon_d365_planning_mcp() -> MCPServerSSE | None:
    """Connect to the Dynamics 365 Planning MCP server, or None if MCP_D365_PLANNING_URL is unset."""
    return _optional_mcp(settings.mcp_d365_planning_url)


def get_axon_d365_procurement_mcp() -> MCPServerSSE | None:
    """Connect to the Dynamics 365 Procurement MCP server, or None if MCP_D365_PROCUREMENT_URL is unset."""
    return _optional_mcp(settings.mcp_d365_procurement_url)


def get_axon_d365_inventory_mcp() -> MCPServerSSE | None:
    """Connect to the Dynamics 365 Inventory MCP server, or None if MCP_D365_INVENTORY_URL is unset."""
    return _optional_mcp(settings.mcp_d365_inventory_url)


# ─────────────────────────────────────────────────────────────────────────────
# Legacy SQL DB adapter  (set MCP_LEGACY_DB_URL in .env to enable)
# ─────────────────────────────────────────────────────────────────────────────


def get_axon_legacy_db_mcp() -> MCPServerSSE | None:
    """Connect to the Legacy DB MCP server (covers planning+procurement+inventory)."""
    return _optional_mcp(settings.mcp_legacy_db_url)


# ─────────────────────────────────────────────────────────────────────────────
# Custom / bring-your-own ERP adapter  (set MCP_CUSTOM_*_URL in .env to enable)
# ─────────────────────────────────────────────────────────────────────────────


def get_axon_custom_planning_mcp() -> MCPServerSSE | None:
    """Connect to a custom ERP Planning MCP server, or None if MCP_CUSTOM_PLANNING_URL is unset."""
    return _optional_mcp(settings.mcp_custom_planning_url)


def get_axon_custom_procurement_mcp() -> MCPServerSSE | None:
    """Connect to a custom ERP Procurement MCP server, or None if MCP_CUSTOM_PROCUREMENT_URL is unset."""
    return _optional_mcp(settings.mcp_custom_procurement_url)


def get_axon_custom_inventory_mcp() -> MCPServerSSE | None:
    """Connect to a custom ERP Inventory MCP server, or None if MCP_CUSTOM_INVENTORY_URL is unset."""
    return _optional_mcp(settings.mcp_custom_inventory_url)


# ─────────────────────────────────────────────────────────────────────────────
# Oracle NetSuite adapter  (set MCP_NETSUITE_*_URL in .env to enable)
# ─────────────────────────────────────────────────────────────────────────────


def get_axon_netsuite_planning_mcp() -> MCPServerSSE | None:
    """Connect to the NetSuite Planning MCP server, or None if MCP_NETSUITE_PLANNING_URL is unset."""
    return _optional_mcp(settings.mcp_netsuite_planning_url)


def get_axon_netsuite_procurement_mcp() -> MCPServerSSE | None:
    """Connect to the NetSuite Procurement MCP server, or None if MCP_NETSUITE_PROCUREMENT_URL is unset."""
    return _optional_mcp(settings.mcp_netsuite_procurement_url)


def get_axon_netsuite_inventory_mcp() -> MCPServerSSE | None:
    """Connect to the NetSuite Inventory MCP server, or None if MCP_NETSUITE_INVENTORY_URL is unset."""
    return _optional_mcp(settings.mcp_netsuite_inventory_url)


# ─────────────────────────────────────────────────────────────────────────────
# Adapter Registry  — discovers all enabled adapters at runtime
# ─────────────────────────────────────────────────────────────────────────────


class AxonAdapterRegistry:
    """
    Runtime registry of all enabled MCP adapter connections.

    Iterates over every configured ERP adapter and returns only those whose
    URL is set in .env.  Agents that want to work across all connected ERPs
    at once can get the full list from this registry.

    Example::

        registry = AxonAdapterRegistry()

        # Use the first available planning server
        planning_mcp = registry.planning_servers()[0]

        # Pass all enabled planning + procurement servers to an agent
        agent = Agent(model, toolsets=registry.planning_servers() + registry.procurement_servers())
    """

    def planning_servers(self) -> list[MCPServerSSE]:
        """Return all enabled planning MCP servers across all configured ERPs."""
        candidates = [
            get_axon_odoo_planning_mcp(),          # always enabled (has default URL)
            get_axon_sap_planning_mcp(),
            get_axon_ebs_planning_mcp(),
            get_axon_d365_planning_mcp(),
            get_axon_netsuite_planning_mcp(),
            get_axon_legacy_db_mcp(),              # covers all domains
            get_axon_custom_planning_mcp(),
        ]
        return [s for s in candidates if s is not None]

    def procurement_servers(self) -> list[MCPServerSSE]:
        """Return all enabled procurement MCP servers across all configured ERPs."""
        candidates = [
            get_axon_odoo_procurement_mcp(),
            get_axon_sap_procurement_mcp(),
            get_axon_ebs_procurement_mcp(),
            get_axon_d365_procurement_mcp(),
            get_axon_netsuite_procurement_mcp(),
            get_axon_legacy_db_mcp(),
            get_axon_custom_procurement_mcp(),
        ]
        return [s for s in candidates if s is not None]

    def inventory_servers(self) -> list[MCPServerSSE]:
        """Return all enabled inventory MCP servers across all configured ERPs."""
        candidates = [
            get_axon_odoo_inventory_mcp(),
            get_axon_sap_inventory_mcp(),
            get_axon_ebs_inventory_mcp(),
            get_axon_d365_inventory_mcp(),
            get_axon_netsuite_inventory_mcp(),
            get_axon_legacy_db_mcp(),
            get_axon_custom_inventory_mcp(),
        ]
        return [s for s in candidates if s is not None]

    def sales_servers(self) -> list[MCPServerSSE]:
        """Return all enabled Sales & Marketing MCP servers."""
        return [get_axon_odoo_sales_mcp()]

    def logistics_servers(self) -> list[MCPServerSSE]:
        """Return all enabled Logistics & Distribution MCP servers."""
        return [get_axon_odoo_logistics_mcp()]

    def production_servers(self) -> list[MCPServerSSE]:
        """Return all enabled Production Planning MCP servers."""
        return [get_axon_odoo_production_mcp()]

    def pd_servers(self) -> list[MCPServerSSE]:
        """Return all enabled Product Development MCP servers."""
        return [get_axon_odoo_pd_mcp()]

    def maintenance_servers(self) -> list[MCPServerSSE]:
        """Return all enabled Maintenance MCP servers."""
        return [get_axon_odoo_maintenance_mcp()]

    def qa_servers(self) -> list[MCPServerSSE]:
        """Return all enabled QA (Quality Assurance) MCP servers."""
        return [get_axon_odoo_qa_mcp()]

    def qc_servers(self) -> list[MCPServerSSE]:
        """Return all enabled QC (Quality Control) MCP servers."""
        return [get_axon_odoo_qc_mcp()]

    def finance_servers(self) -> list[MCPServerSSE]:
        """Return all enabled Finance MCP servers."""
        return [get_axon_odoo_finance_mcp()]

    def all_servers(self) -> list[MCPServerSSE]:
        """Return every enabled MCP server (deduplicated)."""
        seen: set[str] = set()
        result: list[MCPServerSSE] = []
        for srv in (
            self.planning_servers()
            + self.procurement_servers()
            + self.inventory_servers()
            + self.sales_servers()
            + self.logistics_servers()
            + self.production_servers()
            + self.pd_servers()
            + self.maintenance_servers()
            + self.qa_servers()
            + self.qc_servers()
            + self.finance_servers()
        ):
            url = srv.url  # type: ignore[attr-defined]
            if url not in seen:
                seen.add(url)
                result.append(srv)
        return result

    def enabled_erps(self) -> list[str]:
        """Return names of ERPs that have at least one URL configured."""
        erps: list[str] = ["odoo"]  # always enabled
        if settings.mcp_sap_planning_url or settings.mcp_sap_procurement_url or settings.mcp_sap_inventory_url:
            erps.append("sap")
        if settings.mcp_ebs_planning_url or settings.mcp_ebs_procurement_url or settings.mcp_ebs_inventory_url:
            erps.append("oracle_ebs")
        if settings.mcp_d365_planning_url or settings.mcp_d365_procurement_url or settings.mcp_d365_inventory_url:
            erps.append("dynamics365")
        if settings.mcp_legacy_db_url:
            erps.append("legacy_db")
        if settings.mcp_netsuite_planning_url or settings.mcp_netsuite_procurement_url or settings.mcp_netsuite_inventory_url:
            erps.append("netsuite")
        if settings.mcp_custom_planning_url or settings.mcp_custom_procurement_url or settings.mcp_custom_inventory_url:
            erps.append("custom")
        return erps
