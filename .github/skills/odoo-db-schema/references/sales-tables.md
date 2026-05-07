# Sales & CRM Tables


### `sale_order` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `campaign_id` | `integer` | ✓ | → `utm_campaign` |
| `source_id` | `integer` | ✓ | → `utm_source` |
| `medium_id` | `integer` | ✓ | → `utm_medium` |
| `company_id` | `integer` |  | → `res_company` |
| `partner_id` | `integer` |  | → `res_partner` |
| `pending_email_template_id` | `integer` | ✓ | → `mail_template` |
| `journal_id` | `integer` | ✓ | → `account_journal` |
| `partner_invoice_id` | `integer` |  | → `res_partner` |
| `partner_shipping_id` | `integer` |  | → `res_partner` |
| `fiscal_position_id` | `integer` | ✓ | → `account_fiscal_position` |
| `payment_term_id` | `integer` | ✓ | → `account_payment_term` |
| `preferred_payment_method_line_id` | `integer` | ✓ | → `account_payment_method_line` |
| `pricelist_id` | `integer` | ✓ | → `product_pricelist` |
| `currency_id` | `integer` | ✓ | → `res_currency` |
| `user_id` | `integer` | ✓ | → `res_users` |
| `team_id` | `integer` | ✓ | → `crm_team` |
| `incoterm` | `integer` | ✓ | → `account_incoterms` |
| `analytic_account_id` | `integer` | ✓ | → `account_analytic_account` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `utm_reference` | `character varying` | ✓ |  |
| `access_token` | `character varying` | ✓ |  |
| `name` | `character varying` |  |  |
| `state` | `character varying` | ✓ |  |
| `client_order_ref` | `character varying` | ✓ |  |
| `origin` | `character varying` | ✓ |  |
| `reference` | `character varying` | ✓ |  |
| `signed_by` | `character varying` | ✓ |  |
| `incoterm_location` | `character varying` | ✓ |  |
| `invoice_status` | `character varying` | ✓ |  |
| `delivery_status` | `character varying` | ✓ |  |
| `validity_date` | `date` | ✓ |  |
| `note` | `text` | ✓ |  |
| `currency_rate` | `numeric` | ✓ |  |
| `amount_untaxed` | `numeric` | ✓ |  |
| `amount_tax` | `numeric` | ✓ |  |
| `amount_total` | `numeric` | ✓ |  |
| `locked` | `boolean` | ✓ |  |
| `invoicing_closed` | `boolean` | ✓ |  |
| `require_signature` | `boolean` | ✓ |  |
| `require_payment` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `commitment_date` | `timestamp without time zone` | ✓ |  |
| `date_order` | `timestamp without time zone` |  |  |
| `signed_on` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `prepayment_percent` | `double precision` | ✓ |  |
| `sale_order_template_id` | `integer` | ✓ | → `sale_order_template` |
| `warehouse_id` | `integer` | ✓ | → `stock_warehouse` |
| `picking_policy` | `character varying` |  |  |
| `effective_date` | `timestamp without time zone` | ✓ |  |
| `customizable_pdf_form_fields` | `jsonb` | ✓ |  |
| `amount_unpaid` | `numeric` | ✓ |  |
| `opportunity_id` | `integer` | ✓ | → `crm_lead` |
| `carrier_id` | `integer` | ✓ | → `delivery_carrier` |
| `delivery_message` | `character varying` | ✓ |  |
| `recompute_delivery_price` | `boolean` | ✓ |  |
| `shipping_weight` | `double precision` | ✓ |  |
| `website_id` | `integer` | ✓ | → `website` |
| `shop_warning` | `character varying` | ✓ |  |
| `cart_recovery_email_sent` | `boolean` | ✓ |  |
| `is_rating_email_sent` | `boolean` | ✓ |  |
| `project_id` | `integer` | ✓ | → `project_project` |

### `sale_order_line` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `order_id` | `integer` |  | → `sale_order` |
| `sequence` | `integer` | ✓ |  |
| `company_id` | `integer` | ✓ | → `res_company` |
| `currency_id` | `integer` | ✓ | → `res_currency` |
| `order_partner_id` | `integer` | ✓ | → `res_partner` |
| `salesman_id` | `integer` | ✓ | → `res_users` |
| `product_id` | `integer` | ✓ | → `product_product` |
| `product_uom_id` | `integer` | ✓ | → `uom_uom` |
| `linked_line_id` | `integer` | ✓ | → `sale_order_line` |
| `combo_item_id` | `integer` | ✓ | → `product_combo_item` |
| `customer_lead` | `integer` |  |  |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `state` | `character varying` | ✓ |  |
| `display_type` | `character varying` | ✓ |  |
| `virtual_id` | `character varying` | ✓ |  |
| `linked_virtual_id` | `character varying` | ✓ |  |
| `qty_delivered_method` | `character varying` | ✓ |  |
| `invoice_status` | `character varying` | ✓ |  |
| `analytic_distribution` | `jsonb` | ✓ |  |
| `extra_tax_data` | `jsonb` | ✓ |  |
| `name` | `text` |  |  |
| `product_uom_qty` | `numeric` |  |  |
| `price_unit` | `numeric` |  |  |
| `discount` | `numeric` | ✓ |  |
| `price_subtotal` | `numeric` | ✓ |  |
| `price_total` | `numeric` | ✓ |  |
| `price_reduce_taxexcl` | `numeric` | ✓ |  |
| `price_reduce_taxinc` | `numeric` | ✓ |  |
| `qty_delivered` | `numeric` | ✓ |  |
| `qty_invoiced` | `numeric` | ✓ |  |
| `qty_to_invoice` | `numeric` | ✓ |  |
| `untaxed_amount_invoiced` | `numeric` | ✓ |  |
| `untaxed_amount_to_invoice` | `numeric` | ✓ |  |
| `is_downpayment` | `boolean` | ✓ |  |
| `is_expense` | `boolean` | ✓ |  |
| `collapse_prices` | `boolean` | ✓ |  |
| `collapse_composition` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `technical_price_unit` | `double precision` | ✓ |  |
| `price_tax` | `double precision` | ✓ |  |
| `edi_customer_product_ref` | `character varying` | ✓ |  |
| `is_optional` | `boolean` | ✓ |  |
| `warehouse_id` | `integer` | ✓ | → `stock_warehouse` |
| `event_id` | `integer` | ✓ | → `event_event` |
| `event_slot_id` | `integer` | ✓ | → `event_slot` |
| `event_ticket_id` | `integer` | ✓ | → `event_event_ticket` |
| `is_delivery` | `boolean` | ✓ |  |
| `shop_warning` | `character varying` | ✓ |  |
| `is_service` | `boolean` | ✓ |  |
| `project_id` | `integer` | ✓ | → `project_project` |
| `task_id` | `integer` | ✓ | → `project_task` |

### `crm_lead` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `campaign_id` | `integer` | ✓ | → `utm_campaign` |
| `source_id` | `integer` | ✓ | → `utm_source` |
| `medium_id` | `integer` | ✓ | → `utm_medium` |
| `message_bounce` | `integer` | ✓ |  |
| `user_id` | `integer` | ✓ | → `res_users` |
| `team_id` | `integer` | ✓ | → `crm_team` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `stage_id` | `integer` | ✓ | → `crm_stage` |
| `color` | `integer` | ✓ |  |
| `recurring_plan` | `integer` | ✓ | → `crm_recurring_plan` |
| `partner_id` | `integer` | ✓ | → `res_partner` |
| `lang_id` | `integer` | ✓ | → `res_lang` |
| `state_id` | `integer` | ✓ | → `res_country_state` |
| `country_id` | `integer` | ✓ | → `res_country` |
| `lost_reason_id` | `integer` | ✓ | → `crm_lost_reason` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `utm_reference` | `character varying` | ✓ |  |
| `phone_sanitized` | `character varying` | ✓ |  |
| `email_normalized` | `character varying` | ✓ |  |
| `name` | `character varying` |  |  |
| `referred` | `character varying` | ✓ |  |
| `type` | `character varying` |  |  |
| `priority` | `character varying` | ✓ |  |
| `contact_name` | `character varying` | ✓ |  |
| `partner_name` | `character varying` | ✓ |  |
| `function` | `character varying` | ✓ |  |
| `email_from` | `character varying` | ✓ |  |
| `email_domain_criterion` | `character varying` | ✓ |  |
| `phone` | `character varying` | ✓ |  |
| `phone_state` | `character varying` | ✓ |  |
| `email_state` | `character varying` | ✓ |  |
| `website` | `character varying` | ✓ |  |
| `street` | `character varying` | ✓ |  |
| `street2` | `character varying` | ✓ |  |
| `zip` | `character varying` | ✓ |  |
| `city` | `character varying` | ✓ |  |
| `won_status` | `character varying` | ✓ |  |
| `date_deadline` | `date` | ✓ |  |
| `duration_tracking` | `jsonb` | ✓ |  |
| `lead_properties` | `jsonb` | ✓ |  |
| `description` | `text` | ✓ |  |
| `expected_revenue` | `numeric` | ✓ |  |
| `prorated_revenue` | `numeric` | ✓ |  |
| `recurring_revenue` | `numeric` | ✓ |  |
| `recurring_revenue_monthly` | `numeric` | ✓ |  |
| `recurring_revenue_monthly_prorated` | `numeric` | ✓ |  |
| `recurring_revenue_prorated` | `numeric` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `date_closed` | `timestamp without time zone` | ✓ |  |
| `date_automation_last` | `timestamp without time zone` | ✓ |  |
| `date_open` | `timestamp without time zone` | ✓ |  |
| `date_last_stage_update` | `timestamp without time zone` | ✓ |  |
| `date_conversion` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `day_open` | `double precision` | ✓ |  |
| `day_close` | `double precision` | ✓ |  |
| `probability` | `double precision` | ✓ |  |
| `automated_probability` | `double precision` | ✓ |  |
| `reveal_id` | `character varying` | ✓ |  |
| `iap_enrich_done` | `boolean` | ✓ |  |
| `lead_mining_request_id` | `integer` | ✓ | → `crm_iap_lead_mining_request` |
| `event_lead_rule_id` | `integer` | ✓ | → `event_lead_rule` |
| `event_id` | `integer` | ✓ | → `event_event` |
| `origin_channel_id` | `integer` | ✓ | → `discuss_channel` |
