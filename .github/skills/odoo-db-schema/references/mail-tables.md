# Mail & Activity Tables


### `mail_message` (~3391 rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `parent_id` | `integer` | ✓ | → `mail_message` |
| `res_id` | `integer` | ✓ |  |
| `record_alias_domain_id` | `integer` | ✓ | → `mail_alias_domain` |
| `record_company_id` | `integer` | ✓ | → `res_company` |
| `subtype_id` | `integer` | ✓ | → `mail_message_subtype` |
| `mail_activity_type_id` | `integer` | ✓ | → `mail_activity_type` |
| `author_id` | `integer` | ✓ | → `res_partner` |
| `author_guest_id` | `integer` | ✓ | → `mail_guest` |
| `mail_server_id` | `integer` | ✓ | → `ir_mail_server` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `subject` | `character varying` | ✓ |  |
| `model` | `character varying` | ✓ |  |
| `message_type` | `character varying` |  |  |
| `email_from` | `character varying` | ✓ |  |
| `incoming_email_cc` | `character varying` | ✓ |  |
| `outgoing_email_to` | `character varying` | ✓ |  |
| `message_id` | `character varying` | ✓ |  |
| `reply_to` | `character varying` | ✓ |  |
| `email_layout_xmlid` | `character varying` | ✓ |  |
| `body` | `text` | ✓ |  |
| `incoming_email_to` | `text` | ✓ |  |
| `is_internal` | `boolean` | ✓ |  |
| `reply_to_force_new` | `boolean` | ✓ |  |
| `email_add_signature` | `boolean` | ✓ |  |
| `date` | `timestamp without time zone` | ✓ |  |
| `pinned_at` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |

### `mail_activity` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `res_model_id` | `integer` | ✓ | → `ir_model` |
| `res_id` | `integer` | ✓ |  |
| `activity_type_id` | `integer` | ✓ | → `mail_activity_type` |
| `activity_plan_id` | `integer` | ✓ | → `mail_activity_plan` |
| `activity_template_id` | `integer` | ✓ | → `mail_activity_plan_template` |
| `user_id` | `integer` | ✓ | → `res_users` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `res_model` | `character varying` | ✓ |  |
| `res_name` | `character varying` | ✓ |  |
| `summary` | `character varying` | ✓ |  |
| `technical_usage` | `character varying` | ✓ |  |
| `user_tz` | `character varying` | ✓ |  |
| `date_deadline` | `date` |  |  |
| `date_done` | `date` | ✓ |  |
| `note` | `text` | ✓ |  |
| `feedback` | `text` | ✓ |  |
| `automated` | `boolean` | ✓ |  |
| `active` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `calendar_event_id` | `integer` | ✓ | → `calendar_event` |
