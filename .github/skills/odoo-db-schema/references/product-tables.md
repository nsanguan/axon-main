# Product Tables


### `product_template` (~154 rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `sequence` | `integer` | ✓ |  |
| `categ_id` | `integer` | ✓ | → `product_category` |
| `uom_id` | `integer` |  | → `uom_uom` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `color` | `integer` | ✓ |  |
| `base_unit_id` | `integer` | ✓ | → `product_base_unit` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `type` | `character varying` |  |  |
| `service_tracking` | `character varying` |  |  |
| `default_code` | `character varying` | ✓ |  |
| `name` | `jsonb` |  |  |
| `description` | `jsonb` | ✓ |  |
| `description_purchase` | `jsonb` | ✓ |  |
| `description_sale` | `jsonb` | ✓ |  |
| `product_properties` | `jsonb` | ✓ |  |
| `list_price` | `numeric` | ✓ |  |
| `volume` | `numeric` | ✓ |  |
| `weight` | `numeric` | ✓ |  |
| `is_storable` | `boolean` | ✓ |  |
| `sale_ok` | `boolean` | ✓ |  |
| `purchase_ok` | `boolean` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `can_image_1024_be_zoomed` | `boolean` | ✓ |  |
| `has_configurable_attributes` | `boolean` | ✓ |  |
| `is_favorite` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `base_unit_count` | `double precision` |  |  |
| `lot_sequence_id` | `integer` | ✓ | → `ir_sequence` |
| `tracking` | `character varying` | ✓ |  |
| `responsible_id` | `jsonb` | ✓ |  |
| `property_stock_production` | `jsonb` | ✓ |  |
| `property_stock_inventory` | `jsonb` | ✓ |  |
| `description_picking` | `jsonb` | ✓ |  |
| `description_pickingout` | `jsonb` | ✓ |  |
| `description_pickingin` | `jsonb` | ✓ |  |
| `property_account_income_id` | `jsonb` | ✓ |  |
| `property_account_expense_id` | `jsonb` | ✓ |  |
| `purchase_method` | `character varying` | ✓ |  |
| `purchase_line_warn_msg` | `text` | ✓ |  |
| `property_price_difference_account_id` | `jsonb` | ✓ |  |
| `lot_valuated` | `boolean` | ✓ |  |
| `service_type` | `character varying` | ✓ |  |
| `reinvoice_policy` | `character varying` | ✓ |  |
| `invoice_policy` | `character varying` |  |  |
| `sale_delay` | `jsonb` | ✓ |  |
| `sale_line_warn_msg` | `text` | ✓ |  |
| `pos_sequence` | `integer` | ✓ |  |
| `public_description` | `jsonb` | ✓ |  |
| `available_in_pos` | `boolean` | ✓ |  |
| `to_weight` | `boolean` | ✓ |  |
| `self_order_available` | `boolean` | ✓ |  |
| `country_of_origin` | `integer` | ✓ | → `res_country` |
| `hs_code` | `character varying` | ✓ |  |
| `variants_default_code` | `character varying` | ✓ |  |
| `website_id` | `integer` | ✓ | → `website` |
| `website_size_x` | `integer` | ✓ |  |
| `website_size_y` | `integer` | ✓ |  |
| `website_ribbon_id` | `integer` | ✓ | → `product_ribbon` |
| `website_sequence` | `integer` | ✓ |  |
| `website_meta_og_img` | `character varying` | ✓ |  |
| `website_meta_title` | `jsonb` | ✓ |  |
| `website_meta_description` | `jsonb` | ✓ |  |
| `website_meta_keywords` | `jsonb` | ✓ |  |
| `seo_name` | `jsonb` | ✓ |  |
| `website_description` | `jsonb` | ✓ |  |
| `description_ecommerce` | `jsonb` | ✓ |  |
| `out_of_stock_message` | `jsonb` | ✓ |  |
| `compare_list_price` | `numeric` | ✓ |  |
| `is_published` | `boolean` | ✓ |  |
| `is_seo_optimized` | `boolean` | ✓ |  |
| `suggest_optional_products` | `boolean` | ✓ |  |
| `suggest_accessory_products` | `boolean` | ✓ |  |
| `suggest_alternative_products` | `boolean` | ✓ |  |
| `allow_out_of_stock_order` | `boolean` | ✓ |  |
| `show_availability` | `boolean` | ✓ |  |
| `publish_on` | `timestamp without time zone` | ✓ |  |
| `published_date` | `timestamp without time zone` | ✓ |  |
| `suggested_products_last_update` | `timestamp without time zone` | ✓ |  |
| `publish_date` | `timestamp without time zone` |  |  |
| `rating_last_value` | `double precision` | ✓ |  |
| `available_threshold` | `double precision` | ✓ |  |
| `can_be_expensed` | `boolean` | ✓ |  |
| `project_id` | `jsonb` | ✓ |  |
| `project_template_id` | `jsonb` | ✓ |  |
| `task_template_id` | `jsonb` | ✓ |  |

### `product_product` (~226 rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `product_tmpl_id` | `integer` |  | → `product_template` |
| `base_unit_id` | `integer` | ✓ | → `product_base_unit` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `default_code` | `character varying` | ✓ |  |
| `barcode` | `character varying` | ✓ |  |
| `combination_indices` | `character varying` | ✓ |  |
| `standard_price` | `jsonb` | ✓ |  |
| `qty_available` | `jsonb` | ✓ |  |
| `lst_price` | `numeric` | ✓ |  |
| `volume` | `numeric` | ✓ |  |
| `weight` | `numeric` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `can_image_variant_1024_be_zoomed` | `boolean` | ✓ |  |
| `is_favorite` | `boolean` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `base_unit_count` | `double precision` |  |  |
| `lot_properties_definition` | `jsonb` | ✓ |  |
| `variant_ribbon_id` | `integer` | ✓ | → `product_ribbon` |

### `product_category` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `parent_id` | `integer` | ✓ | → `product_category` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `parent_path` | `character varying` | ✓ |  |
| `name` | `jsonb` |  |  |
| `product_properties_definition` | `jsonb` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `removal_strategy_id` | `integer` | ✓ | → `product_removal` |
| `packaging_reserve_method` | `character varying` | ✓ |  |
| `property_account_income_categ_id` | `jsonb` | ✓ |  |
| `property_account_expense_categ_id` | `jsonb` | ✓ |  |
| `property_valuation` | `jsonb` | ✓ |  |
| `property_cost_method` | `jsonb` | ✓ |  |
| `property_stock_journal` | `jsonb` | ✓ |  |
| `property_stock_valuation_account_id` | `jsonb` | ✓ |  |
| `property_price_difference_account_id` | `jsonb` | ✓ |  |
| `property_stock_account_production_cost_id` | `jsonb` | ✓ |  |

### `product_pricelist` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `sequence` | `integer` | ✓ |  |
| `currency_id` | `integer` |  | → `res_currency` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `jsonb` |  |  |
| `active` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `website_id` | `integer` | ✓ | → `website` |
| `code` | `character varying` | ✓ |  |
| `selectable` | `boolean` | ✓ |  |
