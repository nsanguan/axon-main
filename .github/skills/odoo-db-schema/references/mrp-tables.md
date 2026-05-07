# Manufacturing (MRP) Tables


### `mrp_production` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `backorder_sequence` | `integer` | ✓ |  |
| `product_id` | `integer` |  | → `product_product` |
| `production_group_id` | `integer` | ✓ | → `mrp_production_group` |
| `uom_id` | `integer` |  | → `uom_uom` |
| `picking_type_id` | `integer` |  | → `stock_picking_type` |
| `location_src_id` | `integer` |  | → `stock_location` |
| `location_dest_id` | `integer` |  | → `stock_location` |
| `location_final_id` | `integer` | ✓ | → `stock_location` |
| `bom_id` | `integer` | ✓ | → `mrp_bom` |
| `user_id` | `integer` | ✓ | → `res_users` |
| `company_id` | `integer` |  | → `res_company` |
| `orderpoint_id` | `integer` | ✓ | → `stock_warehouse_orderpoint` |
| `production_location_id` | `integer` | ✓ | → `stock_location` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `character varying` | ✓ |  |
| `priority` | `character varying` | ✓ |  |
| `origin` | `character varying` | ✓ |  |
| `state` | `character varying` | ✓ |  |
| `reservation_state` | `character varying` | ✓ |  |
| `product_description_variants` | `character varying` | ✓ |  |
| `note` | `text` | ✓ |  |
| `product_qty` | `numeric` |  |  |
| `qty_producing` | `numeric` | ✓ |  |
| `propagate_cancel` | `boolean` | ✓ |  |
| `is_locked` | `boolean` | ✓ |  |
| `is_planned` | `boolean` | ✓ |  |
| `allow_workorder_dependencies` | `boolean` | ✓ |  |
| `is_outdated_bom` | `boolean` | ✓ |  |
| `date_deadline` | `timestamp without time zone` | ✓ |  |
| `date_start` | `timestamp without time zone` |  |  |
| `previous_date_start` | `timestamp without time zone` | ✓ |  |
| `date_finished` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `product_uom_qty` | `double precision` | ✓ |  |
| `duration_expected` | `double precision` | ✓ |  |
| `duration` | `double precision` | ✓ |  |
| `extra_cost` | `double precision` | ✓ |  |
| `sale_line_id` | `integer` | ✓ | → `sale_order_line` |
| `project_id` | `integer` | ✓ | → `project_project` |

### `mrp_bom` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `product_tmpl_id` | `integer` |  | → `product_template` |
| `product_id` | `integer` | ✓ | → `product_product` |
| `uom_id` | `integer` |  | → `uom_uom` |
| `sequence` | `integer` | ✓ |  |
| `picking_type_id` | `integer` | ✓ | → `stock_picking_type` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `produce_delay` | `integer` | ✓ |  |
| `days_to_prepare_mo` | `integer` | ✓ |  |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `code` | `character varying` | ✓ |  |
| `type` | `character varying` |  |  |
| `ready_to_produce` | `character varying` |  |  |
| `note` | `text` | ✓ |  |
| `product_qty` | `numeric` |  |  |
| `batch_size` | `numeric` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `allow_operation_dependencies` | `boolean` | ✓ |  |
| `enable_batch_size` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `project_id` | `integer` | ✓ | → `project_project` |

### `mrp_bom_line` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `product_id` | `integer` |  | → `product_product` |
| `product_tmpl_id` | `integer` | ✓ | → `product_template` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `uom_id` | `integer` |  | → `uom_uom` |
| `sequence` | `integer` | ✓ |  |
| `bom_id` | `integer` |  | → `mrp_bom` |
| `operation_id` | `integer` | ✓ | → `mrp_routing_workcenter` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `product_qty` | `numeric` |  |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `cost_share` | `numeric` | ✓ |  |
