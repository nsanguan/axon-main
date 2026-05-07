# Inventory / Stock Tables


### `stock_picking` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `backorder_id` | `integer` | ✓ | → `stock_picking` |
| `return_id` | `integer` | ✓ | → `stock_picking` |
| `location_id` | `integer` |  | → `stock_location` |
| `location_dest_id` | `integer` |  | → `stock_location` |
| `picking_type_id` | `integer` |  | → `stock_picking_type` |
| `partner_id` | `integer` | ✓ | → `res_partner` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `user_id` | `integer` | ✓ | → `res_users` |
| `owner_id` | `integer` | ✓ | → `res_partner` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `character varying` | ✓ |  |
| `origin` | `character varying` | ✓ |  |
| `move_type` | `character varying` |  |  |
| `state` | `character varying` | ✓ |  |
| `priority` | `character varying` | ✓ |  |
| `picking_properties` | `jsonb` | ✓ |  |
| `note` | `text` | ✓ |  |
| `shipping_weight` | `numeric` | ✓ |  |
| `has_deadline_issue` | `boolean` | ✓ |  |
| `printed` | `boolean` | ✓ |  |
| `is_locked` | `boolean` | ✓ |  |
| `show_return` | `boolean` | ✓ |  |
| `scheduled_date` | `timestamp without time zone` | ✓ |  |
| `date_deadline` | `timestamp without time zone` | ✓ |  |
| `date_done` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `sale_id` | `integer` | ✓ | → `sale_order` |
| `pos_session_id` | `integer` | ✓ | → `pos_session` |
| `pos_order_id` | `integer` | ✓ | → `pos_order` |
| `carrier_id` | `integer` | ✓ | → `delivery_carrier` |
| `carrier_tracking_ref` | `character varying` | ✓ |  |
| `weight` | `numeric` | ✓ |  |
| `carrier_price` | `double precision` | ✓ |  |
| `website_id` | `integer` | ✓ | → `website` |
| `project_id` | `integer` | ✓ | → `project_project` |
| `batch_id` | `integer` | ✓ | → `stock_picking_batch` |
| `batch_sequence` | `integer` | ✓ |  |

### `stock_move` (~191 rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `sequence` | `integer` | ✓ |  |
| `company_id` | `integer` |  | → `res_company` |
| `product_id` | `integer` |  | → `product_product` |
| `uom_id` | `integer` |  | → `uom_uom` |
| `location_id` | `integer` |  | → `stock_location` |
| `location_dest_id` | `integer` |  | → `stock_location` |
| `location_final_id` | `integer` | ✓ | → `stock_location` |
| `partner_id` | `integer` | ✓ | → `res_partner` |
| `picking_id` | `integer` | ✓ | → `stock_picking` |
| `rule_id` | `integer` | ✓ | → `stock_rule` |
| `picking_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `origin_returned_move_id` | `integer` | ✓ | → `stock_move` |
| `restrict_partner_id` | `integer` | ✓ | → `res_partner` |
| `warehouse_id` | `integer` | ✓ | → `stock_warehouse` |
| `next_serial_count` | `integer` | ✓ |  |
| `orderpoint_id` | `integer` | ✓ | → `stock_warehouse_orderpoint` |
| `packaging_uom_id` | `integer` | ✓ | → `uom_uom` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `priority` | `character varying` | ✓ |  |
| `state` | `character varying` | ✓ |  |
| `origin` | `character varying` | ✓ |  |
| `procure_method` | `character varying` |  |  |
| `inventory_name` | `character varying` | ✓ |  |
| `reference` | `character varying` | ✓ |  |
| `next_serial` | `character varying` | ✓ |  |
| `reservation_date` | `date` | ✓ |  |
| `description_picking_manual` | `text` | ✓ |  |
| `product_qty` | `numeric` | ✓ |  |
| `product_uom_qty` | `numeric` |  |  |
| `quantity` | `numeric` | ✓ |  |
| `picked` | `boolean` | ✓ |  |
| `is_scrap` | `boolean` | ✓ |  |
| `propagate_cancel` | `boolean` | ✓ |  |
| `is_inventory` | `boolean` | ✓ |  |
| `additional` | `boolean` | ✓ |  |
| `should_replenish_scrapped` | `boolean` | ✓ |  |
| `date` | `timestamp without time zone` |  |  |
| `date_deadline` | `timestamp without time zone` | ✓ |  |
| `delay_alert_date` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `price_unit` | `double precision` | ✓ |  |
| `packaging_uom_qty` | `double precision` | ✓ |  |
| `account_move_id` | `integer` | ✓ | → `account_move` |
| `value` | `numeric` | ✓ |  |
| `to_refund` | `boolean` | ✓ |  |
| `is_in` | `boolean` | ✓ |  |
| `is_out` | `boolean` | ✓ |  |
| `is_dropship` | `boolean` | ✓ |  |
| `purchase_line_id` | `integer` | ✓ | → `purchase_order_line` |
| `sale_line_id` | `integer` | ✓ | → `sale_order_line` |
| `unit_factor` | `double precision` | ✓ |  |
| `created_production_id` | `integer` | ✓ | → `mrp_production` |
| `production_id` | `integer` | ✓ | → `mrp_production` |
| `raw_material_production_id` | `integer` | ✓ | → `mrp_production` |
| `production_group_id` | `integer` | ✓ | → `mrp_production_group` |
| `unbuild_id` | `integer` | ✓ | → `mrp_unbuild` |
| `consume_unbuild_id` | `integer` | ✓ | → `mrp_unbuild` |
| `operation_id` | `integer` | ✓ | → `mrp_routing_workcenter` |
| `workorder_id` | `integer` | ✓ | → `mrp_workorder` |
| `bom_line_id` | `integer` | ✓ | → `mrp_bom_line` |
| `byproduct_id` | `integer` | ✓ | → `mrp_bom_byproduct` |
| `cost_share` | `numeric` | ✓ |  |
| `weight` | `numeric` | ✓ |  |
| `repair_id` | `integer` | ✓ | → `repair_order` |
| `repair_line_type` | `character varying` | ✓ |  |

### `stock_quant` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `product_id` | `integer` |  | → `product_product` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `location_id` | `integer` |  | → `stock_location` |
| `lot_id` | `integer` | ✓ | → `stock_lot` |
| `package_id` | `integer` | ✓ | → `stock_package` |
| `owner_id` | `integer` | ✓ | → `res_partner` |
| `user_id` | `integer` | ✓ | → `res_users` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `inventory_date` | `date` | ✓ |  |
| `quantity` | `numeric` | ✓ |  |
| `reserved_quantity` | `numeric` |  |  |
| `inventory_quantity` | `numeric` | ✓ |  |
| `inventory_diff_quantity` | `numeric` | ✓ |  |
| `inventory_quantity_set` | `boolean` | ✓ |  |
| `in_date` | `timestamp without time zone` |  |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `accounting_date` | `date` | ✓ |  |

### `stock_location` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `location_id` | `integer` | ✓ | → `stock_location` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `removal_strategy_id` | `integer` | ✓ | → `product_removal` |
| `cyclic_inventory_frequency` | `integer` | ✓ |  |
| `warehouse_id` | `integer` | ✓ | → `stock_warehouse` |
| `storage_category_id` | `integer` | ✓ | → `stock_storage_category` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `character varying` |  |  |
| `complete_name` | `character varying` | ✓ |  |
| `usage` | `character varying` |  |  |
| `parent_path` | `character varying` | ✓ |  |
| `barcode` | `character varying` | ✓ |  |
| `last_inventory_date` | `date` | ✓ |  |
| `next_inventory_date` | `date` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `replenish_location` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `valuation_account_id` | `integer` | ✓ | → `account_account` |

### `stock_warehouse` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `company_id` | `integer` |  | → `res_company` |
| `partner_id` | `integer` | ✓ | → `res_partner` |
| `view_location_id` | `integer` |  | → `stock_location` |
| `lot_stock_id` | `integer` |  | → `stock_location` |
| `wh_input_stock_loc_id` | `integer` | ✓ | → `stock_location` |
| `wh_qc_stock_loc_id` | `integer` | ✓ | → `stock_location` |
| `wh_output_stock_loc_id` | `integer` | ✓ | → `stock_location` |
| `wh_pack_stock_loc_id` | `integer` | ✓ | → `stock_location` |
| `mto_pull_id` | `integer` | ✓ | → `stock_rule` |
| `pick_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `pack_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `out_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `in_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `int_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `qc_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `store_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `xdock_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `reception_route_id` | `integer` | ✓ | → `stock_route` |
| `delivery_route_id` | `integer` | ✓ | → `stock_route` |
| `sequence` | `integer` | ✓ |  |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `character varying` |  |  |
| `code` | `character varying(5)` |  |  |
| `reception_steps` | `character varying` |  |  |
| `delivery_steps` | `character varying` |  |  |
| `active` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `buy_pull_id` | `integer` | ✓ | → `stock_rule` |
| `manufacture_pull_id` | `integer` | ✓ | → `stock_rule` |
| `manufacture_mto_pull_id` | `integer` | ✓ | → `stock_rule` |
| `pbm_mto_pull_id` | `integer` | ✓ | → `stock_rule` |
| `sam_rule_id` | `integer` | ✓ | → `stock_rule` |
| `manu_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `pbm_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `sam_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `pbm_route_id` | `integer` | ✓ | → `stock_route` |
| `pbm_loc_id` | `integer` | ✓ | → `stock_location` |
| `sam_loc_id` | `integer` | ✓ | → `stock_location` |
| `manufacture_steps` | `character varying` |  |  |
| `pos_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `repair_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `repair_mto_pull_id` | `integer` | ✓ | → `stock_rule` |
