# Project Tables


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
