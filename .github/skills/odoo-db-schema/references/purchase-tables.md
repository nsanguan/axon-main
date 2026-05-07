# Purchase Tables


### `purchase_order` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `partner_id` | `integer` |  | → `res_partner` |
| `dest_address_id` | `integer` | ✓ | → `res_partner` |
| `currency_id` | `integer` |  | → `res_currency` |
| `invoice_count` | `integer` | ✓ |  |
| `fiscal_position_id` | `integer` | ✓ | → `account_fiscal_position` |
| `payment_term_id` | `integer` | ✓ | → `account_payment_term` |
| `incoterm_id` | `integer` | ✓ | → `account_incoterms` |
| `user_id` | `integer` | ✓ | → `res_users` |
| `company_id` | `integer` |  | → `res_company` |
| `reminder_date_before_receipt` | `integer` | ✓ |  |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `access_token` | `character varying` | ✓ |  |
| `name` | `character varying` |  |  |
| `priority` | `character varying` | ✓ |  |
| `origin` | `character varying` | ✓ |  |
| `partner_ref` | `character varying` | ✓ |  |
| `state` | `character varying` | ✓ |  |
| `invoice_status` | `character varying` | ✓ |  |
| `receipt_status` | `character varying` | ✓ |  |
| `note` | `text` | ✓ |  |
| `amount_untaxed` | `numeric` | ✓ |  |
| `amount_tax` | `numeric` | ✓ |  |
| `amount_total` | `numeric` | ✓ |  |
| `amount_total_cc` | `numeric` | ✓ |  |
| `currency_rate` | `numeric` | ✓ |  |
| `locked` | `boolean` | ✓ |  |
| `acknowledged` | `boolean` | ✓ |  |
| `receipt_reminder_email` | `boolean` | ✓ |  |
| `date_order` | `timestamp without time zone` |  |  |
| `date_approve` | `timestamp without time zone` | ✓ |  |
| `date_planned` | `timestamp without time zone` | ✓ |  |
| `date_calendar_start` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `picking_type_id` | `integer` |  | → `stock_picking_type` |
| `incoterm_location` | `character varying` | ✓ |  |
| `effective_date` | `timestamp without time zone` | ✓ |  |
| `date_promised` | `timestamp without time zone` | ✓ |  |
| `project_id` | `integer` | ✓ | → `project_project` |

### `purchase_order_line` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `sequence` | `integer` | ✓ |  |
| `uom_id` | `integer` | ✓ | → `uom_uom` |
| `product_id` | `integer` | ✓ | → `product_product` |
| `order_id` | `integer` |  | → `purchase_order` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `partner_id` | `integer` | ✓ | → `res_partner` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `qty_received_method` | `character varying` | ✓ |  |
| `display_type` | `character varying` | ✓ |  |
| `analytic_distribution` | `jsonb` | ✓ |  |
| `name` | `text` |  |  |
| `product_qty` | `numeric` |  |  |
| `discount` | `numeric` | ✓ |  |
| `price_unit` | `numeric` |  |  |
| `price_unit_product_uom` | `numeric` | ✓ |  |
| `price_subtotal` | `numeric` | ✓ |  |
| `price_total` | `numeric` | ✓ |  |
| `qty_invoiced` | `numeric` | ✓ |  |
| `qty_received` | `numeric` | ✓ |  |
| `qty_received_manual` | `numeric` | ✓ |  |
| `qty_to_invoice` | `numeric` | ✓ |  |
| `is_downpayment` | `boolean` | ✓ |  |
| `date_planned` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `product_uom_qty` | `double precision` | ✓ |  |
| `price_tax` | `double precision` | ✓ |  |
| `non_deductible_tax` | `double precision` | ✓ |  |
| `technical_price_unit` | `double precision` | ✓ |  |
| `orderpoint_id` | `integer` | ✓ | → `stock_warehouse_orderpoint` |
| `location_final_id` | `integer` | ✓ | → `stock_location` |
| `product_description_variants` | `character varying` | ✓ |  |
| `propagate_cancel` | `boolean` | ✓ |  |
| `date_promised` | `timestamp without time zone` | ✓ |  |
| `sale_line_id` | `integer` | ✓ | → `sale_order_line` |
