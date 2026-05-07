# Odoo Meta Tables


### `ir_model` (~778 rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `model` | `character varying` |  |  |
| `order` | `character varying` |  |  |
| `state` | `character varying` | ✓ |  |
| `fold_name` | `character varying` | ✓ |  |
| `name` | `jsonb` |  |  |
| `info` | `text` | ✓ |  |
| `explanation` | `text` | ✓ |  |
| `abstract` | `boolean` | ✓ |  |
| `transient` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `is_mail_thread` | `boolean` | ✓ |  |
| `is_mail_activity` | `boolean` | ✓ |  |
| `is_mail_blacklist` | `boolean` | ✓ |  |
| `website_form_default_field_id` | `integer` | ✓ | → `ir_model_fields` |
| `website_form_key` | `character varying` | ✓ |  |
| `website_form_label` | `jsonb` | ✓ |  |
| `website_form_access` | `boolean` | ✓ |  |

### `ir_model_fields` (~18064 rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `relation_field_id` | `integer` | ✓ | → `ir_model_fields` |
| `model_id` | `integer` |  | → `ir_model` |
| `related_field_id` | `integer` | ✓ | → `ir_model_fields` |
| `size` | `integer` | ✓ |  |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `character varying` |  |  |
| `model` | `character varying` |  |  |
| `relation` | `character varying` | ✓ |  |
| `relation_field` | `character varying` | ✓ |  |
| `relation_model_field` | `character varying` | ✓ |  |
| `ttype` | `character varying` |  |  |
| `related` | `character varying` | ✓ |  |
| `translate` | `character varying` | ✓ |  |
| `state` | `character varying` |  |  |
| `on_delete` | `character varying` | ✓ |  |
| `domain` | `character varying` | ✓ |  |
| `relation_table` | `character varying` | ✓ |  |
| `column1` | `character varying` | ✓ |  |
| `column2` | `character varying` | ✓ |  |
| `depends` | `character varying` | ✓ |  |
| `currency_field` | `character varying` | ✓ |  |
| `field_description` | `jsonb` |  |  |
| `help` | `jsonb` | ✓ |  |
| `compute` | `text` | ✓ |  |
| `copied` | `boolean` | ✓ |  |
| `required` | `boolean` | ✓ |  |
| `readonly` | `boolean` | ✓ |  |
| `index` | `boolean` | ✓ |  |
| `company_dependent` | `boolean` | ✓ |  |
| `group_expand` | `boolean` | ✓ |  |
| `selectable` | `boolean` | ✓ |  |
| `store` | `boolean` | ✓ |  |
| `sanitize` | `boolean` | ✓ |  |
| `sanitize_overridable` | `boolean` | ✓ |  |
| `sanitize_tags` | `boolean` | ✓ |  |
| `sanitize_attributes` | `boolean` | ✓ |  |
| `sanitize_style` | `boolean` | ✓ |  |
| `sanitize_form` | `boolean` | ✓ |  |
| `strip_style` | `boolean` | ✓ |  |
| `strip_classes` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `tracking` | `integer` | ✓ |  |
| `website_form_blacklisted` | `boolean` | ✓ |  |

### `ir_model_access` (~1499 rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `model_id` | `integer` |  | → `ir_model` |
| `group_id` | `integer` | ✓ | → `res_groups` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `character varying` |  |  |
| `active` | `boolean` | ✓ |  |
| `perm_read` | `boolean` | ✓ |  |
| `perm_write` | `boolean` | ✓ |  |
| `perm_create` | `boolean` | ✓ |  |
| `perm_unlink` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |

### `ir_module_module` (~655 rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `website` | `character varying` | ✓ |  |
| `summary` | `jsonb` | ✓ |  |
| `name` | `character varying` |  |  |
| `author` | `character varying` | ✓ |  |
| `icon` | `character varying` | ✓ |  |
| `state` | `character varying(16)` | ✓ |  |
| `latest_version` | `character varying` | ✓ |  |
| `shortdesc` | `jsonb` | ✓ |  |
| `category_id` | `integer` | ✓ | → `ir_module_category` |
| `description` | `jsonb` | ✓ |  |
| `application` | `boolean` | ✓ |  |
| `demo` | `boolean` | ✓ |  |
| `web` | `boolean` | ✓ |  |
| `license` | `character varying(32)` | ✓ |  |
| `sequence` | `integer` | ✓ |  |
| `auto_install` | `boolean` | ✓ |  |
| `to_buy` | `boolean` | ✓ |  |
| `maintainer` | `character varying` | ✓ |  |
| `published_version` | `character varying` | ✓ |  |
| `url` | `character varying` | ✓ |  |
| `contributors` | `text` | ✓ |  |
| `menus_by_module` | `text` | ✓ |  |
| `reports_by_module` | `text` | ✓ |  |
| `views_by_module` | `text` | ✓ |  |
| `iap_paid_service` | `boolean` | ✓ |  |
| `module_type` | `character varying` | ✓ |  |
| `imported` | `boolean` | ✓ |  |

### `ir_cron` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `ir_actions_server_id` | `integer` |  | → `ir_act_server` |
| `user_id` | `integer` |  | → `res_users` |
| `interval_number` | `integer` |  |  |
| `priority` | `integer` | ✓ |  |
| `failure_count` | `integer` | ✓ |  |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `cron_name` | `character varying` | ✓ |  |
| `interval_type` | `character varying` |  |  |
| `active` | `boolean` | ✓ |  |
| `nextcall` | `timestamp without time zone` |  |  |
| `lastcall` | `timestamp without time zone` | ✓ |  |
| `first_failure_date` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |

### `maintenance_request` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `company_id` | `integer` |  | → `res_company` |
| `owner_user_id` | `integer` | ✓ | → `res_users` |
| `category_id` | `integer` | ✓ | → `maintenance_equipment_category` |
| `equipment_id` | `integer` | ✓ | → `maintenance_equipment` |
| `stage_id` | `integer` | ✓ | → `maintenance_stage` |
| `color` | `integer` | ✓ |  |
| `maintenance_team_id` | `integer` |  | → `maintenance_team` |
| `repeat_interval` | `integer` | ✓ |  |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `character varying` |  |  |
| `priority` | `character varying` | ✓ |  |
| `state` | `character varying` |  |  |
| `maintenance_type` | `character varying` | ✓ |  |
| `repeat_unit` | `character varying` | ✓ |  |
| `repeat_type` | `character varying` | ✓ |  |
| `close_date` | `date` | ✓ |  |
| `repeat_until` | `date` | ✓ |  |
| `description` | `text` | ✓ |  |
| `instruction_text` | `text` | ✓ |  |
| `recurring_maintenance` | `boolean` | ✓ |  |
| `schedule_date` | `timestamp without time zone` | ✓ |  |
| `schedule_end` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `duration` | `double precision` | ✓ |  |
| `employee_id` | `integer` | ✓ | → `hr_employee` |

### `fleet_vehicle` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `manager_id` | `integer` | ✓ | → `res_users` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `driver_id` | `integer` | ✓ | → `res_partner` |
| `future_driver_id` | `integer` | ✓ | → `res_partner` |
| `model_id` | `integer` |  | → `fleet_vehicle_model` |
| `brand_id` | `integer` | ✓ | → `fleet_vehicle_model_brand` |
| `state_id` | `integer` | ✓ | → `fleet_vehicle_state` |
| `seats` | `integer` | ✓ |  |
| `doors` | `integer` | ✓ |  |
| `category_id` | `integer` | ✓ | → `fleet_vehicle_model_category` |
| `vehicle_range` | `integer` | ✓ |  |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `name` | `character varying` | ✓ |  |
| `license_plate` | `character varying` | ✓ |  |
| `vin_sn` | `character varying` | ✓ |  |
| `color` | `character varying` | ✓ |  |
| `location` | `character varying` | ✓ |  |
| `model_year` | `character varying` | ✓ |  |
| `odometer_unit` | `character varying` |  |  |
| `transmission` | `character varying` | ✓ |  |
| `fuel_type` | `character varying` | ✓ |  |
| `power_unit` | `character varying` |  |  |
| `co2_emission_unit` | `character varying` |  |  |
| `co2_standard` | `character varying` | ✓ |  |
| `frame_type` | `character varying` | ✓ |  |
| `range_unit` | `character varying` |  |  |
| `next_assignation_date` | `date` | ✓ |  |
| `order_date` | `date` | ✓ |  |
| `acquisition_date` | `date` | ✓ |  |
| `write_off_date` | `date` | ✓ |  |
| `contract_date_start` | `date` | ✓ |  |
| `vehicle_properties` | `jsonb` | ✓ |  |
| `description` | `text` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `trailer_hook` | `boolean` | ✓ |  |
| `plan_to_change_vehicle` | `boolean` | ✓ |  |
| `electric_assistance` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `horsepower` | `double precision` | ✓ |  |
| `horsepower_tax` | `double precision` | ✓ |  |
| `power` | `double precision` | ✓ |  |
| `co2` | `double precision` | ✓ |  |
| `car_value` | `double precision` | ✓ |  |
| `net_car_value` | `double precision` | ✓ |  |
| `residual_value` | `double precision` | ✓ |  |
| `frame_size` | `double precision` | ✓ |  |
| `driver_employee_id` | `integer` | ✓ | → `hr_employee` |
| `future_driver_employee_id` | `integer` | ✓ | → `hr_employee` |
