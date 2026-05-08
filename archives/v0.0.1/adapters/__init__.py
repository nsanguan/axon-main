"""
adapters — Axon ERP Adapter Layer.

This package bridges ERP-specific systems to the Axon universal schema.
Agents and orchestrator nodes only ever see universal Axon objects
(AxonDemandItem, AxonSupplyItem, AxonAllocation) — never raw ERP data.

Package structure::

    adapters/
        mcp_client.py          — Remote MCP connection factory + AxonAdapterRegistry
        mapping/               — ERP-raw-dict → Axon universal schema mappers
            odoo.py            — Odoo XML-RPC records → Axon schema
            sap.py             — SAP BAPI/RFC records → Axon schema
            oracle_ebs.py      — Oracle EBS SQL rows → Axon schema
            dynamics365.py     — D365 OData entities → Axon schema
            legacy_db.py       — Legacy SQL rows → Axon schema (flexible key resolution)
        odoo/                  — Odoo Protocol implementations (AxonDemandProvider, etc.)
        sap/                   — SAP Protocol implementations
        oracle_ebs/            — Oracle EBS Protocol implementations
        dynamics365/           — Dynamics 365 Protocol implementations
        legacy_db/             — Legacy DB Protocol implementations

To add a new ERP:
  1. Create mcp_servers/<erp>/server.py with axon_<erp>_* tools
  2. Add URL config fields to core/config.py
  3. Add adapter factories to adapters/mcp_client.py
  4. Create adapters/mapping/<erp>.py with mapper functions
  5. Create adapters/<erp>/ with Protocol implementations
  6. Register the ERP in AxonAdapterRegistry
"""
