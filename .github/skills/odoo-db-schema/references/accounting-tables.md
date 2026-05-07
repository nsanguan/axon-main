# Accounting Tables


### `account_move` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `sequence_number` | `integer` | ✓ |  |
| `message_main_attachment_id` | `integer` | ✓ | → `ir_attachment` |
| `journal_id` | `integer` |  | → `account_journal` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `origin_payment_id` | `integer` | ✓ | → `account_payment` |
| `statement_line_id` | `integer` | ✓ | → `account_bank_statement_line` |
| `tax_cash_basis_rec_id` | `integer` | ✓ | → `account_partial_reconcile` |
| `tax_cash_basis_origin_move_id` | `integer` | ✓ | → `account_move` |
| `auto_post_origin_id` | `integer` | ✓ | → `account_move` |
| `secure_sequence_number` | `integer` | ✓ |  |
| `invoice_payment_term_id` | `integer` | ✓ | → `account_payment_term` |
| `partner_id` | `integer` | ✓ | → `res_partner` |
| `commercial_partner_id` | `integer` | ✓ | → `res_partner` |
| `partner_shipping_id` | `integer` | ✓ | → `res_partner` |
| `partner_bank_id` | `integer` | ✓ | → `res_partner_bank` |
| `fiscal_position_id` | `integer` | ✓ | → `account_fiscal_position` |
| `preferred_payment_method_line_id` | `integer` | ✓ | → `account_payment_method_line` |
| `currency_id` | `integer` |  | → `res_currency` |
| `reversed_entry_id` | `integer` | ✓ | → `account_move` |
| `invoice_user_id` | `integer` | ✓ | → `res_users` |
| `invoice_incoterm_id` | `integer` | ✓ | → `account_incoterms` |
| `invoice_cash_rounding_id` | `integer` | ✓ | → `account_cash_rounding` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `sequence_prefix` | `character varying` | ✓ |  |
| `access_token` | `character varying` | ✓ |  |
| `name` | `character varying` | ✓ |  |
| `ref` | `character varying` | ✓ |  |
| `state` | `character varying` |  |  |
| `move_type` | `character varying` |  |  |
| `auto_post` | `character varying` |  |  |
| `review_state` | `character varying` |  |  |
| `inalterable_hash` | `character varying` | ✓ |  |
| `payment_reference` | `character varying` | ✓ |  |
| `qr_code_method` | `character varying` | ✓ |  |
| `payment_state` | `character varying` | ✓ |  |
| `invoice_source_email` | `character varying` | ✓ |  |
| `invoice_partner_display_name` | `character varying` | ✓ |  |
| `invoice_origin` | `character varying` | ✓ |  |
| `incoterm_location` | `character varying` | ✓ |  |
| `date` | `date` |  |  |
| `auto_post_until` | `date` | ✓ |  |
| `invoice_date` | `date` | ✓ |  |
| `invoice_date_due` | `date` | ✓ |  |
| `delivery_date` | `date` | ✓ |  |
| `taxable_supply_date` | `date` | ✓ |  |
| `sending_data` | `jsonb` | ✓ |  |
| `narration` | `text` | ✓ |  |
| `invoice_currency_rate` | `numeric` | ✓ |  |
| `amount_untaxed` | `numeric` | ✓ |  |
| `amount_tax` | `numeric` | ✓ |  |
| `amount_total` | `numeric` | ✓ |  |
| `amount_residual` | `numeric` | ✓ |  |
| `amount_untaxed_signed` | `numeric` | ✓ |  |
| `amount_untaxed_in_currency_signed` | `numeric` | ✓ |  |
| `amount_tax_signed` | `numeric` | ✓ |  |
| `amount_total_signed` | `numeric` | ✓ |  |
| `amount_total_in_currency_signed` | `numeric` | ✓ |  |
| `amount_residual_signed` | `numeric` | ✓ |  |
| `quick_edit_total_amount` | `numeric` | ✓ |  |
| `always_tax_exigible` | `boolean` | ✓ |  |
| `posted_before` | `boolean` | ✓ |  |
| `made_sequence_gap` | `boolean` | ✓ |  |
| `is_manually_modified` | `boolean` | ✓ |  |
| `is_move_sent` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `inventory_closing` | `boolean` | ✓ |  |
| `closing_datetime` | `timestamp without time zone` | ✓ |  |
| `campaign_id` | `integer` | ✓ | → `utm_campaign` |
| `source_id` | `integer` | ✓ | → `utm_source` |
| `medium_id` | `integer` | ✓ | → `utm_medium` |
| `team_id` | `integer` | ✓ | → `crm_team` |
| `utm_reference` | `character varying` | ✓ |  |
| `reversed_pos_order_id` | `integer` | ✓ | → `pos_order` |
| `website_id` | `integer` | ✓ | → `website` |
| `repair_order_id` | `integer` | ✓ | → `repair_order` |

### `account_move_line` (~242 rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `move_id` | `integer` |  | → `account_move` |
| `journal_id` | `integer` | ✓ | → `account_journal` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `company_currency_id` | `integer` | ✓ | → `res_currency` |
| `sequence` | `integer` | ✓ |  |
| `account_id` | `integer` | ✓ | → `account_account` |
| `currency_id` | `integer` |  | → `res_currency` |
| `partner_id` | `integer` | ✓ | → `res_partner` |
| `reconcile_model_id` | `integer` | ✓ | → `account_reconcile_model` |
| `payment_id` | `integer` | ✓ | → `account_payment` |
| `statement_line_id` | `integer` | ✓ | → `account_bank_statement_line` |
| `statement_id` | `integer` | ✓ | → `account_bank_statement` |
| `group_tax_id` | `integer` | ✓ | → `account_tax` |
| `tax_line_id` | `integer` | ✓ | → `account_tax` |
| `tax_group_id` | `integer` | ✓ | → `account_tax_group` |
| `tax_repartition_line_id` | `integer` | ✓ | → `account_tax_repartition_line` |
| `full_reconcile_id` | `integer` | ✓ | → `account_full_reconcile` |
| `product_id` | `integer` | ✓ | → `product_product` |
| `product_uom_id` | `integer` | ✓ | → `uom_uom` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `move_name` | `character varying` | ✓ |  |
| `parent_state` | `character varying` | ✓ |  |
| `ref` | `character varying` | ✓ |  |
| `name` | `character varying` | ✓ |  |
| `matching_number` | `character varying` | ✓ |  |
| `display_type` | `character varying` |  |  |
| `date` | `date` | ✓ |  |
| `invoice_date` | `date` | ✓ |  |
| `date_maturity` | `date` | ✓ |  |
| `discount_date` | `date` | ✓ |  |
| `analytic_distribution` | `jsonb` | ✓ |  |
| `extra_tax_data` | `jsonb` | ✓ |  |
| `debit` | `numeric` | ✓ |  |
| `credit` | `numeric` | ✓ |  |
| `balance` | `numeric` | ✓ |  |
| `amount_currency` | `numeric` | ✓ |  |
| `tax_base_amount` | `numeric` | ✓ |  |
| `amount_residual` | `numeric` | ✓ |  |
| `amount_residual_currency` | `numeric` | ✓ |  |
| `quantity` | `numeric` | ✓ |  |
| `price_unit` | `numeric` | ✓ |  |
| `price_subtotal` | `numeric` | ✓ |  |
| `price_total` | `numeric` | ✓ |  |
| `discount` | `numeric` | ✓ |  |
| `discount_amount_currency` | `numeric` | ✓ |  |
| `discount_balance` | `numeric` | ✓ |  |
| `is_storno` | `boolean` | ✓ |  |
| `is_imported` | `boolean` | ✓ |  |
| `reconciled` | `boolean` | ✓ |  |
| `collapse_composition` | `boolean` | ✓ |  |
| `collapse_prices` | `boolean` | ✓ |  |
| `no_followup` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `deductible_percentage` | `double precision` | ✓ |  |
| `purchase_line_id` | `integer` | ✓ | → `purchase_order_line` |
| `is_downpayment` | `boolean` | ✓ |  |
| `cogs_origin_id` | `integer` | ✓ | → `account_move_line` |
| `expense_id` | `integer` | ✓ | → `hr_expense` |
| `vehicle_id` | `integer` | ✓ | → `fleet_vehicle` |

### `account_account` (~335 rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `currency_id` | `integer` | ✓ | → `res_currency` |
| `parent_id` | `integer` | ✓ | → `account_account` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `account_type` | `character varying` |  |  |
| `parent_path` | `character varying` | ✓ |  |
| `name` | `jsonb` |  |  |
| `description` | `jsonb` | ✓ |  |
| `code_store` | `jsonb` | ✓ |  |
| `note` | `text` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `reconcile` | `boolean` | ✓ |  |
| `non_trade` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `account_stock_variation_id` | `integer` | ✓ | → `account_account` |
| `account_stock_expense_id` | `integer` | ✓ | → `account_account` |
| `is_vehicle_account` | `boolean` | ✓ |  |

### `account_journal` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `alias_id` | `integer` | ✓ | → `mail_alias` |
| `default_account_id` | `integer` | ✓ | → `account_account` |
| `suspense_account_id` | `integer` | ✓ | → `account_account` |
| `non_deductible_account_id` | `integer` | ✓ | → `account_account` |
| `sequence` | `integer` | ✓ |  |
| `currency_id` | `integer` | ✓ | → `res_currency` |
| `company_id` | `integer` |  | → `res_company` |
| `invoice_template_pdf_report_id` | `integer` | ✓ | → `ir_act_report_xml` |
| `profit_account_id` | `integer` | ✓ | → `account_account` |
| `loss_account_id` | `integer` | ✓ | → `account_account` |
| `bank_account_id` | `integer` | ✓ | → `res_partner_bank` |
| `journal_group_id` | `integer` | ✓ | → `account_journal_group` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `color` | `integer` | ✓ |  |
| `access_token` | `character varying` | ✓ |  |
| `code` | `character varying(7)` |  |  |
| `type` | `character varying` |  |  |
| `invoice_reference_type` | `character varying` |  |  |
| `invoice_reference_model` | `character varying` |  |  |
| `bank_statements_source` | `character varying` | ✓ |  |
| `incoming_einvoice_notification_email` | `character varying` | ✓ |  |
| `name` | `jsonb` |  |  |
| `sequence_override_regex` | `text` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `is_self_billing` | `boolean` | ✓ |  |
| `restrict_mode_hash_table` | `boolean` | ✓ |  |
| `refund_sequence` | `boolean` | ✓ |  |
| `payment_sequence` | `boolean` | ✓ |  |
| `show_on_dashboard` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |

### `account_tax` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `company_id` | `integer` |  | → `res_company` |
| `sequence` | `integer` |  |  |
| `tax_group_id` | `integer` |  | → `account_tax_group` |
| `cash_basis_transition_account_id` | `integer` | ✓ | → `account_account` |
| `country_id` | `integer` |  | → `res_country` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `type_tax_use` | `character varying` |  |  |
| `tax_scope` | `character varying` | ✓ |  |
| `amount_type` | `character varying` |  |  |
| `price_include_override` | `character varying` | ✓ |  |
| `tax_exigibility` | `character varying` | ✓ |  |
| `name` | `jsonb` |  |  |
| `description` | `jsonb` | ✓ |  |
| `invoice_label` | `jsonb` | ✓ |  |
| `invoice_legal_notes` | `jsonb` | ✓ |  |
| `amount` | `numeric` |  |  |
| `is_domestic` | `boolean` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `include_base_amount` | `boolean` | ✓ |  |
| `is_base_affected` | `boolean` | ✓ |  |
| `analytic` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `ubl_cii_tax_category_code` | `character varying` | ✓ |  |
| `ubl_cii_tax_exemption_reason` | `character varying` | ✓ |  |
| `ubl_cii_tax_exemption_reason_code` | `character varying` | ✓ |  |
| `withholding_sequence_id` | `integer` | ✓ | → `ir_sequence` |
| `is_withholding_tax_on_payment` | `boolean` | ✓ |  |
| `l10n_th_income_tax_type` | `character varying` | ✓ |  |
| `l10n_th_income_tax_type_others` | `character varying` | ✓ |  |

### `account_payment` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `message_main_attachment_id` | `integer` | ✓ | → `ir_attachment` |
| `move_id` | `integer` | ✓ | → `account_move` |
| `journal_id` | `integer` |  | → `account_journal` |
| `company_id` | `integer` |  | → `res_company` |
| `partner_bank_id` | `integer` | ✓ | → `res_partner_bank` |
| `paired_internal_transfer_payment_id` | `integer` | ✓ | → `account_payment` |
| `payment_method_line_id` | `integer` | ✓ | → `account_payment_method_line` |
| `payment_method_id` | `integer` | ✓ | → `account_payment_method` |
| `currency_id` | `integer` | ✓ | → `res_currency` |
| `partner_id` | `integer` | ✓ | → `res_partner` |
| `outstanding_account_id` | `integer` | ✓ | → `account_account` |
| `destination_account_id` | `integer` | ✓ | → `account_account` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `character varying` | ✓ |  |
| `state` | `character varying` |  |  |
| `transaction_uuid` | `character varying` | ✓ |  |
| `payment_type` | `character varying` |  |  |
| `partner_type` | `character varying` |  |  |
| `memo` | `character varying` | ✓ |  |
| `payment_reference` | `character varying` | ✓ |  |
| `date` | `date` |  |  |
| `amount` | `numeric` | ✓ |  |
| `amount_company_currency_signed` | `numeric` | ✓ |  |
| `is_reconciled` | `boolean` | ✓ |  |
| `is_matched` | `boolean` | ✓ |  |
| `is_sent` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `payment_transaction_id` | `integer` | ✓ | → `payment_transaction` |
| `payment_token_id` | `integer` | ✓ | → `payment_token` |
| `source_payment_id` | `integer` | ✓ | → `account_payment` |
| `should_withhold_tax` | `boolean` | ✓ |  |
| `l10n_th_wth_condition` | `character varying` | ✓ |  |
| `pos_payment_method_id` | `integer` | ✓ | → `pos_payment_method` |
| `force_outstanding_account_id` | `integer` | ✓ | → `account_account` |
| `pos_session_id` | `integer` | ✓ | → `pos_session` |
| `pos_order_id` | `integer` | ✓ | → `pos_order` |

### `account_analytic_account` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `plan_id` | `integer` |  | → `account_analytic_plan` |
| `root_plan_id` | `integer` | ✓ | → `account_analytic_plan` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `partner_id` | `integer` | ✓ | → `res_partner` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `code` | `character varying` | ✓ |  |
| `name` | `jsonb` |  |  |
| `active` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |

### `account_analytic_line` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `account_id` | `integer` | ✓ | → `account_analytic_account` |
| `product_uom_id` | `integer` | ✓ | → `uom_uom` |
| `partner_id` | `integer` | ✓ | → `res_partner` |
| `user_id` | `integer` | ✓ | → `res_users` |
| `company_id` | `integer` |  | → `res_company` |
| `currency_id` | `integer` | ✓ | → `res_currency` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `character varying` | ✓ |  |
| `category` | `character varying` | ✓ |  |
| `date` | `date` |  |  |
| `amount` | `numeric` |  |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `unit_amount` | `double precision` | ✓ |  |
| `x_plan1_id` | `integer` | ✓ | → `account_analytic_account` |
| `x_plan2_id` | `integer` | ✓ | → `account_analytic_account` |
| `x_plan3_id` | `integer` | ✓ | → `account_analytic_account` |
| `product_id` | `integer` | ✓ | → `product_product` |
| `general_account_id` | `integer` | ✓ | → `account_account` |
| `journal_id` | `integer` | ✓ | → `account_journal` |
| `move_line_id` | `integer` | ✓ | → `account_move_line` |
| `code` | `character varying(8)` | ✓ |  |
| `ref` | `character varying` | ✓ |  |
| `order_id` | `integer` | ✓ | → `sale_order` |
| `so_line` | `integer` | ✓ | → `sale_order_line` |
| `reinvoice_move_id` | `integer` | ✓ | → `account_move` |
| `billable_type` | `character varying` | ✓ |  |
| `category_report` | `character varying` | ✓ |  |
