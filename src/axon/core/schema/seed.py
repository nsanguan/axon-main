"""
Axon Seed Data — sample demands, supplies, allocations, and tool registry.

Usage: .venv/bin/python3 src/axon/core/schema/seed.py
"""

from __future__ import annotations

import asyncio

import asyncpg

from axon.core.config import settings

SEED_SQL = """
-- =============================================================================
-- Tool Registry (13 tools from tools.py)
-- =============================================================================
INSERT INTO tool_registry (tool_name, server_name, direction, description) VALUES
('get_available_to_promise', 'oracle_ebs', 'READ', 'Return ATP quantity for an item across a date range'),
('get_inventory_levels',      'oracle_ebs', 'READ', 'Return on-hand, reserved, and available inventory for items at a location'),
('get_sales_orders',          'oracle_ebs', 'READ', 'List open sales orders with item, quantity, customer, date'),
('get_demand_forecast',       'oracle_ebs', 'READ', 'Return statistical forecast for items by period'),
('list_wip_jobs',             'oracle_ebs', 'READ', 'List all WIP jobs with status, dates, quantity'),
('get_bom',                   'oracle_ebs', 'READ', 'Return bill of materials for an item'),
('get_work_center_capacity',  'oracle_ebs', 'READ', 'Return available capacity per work center per period'),
('get_suppliers',             'oracle_ebs', 'READ', 'Return approved suppliers with lead times and pricing'),
('get_item_costs',            'oracle_ebs', 'READ', 'Return standard and actual costs for items'),
('get_shipments',             'oracle_ebs', 'READ', 'List shipments with origin, destination, ETA'),
('get_sop',                   'external_rag', 'READ', 'Retrieve Standard Operating Procedure for a process'),
('check_compliance',          'external_rag', 'READ', 'Verify plan against regulatory and SOP constraints'),
('update_work_center_status', 'oracle_ebs', 'WRITE', 'Update work center status (available, maintenance, down)')
ON CONFLICT (tool_name) DO NOTHING;

-- Agent ↔ Tool assignments
INSERT INTO agent_tool_assignments (agent_id, tool_name) VALUES
('sales',        'get_available_to_promise'),
('sales',        'get_inventory_levels'),
('sales',        'get_sales_orders'),
('sales',        'get_demand_forecast'),
('sales',        'get_shipments'),
('production',   'list_wip_jobs'),
('production',   'get_inventory_levels'),
('production',   'get_bom'),
('production',   'get_work_center_capacity'),
('procurement',  'get_suppliers'),
('procurement',  'get_item_costs'),
('warehouse',    'get_inventory_levels'),
('warehouse',    'get_shipments'),
('logistics',    'get_shipments'),
('finance',      'get_item_costs'),
('qa',           'get_sop'),
('qa',           'check_compliance'),
('qc',           'get_sop'),
('qc',           'check_compliance'),
('qc',           'list_wip_jobs'),
('pd',           'get_bom'),
('pd',           'get_sop'),
('maintenance',  'list_wip_jobs'),
('maintenance',  'get_sop'),
('maintenance',  'update_work_center_status')
ON CONFLICT (agent_id, tool_name) DO NOTHING;

-- =============================================================================
-- Sample Demands
-- =============================================================================
INSERT INTO demands (id, item_system, item_type, item_native_id, item_name, quantity, period_start, period_end, source, confidence, priority, metadata) VALUES
(
    'd1000000-0000-0000-0000-000000000001', 'oracle_ebs', 'finished_good',
    'FG-001', 'Aircraft Bolt AN4-10A',
    5000, '2026-06-01', '2026-06-30', 'sales_order', 0.95, 90,
    '{"customer": "Boeing", "order_ref": "SO-2026-0421", "color": "silver", "grade": "aerospace"}'
),
(
    'd1000000-0000-0000-0000-000000000002', 'oracle_ebs', 'raw_material',
    'RM-001', 'Titanium Alloy Ti-6Al-4V Sheet',
    1200, '2026-05-15', '2026-06-15', 'forecast', 0.80, 60,
    '{"thickness_mm": 3.2, "width_cm": 120, "spec": "AMS-4911"}'
),
(
    'd1000000-0000-0000-0000-000000000003', 'oracle_ebs', 'finished_good',
    'FG-002', 'Hydraulic Seal HS-22B',
    800, '2026-07-01', '2026-07-31', 'safety_stock', 0.99, 40,
    '{"location": "WH-01", "min_stock": 200, "max_stock": 1000}'
);

-- =============================================================================
-- Sample Supplies
-- =============================================================================
INSERT INTO supplies (id, item_system, item_type, item_native_id, item_name, quantity, period_start, period_end, source, lead_time_days, location_system, location_type, location_native_id, location_name, metadata) VALUES
(
    '20000000-0000-0000-0000-000000000001', 'oracle_ebs', 'finished_good',
    'FG-001', 'Aircraft Bolt AN4-10A',
    3000, '2026-05-01', '2026-06-30', 'on_hand', 0,
    'oracle_ebs', 'warehouse', 'WH-01', 'Warehouse A',
    '{"lot": "LOT-2026-0512", "quality": "A"}'
),
(
    '20000000-0000-0000-0000-000000000002', 'oracle_ebs', 'finished_good',
    'FG-001', 'Aircraft Bolt AN4-10A',
    2500, '2026-06-10', '2026-07-10', 'wip', 30,
    'oracle_ebs', 'work_center', 'WC-03', 'CNC Machining',
    '{"wip_job": "WIP-10234", "status": "in_progress"}'
),
(
    '20000000-0000-0000-0000-000000000003', 'oracle_ebs', 'raw_material',
    'RM-001', 'Titanium Alloy Ti-6Al-4V Sheet',
    1500, '2026-05-20', '2026-06-20', 'purchase_order', 45,
    'oracle_ebs', 'warehouse', 'WH-02', 'Raw Materials',
    '{"po": "PO-2026-0891", "supplier": "TitaniumMet Inc", "reliability": 0.92}'
);

-- =============================================================================
-- Sample Allocations (pegging)
-- =============================================================================
INSERT INTO allocations (id, demand_id, supply_id, allocated_quantity, status, violation_alert, violation_severity, agent_action) VALUES
(
    'a1000000-0000-0000-0000-000000000001',
    'd1000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000001',
    3000, 'proposed', FALSE, NULL, 'none'
),
(
    'a1000000-0000-0000-0000-000000000002',
    'd1000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000002',
    2000, 'proposed', FALSE, NULL, 'none'
),
(
    'a1000000-0000-0000-0000-000000000003',
    'd1000000-0000-0000-0000-000000000002',
    '20000000-0000-0000-0000-000000000003',
    1200, 'proposed', FALSE, NULL, 'none'
);

-- =============================================================================
-- Sample Negotiation Round
-- =============================================================================
INSERT INTO negotiation_rounds (id, round_number, global_utility, resolved, resolution, started_at, completed_at) VALUES
(
    'c0000000-0000-0000-0000-000000000001',
    1, 0.72, FALSE, NULL,
    '2026-05-08 06:00:00+00',
    '2026-05-08 06:05:00+00'
);

-- =============================================================================
-- Sample Agent Proposals
-- =============================================================================
INSERT INTO agent_proposals (id, agent_id, round_number, utility_score, justification, status) VALUES
(
    'b0000000-0000-0000-0000-000000000001',
    'sales', 1, 0.82,
    'Customer Boeing requires 5000 AN4-10A bolts for June delivery. Priority 90 VIP order.',
    'proposed'
),
(
    'b0000000-0000-0000-0000-000000000002',
    'production', 1, 0.78,
    'CNC capacity at 85% in June. Can complete remaining 2000 bolts by 6/25 with overtime.',
    'proposed'
),
(
    'b0000000-0000-0000-0000-000000000003',
    'procurement', 1, 0.68,
    'Ti-6Al-4V sheet arriving 6/20 from TitaniumMet. Supplier reliability 92%.',
    'proposed'
);

-- Link proposals to allocations
INSERT INTO proposal_allocations (proposal_id, allocation_id) VALUES
('b0000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001'),
('b0000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000002'),
('b0000000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000003');
"""


async def seed():
    url = settings.database.url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url, timeout=15)

    print("Inserting seed data...")
    await conn.execute(SEED_SQL)

    # Counts
    for table in [
        "demands",
        "supplies",
        "allocations",
        "agent_proposals",
        "negotiation_rounds",
        "tool_registry",
        "agent_tool_assignments",
    ]:
        count = await conn.fetchval(f"SELECT count(*) FROM {table}")
        print(f"  ✓ {table}: {count} rows")

    await conn.close()
    print("\nSeed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
