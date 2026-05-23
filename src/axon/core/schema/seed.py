"""
Axon Seed Data — per-schema sample data.

Usage: .venv/bin/python3 src/axon/core/schema/seed.py
"""

from __future__ import annotations

import asyncio

import asyncpg

from axon.core.config import settings

# =============================================================================
# Per-schema seed data
# =============================================================================

BRAIN_SEED_SQL = """
-- Experience ledger sample
INSERT INTO memory_store (namespace, key, value) VALUES
(
    ARRAY['agent_insights', 'sales'],
    'insight-2026-05-01',
    '{"note": "Boeing order AN4-10A is priority 90 VIP — ensure allocation precedence", "source": "negotiation_round_1", "confidence": 0.95}'
),
(
    ARRAY['agent_insights', 'production'],
    'insight-2026-05-01',
    '{"note": "CNC WC-03 bottleneck at 85% capacity in June. Overtime needed for 2000+ bolts", "source": "capacity_planning", "confidence": 0.82}'
),
(
    ARRAY['agent_insights', 'procurement'],
    'insight-2026-05-01',
    '{"note": "TitaniumMet RM-001 lead time 45 days, 92% reliability. Consider SUP-02 as backup", "source": "supplier_eval", "confidence": 0.78}'
),
(
    ARRAY['plan_history'],
    'plan-2026-05-01',
    '{"approved": true, "deadlock": false, "demand_count": 3, "allocation_count": 3, "negotiation_rounds": 1, "business_weights": {"cost": 0.3, "delivery": 0.3, "quality": 0.2, "sustainability": 0.1, "flexibility": 0.1}}'
),
(
    ARRAY['negotiation_patterns'],
    'pattern-2026-05-01',
    '{"round_count": 1, "resolution": "converged", "key_conflict": "demand_vs_on_hand", "resolution_strategy": "wip_offset", "utility_final": 0.72}'
)
ON CONFLICT DO NOTHING;
"""

AGENTS_SEED_SQL = """
-- Sample negotiation round
INSERT INTO negotiation_rounds (id, round_number, global_utility, resolved, resolution, started_at, completed_at) VALUES
( 'c0000000-0000-0000-0000-000000000001', 1, 0.72, FALSE, NULL,
  '2026-05-08 06:00:00+00', '2026-05-08 06:05:00+00')
ON CONFLICT (id) DO NOTHING;

-- Sample agent proposals
INSERT INTO agent_proposals (id, agent_id, round_number, utility_score, justification, status) VALUES
( 'b0000000-0000-0000-0000-000000000001', 'sales', 1, 0.82,
  'Customer Boeing requires 5000 AN4-10A bolts for June delivery. Priority 90 VIP order.', 'proposed'),
( 'b0000000-0000-0000-0000-000000000002', 'production', 1, 0.78,
  'CNC capacity at 85% in June. Can complete remaining 2000 bolts by 6/25 with overtime.', 'proposed'),
( 'b0000000-0000-0000-0000-000000000003', 'procurement', 1, 0.68,
  'Ti-6Al-4V sheet arriving 6/20 from TitaniumMet. Supplier reliability 92%.', 'proposed')
ON CONFLICT (id) DO NOTHING;

-- Link proposals to allocations (cross-schema: references axon_plan.allocations)
INSERT INTO axon_agents.proposal_allocations (proposal_id, allocation_id) VALUES
('b0000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000001'),
('b0000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000002'),
('b0000000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000003');
"""

PLAN_SEED_SQL = """
-- Sample demands
INSERT INTO demands (id, item_system, item_type, item_native_id, item_name, quantity, period_start, period_end, source, confidence, priority, metadata) VALUES
(
    'd1000000-0000-0000-0000-000000000001', 'oracle_ebs', 'finished_good',
    'FG-001', 'Aircraft Bolt AN4-10A',
    5000, '2026-06-01', '2026-06-30', 'sales_order', 0.95, 90,
    '{"customer": "Boeing", "order_ref": "SO-2026-0421"}'
),
(
    'd1000000-0000-0000-0000-000000000002', 'oracle_ebs', 'raw_material',
    'RM-001', 'Titanium Alloy Ti-6Al-4V Sheet',
    1200, '2026-05-15', '2026-06-15', 'forecast', 0.80, 60,
    '{"thickness_mm": 3.2, "spec": "AMS-4911"}'
),
(
    'd1000000-0000-0000-0000-000000000003', 'oracle_ebs', 'finished_good',
    'FG-002', 'Hydraulic Seal HS-22B',
    800, '2026-07-01', '2026-07-31', 'safety_stock', 0.99, 40,
    '{"location": "WH-01", "min_stock": 200}'
)
ON CONFLICT (id) DO NOTHING;

-- Sample supplies
INSERT INTO supplies (id, item_system, item_type, item_native_id, item_name, quantity, period_start, period_end, source, lead_time_days, location_native_id, location_name, metadata) VALUES
(
    '20000000-0000-0000-0000-000000000001', 'oracle_ebs', 'finished_good',
    'FG-001', 'Aircraft Bolt AN4-10A',
    3000, '2026-05-01', '2026-06-30', 'on_hand', 0, 'WH-01', 'Warehouse A',
    '{"lot": "LOT-2026-0512", "quality": "A"}'
),
(
    '20000000-0000-0000-0000-000000000002', 'oracle_ebs', 'finished_good',
    'FG-001', 'Aircraft Bolt AN4-10A',
    2500, '2026-06-10', '2026-07-10', 'wip', 30, 'WC-03', 'CNC Machining',
    '{"wip_job": "WIP-10234", "status": "in_progress"}'
),
(
    '20000000-0000-0000-0000-000000000003', 'oracle_ebs', 'raw_material',
    'RM-001', 'Titanium Alloy Ti-6Al-4V Sheet',
    1500, '2026-05-20', '2026-06-20', 'purchase_order', 45, 'WH-02', 'Raw Materials',
    '{"po": "PO-2026-0891", "supplier": "TitaniumMet Inc"}'
)
ON CONFLICT (id) DO NOTHING;

-- Sample allocations
INSERT INTO allocations (id, demand_id, supply_id, allocated_quantity, status) VALUES
( 'a1000000-0000-0000-0000-000000000001',
  'd1000000-0000-0000-0000-000000000001',
  '20000000-0000-0000-0000-000000000001', 3000, 'proposed'),
( 'a1000000-0000-0000-0000-000000000002',
  'd1000000-0000-0000-0000-000000000001',
  '20000000-0000-0000-0000-000000000002', 2000, 'proposed'),
( 'a1000000-0000-0000-0000-000000000003',
  'd1000000-0000-0000-0000-000000000002',
  '20000000-0000-0000-0000-000000000003', 1200, 'proposed')
ON CONFLICT (id) DO NOTHING;

"""

MCP_SEED_SQL = """
-- Tool registry
INSERT INTO tool_registry (tool_name, server_name, direction, description) VALUES
('authenticate',              'ebs_auth',     'READ',  'Authenticate and return a session token'),
('validate_session',          'ebs_auth',     'READ',  'Validate an existing session token'),
('refresh_token',             'ebs_auth',     'WRITE', 'Refresh an expiring session token'),
('get_permissions',           'ebs_auth',     'READ',  'Return RBAC permissions for the current session'),
('get_sales_orders',          'ebs_demand',   'READ',  'List open sales orders with item, quantity, customer, date'),
('get_demand_forecast',       'ebs_demand',   'READ',  'Return statistical forecast for items by period'),
('get_available_to_promise',  'ebs_demand',   'READ',  'Return ATP quantity for an item across a date range'),
('get_inventory_levels',      'ebs_supply',   'READ',  'Return on-hand, reserved, and available inventory'),
('get_safety_stock',          'ebs_supply',   'READ',  'Return safety stock targets per item x location'),
('get_storage_capacity',      'ebs_supply',   'READ',  'Return total and available storage capacity'),
('get_inventory_aging',       'ebs_supply',   'READ',  'Return inventory aging breakdown (FIFO layers)'),
('get_suppliers',             'ebs_supply',   'READ',  'Return approved suppliers with lead times and pricing'),
('get_item_costs',            'ebs_supply',   'READ',  'Return standard and actual costs for items'),
('get_purchase_orders',       'ebs_supply',   'READ',  'List open purchase orders'),
('get_supplier_performance',  'ebs_supply',   'READ',  'Return on-time delivery %, quality score, lead time variance'),
('create_purchase_requisition','ebs_supply',  'WRITE','Create a purchase requisition'),
('list_wip_jobs',             'ebs_production','READ', 'List all WIP jobs with status, dates, quantity'),
('get_bom',                   'ebs_production','READ', 'Return bill of materials for an item'),
('get_work_center_capacity',  'ebs_production','READ', 'Return available capacity per work center per period'),
('get_routing',               'ebs_production','READ', 'Return manufacturing routing for an item'),
('reschedule_wip_job',        'ebs_production','WRITE','Update start/end dates of a WIP job'),
('get_item_master',           'ebs_production','READ', 'Return item attributes: make/buy, lead time, lifecycle'),
('get_shipments',             'ebs_logistics','READ', 'List shipments with origin, destination, ETA'),
('get_carrier_rates',         'ebs_logistics','READ', 'Return carrier rate cards by lane'),
('get_transit_times',         'ebs_logistics','READ', 'Return standard transit time per lane'),
('get_delivery_constraints',  'ebs_logistics','READ', 'Return customer delivery windows, dock constraints'),
('create_shipment',           'ebs_logistics','WRITE','Create a shipment record'),
('get_inspection_plan',       'ebs_quality',  'READ',  'Return inspection plan (sampling, criteria) for an item/lot'),
('get_defect_history',        'ebs_quality',  'READ',  'Return defect rate and Pareto by item, operation, period'),
('create_inspection_lot',     'ebs_quality',  'WRITE','Create an inspection lot for a received batch'),
('get_asset_health',          'ebs_asset',    'READ',  'Return current health score, MTBF, next scheduled maintenance'),
('get_maintenance_schedule',  'ebs_asset',    'READ',  'Return preventive and predictive maintenance schedule'),
('get_downtime_history',      'ebs_asset',    'READ',  'Return downtime events with duration, cause, capacity'),
('update_work_center_status', 'ebs_asset',    'WRITE','Update work center status'),
('get_budget',                'ebs_finance',  'READ',  'Return budget allocation per department/cost center'),
('get_gl_accounts',           'ebs_finance',  'READ',  'Return chart of accounts (COGS, inventory, variance)'),
('get_profitability',         'ebs_finance',  'READ',  'Return margin analysis per item/customer/channel'),
('get_engineering_changes',   'ebs_engineering','READ','List ECOs with status and effective dates'),
('get_bom',                   'ebs_production','READ','Return bill of materials for an item'),
('get_warehouse_capacity',    'ebs_warehouse', 'READ', 'Return total and available capacity per warehouse'),
('get_subinventory_levels',   'ebs_warehouse', 'READ', 'Return on-hand quantities per subinventory/locator'),
('get_locator_capacity',      'ebs_warehouse', 'READ', 'Return capacity and utilization per locator'),
('get_picking_rules',         'ebs_warehouse', 'READ', 'Return picking rule assignments'),
('get_putaway_rules',         'ebs_warehouse', 'READ', 'Return putaway rule assignments'),
('get_cycle_count_schedule',  'ebs_warehouse', 'READ', 'Return ABC class cycle count schedule'),
('get_wave_details',          'ebs_warehouse', 'READ', 'Return wave planning details'),
('get_pick_slip_details',     'ebs_warehouse', 'READ', 'Return pick slip line details'),
('get_material_transactions', 'ebs_warehouse', 'READ', 'Return material transaction history'),
('get_receipt_routing',       'ebs_warehouse', 'READ', 'Return receipt routing rules'),
('get_labeling_rules',        'ebs_warehouse', 'READ', 'Return customer/item-specific labeling rules'),
('create_pick_release',       'ebs_warehouse', 'WRITE','Create a pick release for an order'),
('create_cycle_count_entry',  'ebs_warehouse', 'WRITE','Create a cycle count entry'),
('create_subinventory_transfer','ebs_warehouse','WRITE','Transfer material between subinventories'),
('get_sop',                   'llmwiki',       'READ',  'Retrieve Standard Operating Procedure for a process'),
('check_compliance',          'llmwiki',       'READ',  'Verify plan against regulatory and SOP constraints')
ON CONFLICT (tool_name) DO NOTHING;

-- Agent tool assignments
INSERT INTO agent_tool_assignments (agent_id, tool_name) VALUES
('sales',        'get_available_to_promise'), ('sales',        'get_inventory_levels'),
('sales',        'get_sales_orders'),         ('sales',        'get_demand_forecast'),
('sales',        'get_shipments'),
('production',   'list_wip_jobs'),            ('production',   'get_inventory_levels'),
('production',   'get_bom'),                  ('production',   'get_work_center_capacity'),
('procurement',  'get_suppliers'),            ('procurement',  'get_item_costs'),
('warehouse',    'get_inventory_levels'),     ('warehouse',    'get_shipments'),
('logistics',    'get_shipments'),
('finance',      'get_item_costs'),
('qa',           'get_sop'),                  ('qa',           'check_compliance'),
('qc',           'get_sop'),                  ('qc',           'check_compliance'),
('qc',           'list_wip_jobs'),
('pd',           'get_bom'),                  ('pd',           'get_sop'),
('maintenance',  'list_wip_jobs'),            ('maintenance',  'get_sop'),
('maintenance',  'update_work_center_status')
ON CONFLICT (agent_id, tool_name) DO NOTHING;
"""

# -----------------------------------------------------------------------------
# Experience records — planning ledger entries in axon_brain
# (separate from BRAIN_SEED_SQL so the insert order can be controlled)
# -----------------------------------------------------------------------------
EXPERIENCE_RECORDS_SQL = """
INSERT INTO experience_records
    (plan_id, context_snapshot, final_plan, negotiations, tags, plan_confidence, created_at)
VALUES
-- 1. VIP Boeing bolt order — approved, converged round 1
(
    'e1000000-0000-0000-0000-000000000001',
    '{"demands":[{"id":"d1","item":"AN4-10A","quantity":5000,"priority":90,"customer":"Boeing"}],"supplies":[{"id":"s1","item":"AN4-10A","source":"on_hand","quantity":3000},{"id":"s2","item":"AN4-10A","source":"wip","quantity":2500}],"degradation_level":"FULL","business_weights":{"cost":0.3,"delivery":0.3,"quality":0.2,"sustainability":0.1,"flexibility":0.1}}',
    '[{"demand_id":"d1","supply_id":"s1","allocated_quantity":3000,"status":"approved"},{"demand_id":"d1","supply_id":"s2","allocated_quantity":2000,"status":"approved"}]',
    '[{"round_number":1,"global_utility":0.82,"resolved":true,"resolution":"converged"}]',
    ARRAY['approved','vip','boeing','aerospace'],
    0.82,
    '2026-05-08 06:00:00+00'
),
-- 2. Safety stock replenishment — auto-approved, high confidence
(
    'e1000000-0000-0000-0000-000000000002',
    '{"demands":[{"id":"d2","item":"HS-22B","quantity":800,"priority":40}],"supplies":[{"id":"s3","item":"HS-22B","source":"on_hand","quantity":1200}],"degradation_level":"FULL","business_weights":{"cost":0.3,"delivery":0.3,"quality":0.2,"sustainability":0.1,"flexibility":0.1}}',
    '[{"demand_id":"d2","supply_id":"s3","allocated_quantity":800,"status":"approved"}]',
    '[{"round_number":1,"global_utility":0.91,"resolved":true,"resolution":"converged"}]',
    ARRAY['approved','safety_stock','auto_approved'],
    0.91,
    '2026-05-07 14:00:00+00'
),
-- 3. RM-001 titanium shortage — deadlock, HITL required
(
    'e1000000-0000-0000-0000-000000000003',
    '{"demands":[{"id":"d3","item":"RM-001","quantity":1200,"priority":60}],"supplies":[],"degradation_level":"DEGRADED","business_weights":{"cost":0.3,"delivery":0.3,"quality":0.2,"sustainability":0.1,"flexibility":0.1}}',
    '[]',
    '[{"round_number":1,"global_utility":0.43,"resolved":false},{"round_number":2,"global_utility":0.51,"resolved":false},{"round_number":3,"global_utility":0.58,"resolved":false}]',
    ARRAY['deadlock','hitl_required','procurement'],
    0.58,
    '2026-05-06 09:00:00+00'
),
-- 4. Airbus A350 bracket order — approved after 2 rounds
(
    'e1000000-0000-0000-0000-000000000004',
    '{"demands":[{"id":"d4","item":"FR-220","quantity":3200,"priority":85,"customer":"Airbus"}],"supplies":[{"id":"s4","item":"FR-220","source":"on_hand","quantity":1000},{"id":"s5","item":"FR-220","source":"purchase_order","quantity":2500}],"degradation_level":"FULL","business_weights":{"cost":0.25,"delivery":0.35,"quality":0.2,"sustainability":0.1,"flexibility":0.1}}',
    '[{"demand_id":"d4","supply_id":"s4","allocated_quantity":1000,"status":"approved"},{"demand_id":"d4","supply_id":"s5","allocated_quantity":2200,"status":"approved"}]',
    '[{"round_number":1,"global_utility":0.61,"resolved":false,"resolution":null},{"round_number":2,"global_utility":0.79,"resolved":true,"resolution":"converged"}]',
    ARRAY['approved','vip','airbus','aerospace'],
    0.79,
    '2026-05-05 11:30:00+00'
),
-- 5. Quarterly safety stock rebalance — auto-approved, routine
(
    'e1000000-0000-0000-0000-000000000005',
    '{"demands":[{"id":"d5a","item":"OR-55","quantity":500,"priority":30},{"id":"d5b","item":"GK-18","quantity":300,"priority":35},{"id":"d5c","item":"HS-22B","quantity":400,"priority":30}],"supplies":[{"id":"s6","item":"OR-55","source":"on_hand","quantity":700},{"id":"s7","item":"GK-18","source":"on_hand","quantity":450},{"id":"s8","item":"HS-22B","source":"on_hand","quantity":600}],"degradation_level":"FULL","business_weights":{"cost":0.3,"delivery":0.3,"quality":0.2,"sustainability":0.1,"flexibility":0.1}}',
    '[{"demand_id":"d5a","supply_id":"s6","allocated_quantity":500,"status":"approved"},{"demand_id":"d5b","supply_id":"s7","allocated_quantity":300,"status":"approved"},{"demand_id":"d5c","supply_id":"s8","allocated_quantity":400,"status":"approved"}]',
    '[{"round_number":1,"global_utility":0.94,"resolved":true,"resolution":"converged"}]',
    ARRAY['approved','safety_stock','auto_approved','quarterly'],
    0.94,
    '2026-05-03 08:00:00+00'
),
-- 6. WC-02 machine breakdown — partial plan, rejected
(
    'e1000000-0000-0000-0000-000000000006',
    '{"demands":[{"id":"d6","item":"AN4-10A","quantity":2000,"priority":85,"customer":"Boeing"}],"supplies":[{"id":"s9","item":"AN4-10A","source":"wip","quantity":800}],"degradation_level":"PARTIAL","business_weights":{"cost":0.3,"delivery":0.3,"quality":0.2,"sustainability":0.1,"flexibility":0.1}}',
    '[{"demand_id":"d6","supply_id":"s9","allocated_quantity":800,"status":"rejected"}]',
    '[{"round_number":1,"global_utility":0.38,"resolved":false},{"round_number":2,"global_utility":0.42,"resolved":false},{"round_number":3,"global_utility":0.45,"resolved":false},{"round_number":4,"global_utility":0.48,"resolved":false},{"round_number":5,"global_utility":0.49,"resolved":false}]',
    ARRAY['rejected','deadlock','machine_breakdown','boeing'],
    0.49,
    '2026-05-01 07:15:00+00'
),
-- 7. Lockheed Martin hydraulic actuator — approved, expedited
(
    'e1000000-0000-0000-0000-000000000007',
    '{"demands":[{"id":"d7","item":"HA-400","quantity":150,"priority":92,"customer":"Lockheed Martin"}],"supplies":[{"id":"s10","item":"HA-400","source":"purchase_order","quantity":200}],"degradation_level":"FULL","business_weights":{"cost":0.2,"delivery":0.4,"quality":0.2,"sustainability":0.1,"flexibility":0.1}}',
    '[{"demand_id":"d7","supply_id":"s10","allocated_quantity":150,"status":"approved"}]',
    '[{"round_number":1,"global_utility":0.88,"resolved":true,"resolution":"converged"}]',
    ARRAY['approved','vip','lockheed','expedited','aerospace'],
    0.88,
    '2026-04-28 16:45:00+00'
),
-- 8. Raytheon sensor housing — approved, 3 rounds
(
    'e1000000-0000-0000-0000-000000000008',
    '{"demands":[{"id":"d8","item":"SH-700","quantity":75,"priority":80,"customer":"Raytheon"}],"supplies":[{"id":"s11","item":"SH-700","source":"on_hand","quantity":40},{"id":"s12","item":"SH-700","source":"wip","quantity":60}],"degradation_level":"FULL","business_weights":{"cost":0.3,"delivery":0.3,"quality":0.25,"sustainability":0.1,"flexibility":0.05}}',
    '[{"demand_id":"d8","supply_id":"s11","allocated_quantity":40,"status":"approved"},{"demand_id":"d8","supply_id":"s12","allocated_quantity":35,"status":"approved"}]',
    '[{"round_number":1,"global_utility":0.55,"resolved":false},{"round_number":2,"global_utility":0.68,"resolved":false},{"round_number":3,"global_utility":0.76,"resolved":true,"resolution":"converged"}]',
    ARRAY['approved','vip','raytheon','defense'],
    0.76,
    '2026-04-25 10:00:00+00'
),
-- 9. Routine MRO consumables restock — auto-approved, fully automated
(
    'e1000000-0000-0000-0000-000000000009',
    '{"demands":[{"id":"d9a","item":"MRO-001","quantity":1000,"priority":20},{"id":"d9b","item":"MRO-002","quantity":500,"priority":20}],"supplies":[{"id":"s13","item":"MRO-001","source":"purchase_order","quantity":1200},{"id":"s14","item":"MRO-002","source":"on_hand","quantity":600}],"degradation_level":"FULL","business_weights":{"cost":0.4,"delivery":0.25,"quality":0.15,"sustainability":0.1,"flexibility":0.1}}',
    '[{"demand_id":"d9a","supply_id":"s13","allocated_quantity":1000,"status":"approved"},{"demand_id":"d9b","supply_id":"s14","allocated_quantity":500,"status":"approved"}]',
    '[{"round_number":1,"global_utility":0.96,"resolved":true,"resolution":"converged"}]',
    ARRAY['approved','mro','auto_approved','routine'],
    0.96,
    '2026-04-20 09:30:00+00'
),
-- 10. GE Aviation turbine blade demand spike — approved with overtime
(
    'e1000000-0000-0000-0000-000000000010',
    '{"demands":[{"id":"d10","item":"TB-900","quantity":400,"priority":88,"customer":"GE Aviation"}],"supplies":[{"id":"s15","item":"TB-900","source":"on_hand","quantity":120},{"id":"s16","item":"TB-900","source":"wip","quantity":200},{"id":"s17","item":"TB-900","source":"purchase_order","quantity":150}],"degradation_level":"FULL","business_weights":{"cost":0.3,"delivery":0.3,"quality":0.2,"sustainability":0.1,"flexibility":0.1}}',
    '[{"demand_id":"d10","supply_id":"s15","allocated_quantity":120,"status":"approved"},{"demand_id":"d10","supply_id":"s16","allocated_quantity":200,"status":"approved"},{"demand_id":"d10","supply_id":"s17","allocated_quantity":80,"status":"approved"}]',
    '[{"round_number":1,"global_utility":0.57,"resolved":false},{"round_number":2,"global_utility":0.74,"resolved":true,"resolution":"converged"}]',
    ARRAY['approved','vip','ge_aviation','demand_spike','overtime'],
    0.74,
    '2026-04-15 13:00:00+00'
)
ON CONFLICT (plan_id) DO NOTHING;
"""

# -----------------------------------------------------------------------------
# Board schema seed data
# -----------------------------------------------------------------------------
BOARD_SEED_SQL = """
-- Default HITL system config (single row, id=1)
INSERT INTO system_config
    (id, vip_priority_threshold, hitl_delay_days, hitl_cost_threshold,
     hitl_first_n_cycles, auto_approve_confidence, max_negotiation_rounds)
VALUES (1, 80, 7, 50000.00, 5, 0.5, 5)
ON CONFLICT (id) DO NOTHING;

-- Default business weights (single row, id=1)
INSERT INTO business_weights (id, cost, delivery, quality, sustainability, flexibility, updated_by)
VALUES (1, 0.3, 0.3, 0.2, 0.1, 0.1, 'system')
ON CONFLICT (id) DO NOTHING;

-- HITL queue — multiple pending approval scenarios
INSERT INTO hitl_queue
    (plan_id, context_summary, deadlock, demand_count, supply_count,
     agent_proposals, negotiation_rounds, global_utility, requires_approval, reason)
VALUES
(
    'e0000000-0000-0000-0000-000000000001',
    'VIP Boeing order SO-2026-0421 for 5000 AN4-10A bolts. CNC capacity shortage detected. Production agent proposes WC-03 overtime; logistics agent flags 10-day buffer risk.',
    FALSE, 3, 2, 10, 2, 0.65, TRUE,
    'VIP order (priority 90) requires planning manager review'
),
(
    'e0000000-0000-0000-0000-000000000002',
    'WC-02 CNC machine breakdown — estimated 14-day repair. Boeing fastener order SO-2026-0422 (2,000 units) blocked. Re-routing to WC-05 feasible but adds $18,500 overtime cost. Agents deadlocked on cost vs. schedule trade-off after 5 rounds.',
    TRUE, 2, 3, 8, 5, 0.43, TRUE,
    'Agent negotiation deadlock (5 rounds) — delay exceeds 7-day HITL threshold'
),
(
    'e0000000-0000-0000-0000-000000000003',
    'Critical fastener shortage for Airbus A350 frame brackets. Expedited air freight from Osaka supplier costs $72,000. Sea freight alternative saves $48,000 but misses SLA by 12 days. QA agent confirms both options meet AMS-2750 compliance.',
    FALSE, 1, 2, 6, 2, 0.71, TRUE,
    'Cost impact $72,000 exceeds $50,000 HITL threshold — expedited shipping approval required'
),
(
    'e0000000-0000-0000-0000-000000000004',
    'Unexpected 300% demand spike for Hydraulic Seal HS-22B — new Airbus blanket order AX-2026-0189 for 2,400 units by July 15. Current on-hand: 200 units. Procurement agent identified 3 approved suppliers; fastest lead time 28 days. Safety stock will be depleted.',
    FALSE, 3, 1, 7, 3, 0.58, TRUE,
    'New VIP customer (priority 85) in first 5 planning cycles — mandatory review required'
)
ON CONFLICT (plan_id) DO NOTHING;

-- Approval audit trail for completed plans
INSERT INTO approval_audit (plan_id, approved, note, decided_by, decided_at)
VALUES
(
    'e1000000-0000-0000-0000-000000000001',
    TRUE, 'Approved — overtime authorized for CNC WC-03',
    'planning_manager', '2026-05-08 07:00:00+00'
),
(
    'e1000000-0000-0000-0000-000000000002',
    TRUE, 'Auto-approved — safety stock replenishment within policy limits',
    'system', '2026-05-07 14:30:00+00'
);

-- Initial board KPI snapshot
INSERT INTO board_kpis
    (total_plans, pending_approvals, approved_24h, rejected_24h,
     avg_confidence, degradation_level, healthy_server_count)
VALUES (3, 1, 2, 0, 0.77, 'FULL', 5);

-- Board event feed (activity log)
INSERT INTO board_events (event_type, actor, plan_id, detail) VALUES
(
    'plan_approved', 'planning_manager',
    'e1000000-0000-0000-0000-000000000001',
    '{"note": "Overtime authorized for CNC WC-03", "cost_impact": 12500}'
),
(
    'plan_approved', 'system',
    'e1000000-0000-0000-0000-000000000002',
    '{"note": "Auto-approved — safety stock replenishment"}'
),
(
    'hitl_triggered', 'orchestrator',
    'e0000000-0000-0000-0000-000000000001',
    '{"trigger": "vip_order", "priority": 90, "order_ref": "SO-2026-0421"}'
),
(
    'weights_updated', 'planning_manager', NULL,
    '{"old": {"cost": 0.25, "delivery": 0.35}, "new": {"cost": 0.30, "delivery": 0.30}, "reason": "Quarterly rebalance"}'
),
(
    'system_start', 'system', NULL,
    '{"version": "1.0.0", "mode": "production", "agents": 10}'
);
"""


async def seed():
    url = settings.database.url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url, timeout=15)

    schemas_seed = {
        "axon_brain": BRAIN_SEED_SQL,
        "axon_plan": PLAN_SEED_SQL,
        "axon_agents": AGENTS_SEED_SQL,
        "axon_mcp": MCP_SEED_SQL,
        "axon_board": BOARD_SEED_SQL,
    }

    # Order matters: plan first (demands, supplies, allocations),
    # then agents (proposals + proposal_allocations),
    # then mcp, then brain (memory_store only),
    # then brain experience records, then board
    schema_order = ["axon_plan", "axon_agents", "axon_mcp", "axon_brain"]
    for schema_name in schema_order:
        sql = schemas_seed.get(schema_name)
        if not sql:
            continue
        print(f"  Seeding {schema_name}...")
        prefixed = f"SET search_path TO {schema_name};\n\n{sql}"
        try:
            await conn.execute(prefixed)
        except Exception as exc:
            print(f"    ⚠ {exc}")

    # Experience records (axon_brain schema, separate step)
    print("  Seeding axon_brain.experience_records...")
    try:
        await conn.execute(f"SET search_path TO axon_brain;\n\n{EXPERIENCE_RECORDS_SQL}")
    except Exception as exc:
        print(f"    ⚠ experience_records: {exc}")

    # Board schema seed
    print("  Seeding axon_board...")
    try:
        await conn.execute(f"SET search_path TO axon_board;\n\n{BOARD_SEED_SQL}")
    except Exception as exc:
        print(f"    ⚠ axon_board: {exc}")

    # Count summary
    print("\nRow counts:")
    for schema_name in ["axon_brain", "axon_agents", "axon_plan", "axon_mcp", "axon_board"]:
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = $1 AND table_type = 'BASE TABLE' "
            "ORDER BY table_name",
            schema_name,
        )
        for t in tables:
            try:
                count = await conn.fetchval(f"SELECT count(*) FROM {schema_name}.{t['table_name']}")
                print(f"  {schema_name}.{t['table_name']}: {count} rows")
            except Exception:
                pass

    await conn.close()
    print("\nSeed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
