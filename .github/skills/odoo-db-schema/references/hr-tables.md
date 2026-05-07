# HR & Payroll Tables


### `hr_employee` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `resource_id` | `integer` |  | → `resource_resource` |
| `company_id` | `integer` |  | → `res_company` |
| `message_main_attachment_id` | `integer` | ✓ | → `ir_attachment` |
| `current_version_id` | `integer` | ✓ | → `hr_version` |
| `contract_template_id` | `integer` | ✓ | → `hr_version` |
| `user_id` | `integer` | ✓ | → `res_users` |
| `work_contact_id` | `integer` | ✓ | → `res_partner` |
| `country_of_birth` | `integer` | ✓ | → `res_country` |
| `parent_id` | `integer` | ✓ | → `hr_employee` |
| `coach_id` | `integer` | ✓ | → `hr_employee` |
| `color` | `integer` | ✓ |  |
| `monday_location_id` | `integer` | ✓ | → `hr_work_location` |
| `tuesday_location_id` | `integer` | ✓ | → `hr_work_location` |
| `wednesday_location_id` | `integer` | ✓ | → `hr_work_location` |
| `thursday_location_id` | `integer` | ✓ | → `hr_work_location` |
| `friday_location_id` | `integer` | ✓ | → `hr_work_location` |
| `saturday_location_id` | `integer` | ✓ | → `hr_work_location` |
| `sunday_location_id` | `integer` | ✓ | → `hr_work_location` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `character varying` | ✓ |  |
| `work_phone` | `character varying` | ✓ |  |
| `mobile_phone` | `character varying` | ✓ |  |
| `work_email` | `character varying` | ✓ |  |
| `legal_name` | `character varying` | ✓ |  |
| `private_phone` | `character varying` | ✓ |  |
| `private_email` | `character varying` | ✓ |  |
| `lang` | `character varying` | ✓ |  |
| `place_of_birth` | `character varying` | ✓ |  |
| `birthday_month` | `character varying` | ✓ |  |
| `permit_no` | `character varying` | ✓ |  |
| `visa_no` | `character varying` | ✓ |  |
| `certificate` | `character varying` | ✓ |  |
| `study_field` | `character varying` | ✓ |  |
| `emergency_contact` | `character varying` | ✓ |  |
| `emergency_phone` | `character varying` | ✓ |  |
| `barcode` | `character varying` | ✓ |  |
| `pin` | `character varying` | ✓ |  |
| `id_card_name` | `character varying` | ✓ |  |
| `driving_license_name` | `character varying` | ✓ |  |
| `today_location_name` | `character varying` | ✓ |  |
| `birthday` | `date` | ✓ |  |
| `visa_expire` | `date` | ✓ |  |
| `work_permit_expiration_date` | `date` | ✓ |  |
| `first_contract_date` | `date` | ✓ |  |
| `salary_distribution` | `jsonb` | ✓ |  |
| `employee_properties` | `jsonb` | ✓ |  |
| `hourly_cost` | `numeric` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `birthday_public_display` | `boolean` | ✓ |  |
| `work_permit_scheduled_activity` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `external_code` | `character varying` | ✓ |  |
| `leave_manager_id` | `integer` | ✓ | → `res_users` |
| `expense_manager_id` | `integer` | ✓ | → `res_users` |
| `attendance_manager_id` | `integer` | ✓ | → `res_users` |
| `last_attendance_id` | `integer` | ✓ | → `hr_attendance` |
| `last_check_in` | `timestamp without time zone` | ✓ |  |
| `last_check_out` | `timestamp without time zone` | ✓ |  |

### `hr_leave` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `message_main_attachment_id` | `integer` | ✓ | → `ir_attachment` |
| `user_id` | `integer` | ✓ | → `res_users` |
| `work_entry_type_id` | `integer` |  | → `hr_work_entry_type` |
| `employee_id` | `integer` |  | → `hr_employee` |
| `employee_company_id` | `integer` | ✓ | → `res_company` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `department_id` | `integer` | ✓ | → `hr_department` |
| `resource_calendar_id` | `integer` | ✓ | → `resource_calendar` |
| `meeting_id` | `integer` | ✓ | → `calendar_event` |
| `first_approver_id` | `integer` | ✓ | → `hr_employee` |
| `second_approver_id` | `integer` | ✓ | → `hr_employee` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `private_name` | `character varying` | ✓ |  |
| `state` | `character varying` | ✓ |  |
| `duration_display` | `character varying` | ✓ |  |
| `request_date_from_period` | `character varying` | ✓ |  |
| `request_date_to_period` | `character varying` | ✓ |  |
| `request_date_from` | `date` | ✓ |  |
| `request_date_to` | `date` | ✓ |  |
| `notes` | `text` | ✓ |  |
| `date_from` | `timestamp without time zone` | ✓ |  |
| `date_to` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `number_of_days` | `double precision` | ✓ |  |
| `number_of_hours` | `double precision` | ✓ |  |
| `request_hour_from` | `double precision` | ✓ |  |
| `request_hour_to` | `double precision` | ✓ |  |

### `hr_expense` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `message_main_attachment_id` | `integer` | ✓ | → `ir_attachment` |
| `employee_id` | `integer` |  | → `hr_employee` |
| `department_id` | `integer` | ✓ | → `hr_department` |
| `manager_id` | `integer` | ✓ | → `res_users` |
| `company_id` | `integer` |  | → `res_company` |
| `product_id` | `integer` | ✓ | → `product_product` |
| `product_uom_id` | `integer` | ✓ | → `uom_uom` |
| `split_expense_origin_id` | `integer` | ✓ | → `hr_expense` |
| `currency_id` | `integer` |  | → `res_currency` |
| `payment_method_line_id` | `integer` | ✓ | → `account_payment_method_line` |
| `existing_bill_id` | `integer` | ✓ | → `account_move` |
| `account_move_id` | `integer` | ✓ | → `account_move` |
| `vendor_id` | `integer` | ✓ | → `res_partner` |
| `account_id` | `integer` | ✓ | → `account_account` |
| `former_sheet_id` | `integer` | ✓ |  |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `character varying` | ✓ |  |
| `state` | `character varying` | ✓ |  |
| `approval_state` | `character varying` | ✓ |  |
| `payment_mode` | `character varying` |  |  |
| `date` | `date` | ✓ |  |
| `analytic_distribution` | `jsonb` | ✓ |  |
| `description` | `text` | ✓ |  |
| `quantity` | `numeric` |  |  |
| `tax_amount_currency` | `numeric` | ✓ |  |
| `tax_amount` | `numeric` | ✓ |  |
| `total_amount_currency` | `numeric` | ✓ |  |
| `total_amount` | `numeric` | ✓ |  |
| `untaxed_amount_currency` | `numeric` | ✓ |  |
| `untaxed_amount` | `numeric` | ✓ |  |
| `price_unit` | `numeric` |  |  |
| `has_existing_bill` | `boolean` | ✓ |  |
| `approval_date` | `timestamp without time zone` | ✓ |  |
| `last_notification_date` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `sale_order_id` | `integer` | ✓ | → `sale_order` |
| `sale_order_line_id` | `integer` | ✓ | → `sale_order_line` |

### `project_project` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `account_id` | `integer` | ✓ | → `account_analytic_account` |
| `alias_id` | `integer` |  | → `mail_alias` |
| `sequence` | `integer` | ✓ |  |
| `partner_id` | `integer` | ✓ | → `res_partner` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `color` | `integer` | ✓ |  |
| `user_id` | `integer` | ✓ | → `res_users` |
| `stage_id` | `integer` | ✓ | → `project_project_stage` |
| `last_update_id` | `integer` | ✓ | → `project_update` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `access_token` | `character varying` | ✓ |  |
| `privacy_visibility` | `character varying` |  |  |
| `last_update_status` | `character varying` |  |  |
| `date_start` | `date` | ✓ |  |
| `date` | `date` | ✓ |  |
| `duration_tracking` | `jsonb` | ✓ |  |
| `name` | `jsonb` |  |  |
| `label_tasks` | `jsonb` | ✓ |  |
| `task_properties_definition` | `jsonb` | ✓ |  |
| `description` | `text` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `allow_task_dependencies` | `boolean` | ✓ |  |
| `allow_milestones` | `boolean` | ✓ |  |
| `allow_recurring_tasks` | `boolean` | ✓ |  |
| `is_template` | `boolean` | ✓ |  |
| `date_last_stage_update` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `x_plan2_id` | `integer` | ✓ | → `account_analytic_account` |
| `x_plan3_id` | `integer` | ✓ | → `account_analytic_account` |
| `sale_line_id` | `integer` | ✓ | → `sale_order_line` |
| `reinvoiced_sale_order_id` | `integer` | ✓ | → `sale_order` |
| `allow_billable` | `boolean` | ✓ |  |
| `lead_id` | `integer` | ✓ | → `crm_lead` |

### `project_task` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `sequence` | `integer` | ✓ |  |
| `stage_id` | `integer` | ✓ | → `project_task_type` |
| `project_id` | `integer` | ✓ | → `project_project` |
| `partner_id` | `integer` | ✓ | → `res_partner` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `color` | `integer` | ✓ |  |
| `displayed_image_id` | `integer` | ✓ | → `ir_attachment` |
| `parent_id` | `integer` | ✓ | → `project_task` |
| `milestone_id` | `integer` | ✓ | → `project_milestone` |
| `recurrence_id` | `integer` | ✓ | → `project_task_recurrence` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `access_token` | `character varying` | ✓ |  |
| `name` | `character varying` |  |  |
| `priority` | `character varying` | ✓ |  |
| `state` | `character varying` |  |  |
| `partner_phone` | `character varying` | ✓ |  |
| `email_from` | `character varying` | ✓ |  |
| `html_field_history` | `jsonb` | ✓ |  |
| `duration_tracking` | `jsonb` | ✓ |  |
| `task_properties` | `jsonb` | ✓ |  |
| `description` | `text` | ✓ |  |
| `working_hours_open` | `numeric` | ✓ |  |
| `working_hours_close` | `numeric` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `display_in_project` | `boolean` | ✓ |  |
| `recurring_task` | `boolean` | ✓ |  |
| `is_template` | `boolean` | ✓ |  |
| `has_template_ancestor` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `date_end` | `timestamp without time zone` | ✓ |  |
| `date_assign` | `timestamp without time zone` | ✓ |  |
| `date_deadline` | `timestamp without time zone` | ✓ |  |
| `date_last_stage_update` | `timestamp without time zone` | ✓ |  |
| `rating_last_value` | `double precision` | ✓ |  |
| `allocated_hours` | `double precision` | ✓ |  |
| `working_days_open` | `double precision` | ✓ |  |
| `working_days_close` | `double precision` | ✓ |  |
| `partner_name` | `character varying` | ✓ |  |
| `partner_company_name` | `character varying` | ✓ |  |
| `sale_order_id` | `integer` | ✓ | → `sale_order` |
| `sale_line_id` | `integer` | ✓ | → `sale_order_line` |
