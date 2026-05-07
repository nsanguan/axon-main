# Point of Sale Tables


### `pos_order` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `user_id` | `integer` | ✓ | → `res_users` |
| `company_id` | `integer` |  | → `res_company` |
| `pricelist_id` | `integer` | ✓ | → `product_pricelist` |
| `partner_id` | `integer` | ✓ | → `res_partner` |
| `sequence_number` | `integer` | ✓ |  |
| `session_id` | `integer` | ✓ | → `pos_session` |
| `config_id` | `integer` | ✓ | → `pos_config` |
| `account_move` | `integer` | ✓ | → `account_move` |
| `preset_id` | `integer` | ✓ | → `pos_preset` |
| `nb_print` | `integer` | ✓ |  |
| `sale_journal` | `integer` | ✓ | → `account_journal` |
| `fiscal_position_id` | `integer` | ✓ | → `account_fiscal_position` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `access_token` | `character varying` | ✓ |  |
| `name` | `character varying` |  |  |
| `last_order_preparation_change` | `character varying` | ✓ |  |
| `state` | `character varying` | ✓ |  |
| `floating_order_name` | `character varying` | ✓ |  |
| `pos_reference` | `character varying` | ✓ |  |
| `ticket_code` | `character varying` | ✓ |  |
| `tracking_number` | `character varying` | ✓ |  |
| `uuid` | `character varying` | ✓ |  |
| `email` | `character varying` | ✓ |  |
| `mobile` | `character varying` | ✓ |  |
| `source` | `character varying` | ✓ |  |
| `general_customer_note` | `text` | ✓ |  |
| `internal_note` | `text` | ✓ |  |
| `amount_difference` | `numeric` | ✓ |  |
| `amount_tax` | `numeric` |  |  |
| `amount_total` | `numeric` |  |  |
| `amount_paid` | `numeric` |  |  |
| `amount_return` | `numeric` |  |  |
| `currency_rate` | `numeric` | ✓ |  |
| `tip_amount` | `numeric` | ✓ |  |
| `is_refund` | `boolean` | ✓ |  |
| `to_invoice` | `boolean` | ✓ |  |
| `is_tipped` | `boolean` | ✓ |  |
| `has_deleted_line` | `boolean` | ✓ |  |
| `defer_invoice_pdf` | `boolean` | ✓ |  |
| `date_order` | `timestamp without time zone` | ✓ |  |
| `preset_time` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `next_online_payment_amount` | `numeric` | ✓ |  |
| `table_id` | `integer` | ✓ | → `restaurant_table` |
| `customer_count` | `integer` | ✓ |  |
| `shipping_date` | `date` | ✓ |  |
| `self_ordering_table_id` | `integer` | ✓ | → `restaurant_table` |
| `table_stand_number` | `character varying` | ✓ |  |
| `use_self_order_online_payment` | `boolean` | ✓ |  |
| `crm_team_id` | `integer` | ✓ | → `crm_team` |
| `employee_id` | `integer` | ✓ | → `hr_employee` |
| `cashier` | `character varying` | ✓ |  |

### `pos_order_line` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `company_id` | `integer` | ✓ | → `res_company` |
| `product_id` | `integer` |  | → `product_product` |
| `order_id` | `integer` |  | → `pos_order` |
| `refunded_orderline_id` | `integer` | ✓ | → `pos_order_line` |
| `combo_parent_id` | `integer` | ✓ | → `pos_order_line` |
| `combo_item_id` | `integer` | ✓ | → `product_combo_item` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `character varying` |  |  |
| `notice` | `character varying` | ✓ |  |
| `price_type` | `character varying` | ✓ |  |
| `full_product_name` | `character varying` | ✓ |  |
| `customer_note` | `character varying` | ✓ |  |
| `uuid` | `character varying` | ✓ |  |
| `note` | `character varying` | ✓ |  |
| `extra_tax_data` | `jsonb` | ✓ |  |
| `price_unit` | `numeric` | ✓ |  |
| `qty` | `numeric` | ✓ |  |
| `price_subtotal` | `numeric` |  |  |
| `price_subtotal_incl` | `numeric` |  |  |
| `total_cost` | `numeric` | ✓ |  |
| `discount` | `numeric` | ✓ |  |
| `is_total_cost_computed` | `boolean` | ✓ |  |
| `is_edited` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `price_extra` | `double precision` | ✓ |  |
| `course_id` | `integer` | ✓ | → `restaurant_order_course` |
| `combo_id` | `integer` | ✓ | → `product_combo` |
| `sale_order_origin_id` | `integer` | ✓ | → `sale_order` |
| `sale_order_line_id` | `integer` | ✓ | → `sale_order_line` |
| `down_payment_details` | `text` | ✓ |  |
| `qty_delivered` | `double precision` | ✓ |  |
| `event_ticket_id` | `integer` | ✓ | → `event_event_ticket` |

### `pos_session` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `config_id` | `integer` |  | → `pos_config` |
| `user_id` | `integer` |  | → `res_users` |
| `cash_journal_id` | `integer` | ✓ | → `account_journal` |
| `move_id` | `integer` | ✓ | → `account_move` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `access_token` | `character varying` | ✓ |  |
| `name` | `character varying` | ✓ |  |
| `state` | `character varying` |  |  |
| `opening_notes` | `text` | ✓ |  |
| `closing_notes` | `text` | ✓ |  |
| `cash_register_balance_end_real` | `numeric` | ✓ |  |
| `cash_register_balance_start` | `numeric` | ✓ |  |
| `cash_real_transaction` | `numeric` | ✓ |  |
| `rescue` | `boolean` | ✓ |  |
| `start_at` | `timestamp without time zone` | ✓ |  |
| `stop_at` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `update_stock_at_closing` | `boolean` | ✓ |  |
| `employee_id` | `integer` | ✓ | → `hr_employee` |
