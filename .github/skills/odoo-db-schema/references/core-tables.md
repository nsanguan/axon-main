# Core / Base Tables


### `res_partner` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `company_id` | `integer` | ✓ | → `res_company` |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `name` | `character varying` | ✓ |  |
| `parent_id` | `integer` | ✓ | → `res_partner` |
| `user_id` | `integer` | ✓ | → `res_users` |
| `state_id` | `integer` | ✓ | → `res_country_state` |
| `country_id` | `integer` | ✓ | → `res_country` |
| `industry_id` | `integer` | ✓ | → `res_partner_industry` |
| `color` | `integer` | ✓ |  |
| `commercial_partner_id` | `integer` | ✓ | → `res_partner` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `complete_name` | `character varying` | ✓ |  |
| `ref` | `character varying` | ✓ |  |
| `lang` | `character varying` | ✓ |  |
| `tz` | `character varying` | ✓ |  |
| `vat` | `character varying` | ✓ |  |
| `company_registry` | `character varying` | ✓ |  |
| `website` | `character varying` | ✓ |  |
| `function` | `character varying` | ✓ |  |
| `type` | `character varying` | ✓ |  |
| `street` | `character varying` | ✓ |  |
| `street2` | `character varying` | ✓ |  |
| `zip` | `character varying` | ✓ |  |
| `city` | `character varying` | ✓ |  |
| `email` | `character varying` | ✓ |  |
| `phone` | `character varying` | ✓ |  |
| `commercial_company_name` | `character varying` | ✓ |  |
| `properties` | `jsonb` | ✓ |  |
| `barcode` | `jsonb` | ✓ |  |
| `comment` | `text` | ✓ |  |
| `partner_latitude` | `numeric` | ✓ |  |
| `partner_longitude` | `numeric` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `employee` | `boolean` | ✓ |  |
| `is_company` | `boolean` | ✓ |  |
| `partner_share` | `boolean` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `message_bounce` | `integer` | ✓ |  |
| `email_normalized` | `character varying` | ✓ |  |
| `signup_type` | `character varying` | ✓ |  |
| `phone_sanitized` | `character varying` | ✓ |  |
| `specific_property_product_pricelist` | `jsonb` | ✓ |  |
| `property_stock_customer` | `jsonb` | ✓ |  |
| `property_stock_supplier` | `jsonb` | ✓ |  |
| `picking_warn_msg` | `text` | ✓ |  |
| `invoice_template_pdf_report_id` | `integer` | ✓ | → `ir_act_report_xml` |
| `supplier_rank` | `integer` | ✓ |  |
| `customer_rank` | `integer` | ✓ |  |
| `autopost_bills` | `character varying` |  |  |
| `credit_limit` | `jsonb` | ✓ |  |
| `property_account_payable_id` | `jsonb` | ✓ |  |
| `property_account_receivable_id` | `jsonb` | ✓ |  |
| `property_account_position_id` | `jsonb` | ✓ |  |
| `property_payment_term_id` | `jsonb` | ✓ |  |
| `property_supplier_payment_term_id` | `jsonb` | ✓ |  |
| `trust` | `jsonb` | ✓ |  |
| `ignore_abnormal_invoice_date` | `jsonb` | ✓ |  |
| `ignore_abnormal_invoice_amount` | `jsonb` | ✓ |  |
| `additional_identifiers` | `jsonb` | ✓ |  |
| `invoice_sending_method` | `jsonb` | ✓ |  |
| `invoice_edi_format_store` | `jsonb` | ✓ |  |
| `property_outbound_payment_method_line_id` | `jsonb` | ✓ |  |
| `property_inbound_payment_method_line_id` | `jsonb` | ✓ |  |
| `peppol_endpoint` | `character varying` | ✓ |  |
| `peppol_eas` | `character varying` | ✓ |  |
| `buyer_id` | `integer` | ✓ | → `res_users` |
| `property_purchase_currency_id` | `jsonb` | ✓ |  |
| `receipt_reminder_email` | `jsonb` | ✓ |  |
| `reminder_date_before_receipt` | `jsonb` | ✓ |  |
| `purchase_warn_msg` | `text` | ✓ |  |
| `l10n_th_title` | `character varying` | ✓ |  |
| `l10n_th_company_type` | `character varying` | ✓ |  |
| `suggest_days` | `integer` | ✓ |  |
| `suggest_percent` | `integer` | ✓ |  |
| `suggest_based_on` | `character varying` | ✓ |  |
| `group_rfq` | `character varying` |  |  |
| `group_on` | `character varying` |  |  |
| `incoterm_id` | `integer` | ✓ | → `account_incoterms` |
| `incoterm_location` | `character varying` | ✓ |  |
| `sale_warn_msg` | `text` | ✓ |  |
| `date_localization` | `date` | ✓ |  |
| `calendar_last_notif_ack` | `timestamp without time zone` | ✓ |  |
| `website_id` | `integer` | ✓ | → `website` |
| `is_published` | `boolean` | ✓ |  |
| `publish_on` | `timestamp without time zone` | ✓ |  |
| `published_date` | `timestamp without time zone` | ✓ |  |
| `website_meta_og_img` | `character varying` | ✓ |  |
| `website_meta_title` | `jsonb` | ✓ |  |
| `website_meta_description` | `jsonb` | ✓ |  |
| `website_meta_keywords` | `jsonb` | ✓ |  |
| `seo_name` | `jsonb` | ✓ |  |
| `website_description` | `jsonb` | ✓ |  |
| `website_short_description` | `jsonb` | ✓ |  |
| `is_seo_optimized` | `boolean` | ✓ |  |
| `property_delivery_carrier_id` | `jsonb` | ✓ |  |
| `pickup_location_data` | `jsonb` | ✓ |  |
| `pickup_delivery_method_id` | `integer` | ✓ | → `delivery_carrier` |

### `res_users` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `company_id` | `integer` |  | → `res_company` |
| `partner_id` | `integer` |  | → `res_partner` |
| `active` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `login` | `character varying` |  |  |
| `password` | `character varying` | ✓ |  |
| `action_id` | `integer` | ✓ |  |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `signature` | `text` | ✓ |  |
| `share` | `boolean` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `totp_last_counter` | `integer` | ✓ |  |
| `totp_secret` | `character varying` | ✓ |  |
| `tour_enabled` | `boolean` | ✓ |  |
| `notification_type` | `character varying` |  |  |
| `manual_im_status` | `character varying` | ✓ |  |
| `out_of_office_message` | `text` | ✓ |  |
| `out_of_office_from` | `timestamp without time zone` | ✓ |  |
| `out_of_office_to` | `timestamp without time zone` | ✓ |  |
| `odoobot_state` | `character varying` | ✓ |  |
| `odoobot_failed` | `boolean` | ✓ |  |
| `sale_team_id` | `integer` | ✓ | → `crm_team` |
| `property_warehouse_id` | `jsonb` | ✓ |  |
| `website_id` | `integer` | ✓ | → `website` |
| `last_lunch_location_id` | `integer` | ✓ | → `lunch_location` |
| `karma` | `integer` | ✓ |  |
| `rank_id` | `integer` | ✓ | → `gamification_karma_rank` |
| `next_rank_id` | `integer` | ✓ | → `gamification_karma_rank` |

### `res_company` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `name` | `character varying` |  |  |
| `partner_id` | `integer` |  | → `res_partner` |
| `currency_id` | `integer` |  | → `res_currency` |
| `sequence` | `integer` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `parent_path` | `character varying` | ✓ |  |
| `parent_id` | `integer` | ✓ | → `res_company` |
| `paperformat_id` | `integer` | ✓ | → `report_paperformat` |
| `external_report_layout_id` | `integer` | ✓ | → `ir_ui_view` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `email` | `character varying` | ✓ |  |
| `phone` | `character varying` | ✓ |  |
| `report_tables_id` | `character varying` | ✓ |  |
| `font` | `character varying` | ✓ |  |
| `primary_color` | `character varying` | ✓ |  |
| `secondary_color` | `character varying` | ✓ |  |
| `report_header` | `jsonb` | ✓ |  |
| `report_footer` | `jsonb` | ✓ |  |
| `company_details` | `jsonb` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `uses_default_logo` | `boolean` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `nomenclature_id` | `integer` | ✓ | → `barcode_nomenclature` |
| `resource_calendar_id` | `integer` | ✓ | → `resource_calendar` |
| `tz` | `character varying` |  |  |
| `alias_domain_id` | `integer` | ✓ | → `mail_alias_domain` |
| `email_primary_color` | `character varying` | ✓ |  |
| `email_secondary_color` | `character varying` | ✓ |  |
| `iap_enrich_auto_done` | `boolean` | ✓ |  |
| `snailmail_color` | `boolean` | ✓ |  |
| `snailmail_cover` | `boolean` | ✓ |  |
| `snailmail_duplex` | `boolean` | ✓ |  |
| `internal_transit_location_id` | `integer` | ✓ | → `stock_location` |
| `stock_mail_confirmation_template_id` | `integer` | ✓ | → `mail_template` |
| `annual_inventory_day` | `integer` | ✓ |  |
| `horizon_days` | `integer` |  |  |
| `annual_inventory_month` | `character varying` | ✓ |  |
| `stock_confirmation_type` | `character varying` | ✓ |  |
| `picking_policy` | `character varying` |  |  |
| `stock_move_email_validation` | `boolean` | ✓ |  |
| `stock_text_confirmation` | `boolean` | ✓ |  |
| `stock_sms_confirmation_template_id` | `integer` | ✓ | → `sms_template` |
| `has_received_warning_stock_sms` | `boolean` | ✓ |  |
| `pay_now_label` | `jsonb` | ✓ |  |
| `pay_later_label` | `jsonb` | ✓ |  |
| `fiscalyear_last_day` | `integer` |  |  |
| `transfer_account_id` | `integer` | ✓ | → `account_account` |
| `default_cash_difference_income_account_id` | `integer` | ✓ | → `account_account` |
| `default_cash_difference_expense_account_id` | `integer` | ✓ | → `account_account` |
| `account_journal_suspense_account_id` | `integer` | ✓ | → `account_account` |
| `account_journal_early_pay_discount_gain_account_id` | `integer` | ✓ | → `account_account` |
| `account_journal_early_pay_discount_loss_account_id` | `integer` | ✓ | → `account_account` |
| `account_sale_tax_id` | `integer` | ✓ | → `account_tax` |
| `account_purchase_tax_id` | `integer` | ✓ | → `account_tax` |
| `account_purchase_receipt_fiscal_position_id` | `integer` | ✓ | → `account_fiscal_position` |
| `currency_exchange_journal_id` | `integer` | ✓ | → `account_journal` |
| `income_currency_exchange_account_id` | `integer` | ✓ | → `account_account` |
| `expense_currency_exchange_account_id` | `integer` | ✓ | → `account_account` |
| `incoterm_id` | `integer` | ✓ | → `account_incoterms` |
| `batch_payment_sequence_id` | `integer` | ✓ | → `ir_sequence` |
| `account_opening_move_id` | `integer` | ✓ | → `account_move` |
| `account_default_pos_receivable_account_id` | `integer` | ✓ | → `account_account` |
| `expense_accrual_account_id` | `integer` | ✓ | → `account_account` |
| `revenue_accrual_account_id` | `integer` | ✓ | → `account_account` |
| `automatic_entry_default_journal_id` | `integer` | ✓ | → `account_journal` |
| `domestic_fiscal_position_id` | `integer` | ✓ | → `account_fiscal_position` |
| `account_fiscal_country_id` | `integer` | ✓ | → `res_country` |
| `tax_cash_basis_journal_id` | `integer` | ✓ | → `account_journal` |
| `account_cash_basis_base_account_id` | `integer` | ✓ | → `account_account` |
| `account_discount_income_allocation_id` | `integer` | ✓ | → `account_account` |
| `account_discount_expense_allocation_id` | `integer` | ✓ | → `account_account` |
| `price_difference_account_id` | `integer` | ✓ | → `account_account` |
| `fiscalyear_last_month` | `character varying` |  |  |
| `chart_template` | `character varying` | ✓ |  |
| `bank_account_code_prefix` | `character varying` | ✓ |  |
| `cash_account_code_prefix` | `character varying` | ✓ |  |
| `transfer_account_code_prefix` | `character varying` | ✓ |  |
| `tax_calculation_rounding_method` | `character varying` | ✓ |  |
| `terms_type` | `character varying` | ✓ |  |
| `quick_edit_mode` | `character varying` | ✓ |  |
| `account_price_include` | `character varying` |  |  |
| `fiscalyear_lock_date` | `date` | ✓ |  |
| `tax_lock_date` | `date` | ✓ |  |
| `sale_lock_date` | `date` | ✓ |  |
| `purchase_lock_date` | `date` | ✓ |  |
| `hard_lock_date` | `date` | ✓ |  |
| `account_opening_date` | `date` | ✓ |  |
| `invoice_terms` | `jsonb` | ✓ |  |
| `invoice_terms_html` | `jsonb` | ✓ |  |
| `expects_chart_of_accounts` | `boolean` | ✓ |  |
| `anglo_saxon_accounting` | `boolean` | ✓ |  |
| `qr_code` | `boolean` | ✓ |  |
| `link_qr_code` | `boolean` | ✓ |  |
| `display_invoice_amount_total_words` | `boolean` | ✓ |  |
| `display_invoice_tax_company_currency` | `boolean` | ✓ |  |
| `account_use_credit_limit` | `boolean` | ✓ |  |
| `tax_exigibility` | `boolean` | ✓ |  |
| `account_storno` | `boolean` | ✓ |  |
| `quick_edit_mode_enabled` | `boolean` | ✓ |  |
| `document_sequence_editable` | `boolean` | ✓ |  |
| `set_to_review_documents` | `boolean` | ✓ |  |
| `restrictive_audit_trail` | `boolean` | ✓ |  |
| `autopost_bills` | `boolean` | ✓ |  |
| `withholding_tax_base_account_id` | `integer` | ✓ | → `account_account` |
| `po_lock` | `character varying` | ✓ |  |
| `po_double_validation` | `character varying` | ✓ |  |
| `po_double_validation_amount` | `numeric` | ✓ |  |
| `account_production_wip_account_id` | `integer` | ✓ | → `account_account` |
| `account_production_wip_overhead_account_id` | `integer` | ✓ | → `account_account` |
| `inventory_period` | `character varying` |  |  |
| `days_to_purchase` | `integer` | ✓ |  |
| `quotation_validity_days` | `integer` | ✓ |  |
| `sale_discount_product_id` | `integer` | ✓ | → `product_product` |
| `downpayment_account_id` | `integer` | ✓ | → `account_account` |
| `sale_onboarding_payment_method` | `character varying` | ✓ |  |
| `portal_confirmation_sign` | `boolean` | ✓ |  |
| `portal_confirmation_pay` | `boolean` | ✓ |  |
| `display_product_images_on_so` | `boolean` | ✓ |  |
| `prepayment_percent` | `double precision` | ✓ |  |
| `sale_order_template_id` | `integer` | ✓ | → `sale_order_template` |
| `security_lead` | `integer` |  |  |
| `point_of_sale_ticket_portal_url_display_mode` | `character varying` |  |  |
| `point_of_sale_use_ticket_qr_code` | `boolean` | ✓ |  |
| `point_of_sale_ticket_unique_code` | `boolean` | ✓ |  |
| `point_of_sale_update_stock_quantities` | `character varying` | ✓ |  |
| `hr_presence_control_email_amount` | `integer` | ✓ |  |
| `contract_expiration_notice_period` | `integer` | ✓ |  |
| `work_permit_expiration_notice_period` | `integer` | ✓ |  |
| `hr_presence_control_ip_list` | `character varying` | ✓ |  |
| `employee_properties_definition` | `jsonb` | ✓ |  |
| `hr_presence_control_login` | `boolean` | ✓ |  |
| `hr_presence_control_email` | `boolean` | ✓ |  |
| `hr_presence_control_ip` | `boolean` | ✓ |  |
| `hr_presence_control_attendance` | `boolean` | ✓ |  |
| `external_code` | `character varying` | ✓ |  |
| `social_twitter` | `character varying` | ✓ |  |
| `social_facebook` | `character varying` | ✓ |  |
| `social_github` | `character varying` | ✓ |  |
| `social_linkedin` | `character varying` | ✓ |  |
| `social_youtube` | `character varying` | ✓ |  |
| `social_instagram` | `character varying` | ✓ |  |
| `social_tiktok` | `character varying` | ✓ |  |
| `social_discord` | `character varying` | ✓ |  |
| `website_id` | `integer` | ✓ | → `website` |
| `free_order_label` | `jsonb` | ✓ |  |
| `expense_journal_id` | `integer` | ✓ | → `account_journal` |
| `lunch_notify_message` | `jsonb` | ✓ |  |
| `lunch_minimum_threshold` | `double precision` | ✓ |  |
| `overtime_company_threshold` | `integer` | ✓ |  |
| `overtime_employee_threshold` | `integer` | ✓ |  |
| `attendance_kiosk_delay` | `integer` | ✓ |  |
| `attendance_kiosk_mode` | `character varying` | ✓ |  |
| `attendance_barcode_source` | `character varying` | ✓ |  |
| `attendance_kiosk_key` | `character varying` | ✓ |  |
| `attendance_overtime_validation` | `character varying` | ✓ |  |
| `hr_attendance_display_overtime` | `boolean` | ✓ |  |
| `attendance_kiosk_use_pin` | `boolean` | ✓ |  |
| `attendance_from_systray` | `boolean` | ✓ |  |
| `auto_check_out` | `boolean` | ✓ |  |
| `single_check_in` | `boolean` | ✓ |  |
| `absence_management` | `boolean` | ✓ |  |
| `attendance_device_tracking` | `boolean` | ✓ |  |
| `auto_check_out_tolerance` | `double precision` | ✓ |  |
| `job_properties_definition` | `jsonb` | ✓ |  |
| `applicant_properties_definition` | `jsonb` | ✓ |  |

### `res_currency` (~170 rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `name` | `character varying` |  |  |
| `symbol` | `character varying` |  |  |
| `iso_numeric` | `integer` | ✓ |  |
| `decimal_places` | `integer` | ✓ |  |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `full_name` | `character varying` | ✓ |  |
| `position` | `character varying` | ✓ |  |
| `currency_unit_label` | `jsonb` | ✓ |  |
| `currency_subunit_label` | `jsonb` | ✓ |  |
| `rounding` | `numeric` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |

### `uom_uom` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `sequence` | `integer` | ✓ |  |
| `relative_uom_id` | `integer` | ✓ | → `uom_uom` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `parent_path` | `character varying` | ✓ |  |
| `name` | `jsonb` |  |  |
| `relative_factor` | `numeric` |  |  |
| `factor` | `numeric` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `package_type_id` | `integer` | ✓ | → `stock_package_type` |
| `is_pos_groupable` | `boolean` | ✓ |  |
