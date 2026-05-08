"""
adapters.mapping — ERP → Axon Universal Schema Mappers.

Re-exports mapper functions from all supported ERP adapters so agents
and orchestrator nodes can do::

    from adapters.mapping.odoo import axon_demand_stream_record_to_item
    from adapters.mapping.sap import axon_sap_demand_row_to_item
    # … etc.

Each sub-module translates raw dict records (from an ERP's MCP tool output)
into Axon universal schema objects (AxonDemandItem, AxonSupplyItem,
AxonAllocation).  Agents only ever see universal schema — never raw ERP dicts.
"""

# Odoo
from adapters.mapping.odoo import (  # noqa: F401
    axon_demand_stream_record_to_item,
    axon_sale_order_line_to_demand_item,
    axon_supply_stream_record_to_item,
    axon_stock_quant_to_supply_item,
    axon_pegging_ledger_to_allocation,
)

# SAP
from adapters.mapping.sap import (  # noqa: F401
    axon_sap_demand_row_to_item,
    axon_sap_supply_row_to_item,
    axon_sap_stock_row_to_item,
    axon_sap_allocation_row_to_allocation,
)

# Oracle EBS
from adapters.mapping.oracle_ebs import (  # noqa: F401
    axon_ebs_demand_row_to_item,
    axon_ebs_po_row_to_item,
    axon_ebs_wip_row_to_item,
    axon_ebs_onhand_row_to_item,
    axon_ebs_requisition_row_to_allocation,
)

# Microsoft Dynamics 365
from adapters.mapping.dynamics365 import (  # noqa: F401
    axon_d365_demand_row_to_item,
    axon_d365_sales_order_line_to_item,
    axon_d365_po_line_to_item,
    axon_d365_production_order_to_item,
    axon_d365_onhand_row_to_item,
    axon_d365_requisition_row_to_allocation,
)

# Legacy SQL DB
from adapters.mapping.legacy_db import (  # noqa: F401
    axon_legacy_demand_row_to_item,
    axon_legacy_supply_row_to_item,
    axon_legacy_stock_row_to_item,
    axon_legacy_allocation_row_to_allocation,
)

# Oracle NetSuite
from adapters.mapping.netsuite import (  # noqa: F401
    axon_netsuite_demand_row_to_item,
    axon_netsuite_supply_row_to_item,
    axon_netsuite_stock_row_to_item,
    axon_netsuite_allocation_row_to_allocation,
)
