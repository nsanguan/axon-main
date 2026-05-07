# Payment Tables


### `payment_transaction` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `provider_id` | `integer` |  | → `payment_provider` |
| `company_id` | `integer` | ✓ | → `res_company` |
| `payment_method_id` | `integer` |  | → `payment_method` |
| `currency_id` | `integer` |  | → `res_currency` |
| `token_id` | `integer` | ✓ | → `payment_token` |
| `source_transaction_id` | `integer` | ✓ | → `payment_transaction` |
| `partner_id` | `integer` |  | → `res_partner` |
| `partner_state_id` | `integer` | ✓ | → `res_country_state` |
| `partner_country_id` | `integer` | ✓ | → `res_country` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `reference` | `character varying` |  |  |
| `provider_reference` | `character varying` | ✓ |  |
| `state` | `character varying` |  |  |
| `operation` | `character varying` | ✓ |  |
| `landing_route` | `character varying` | ✓ |  |
| `partner_name` | `character varying` | ✓ |  |
| `partner_lang` | `character varying` | ✓ |  |
| `partner_email` | `character varying` | ✓ |  |
| `partner_address` | `character varying` | ✓ |  |
| `partner_zip` | `character varying` | ✓ |  |
| `partner_city` | `character varying` | ✓ |  |
| `partner_phone` | `character varying` | ✓ |  |
| `state_message` | `text` | ✓ |  |
| `amount` | `numeric` |  |  |
| `is_live` | `boolean` | ✓ |  |
| `is_post_processed` | `boolean` | ✓ |  |
| `tokenize` | `boolean` | ✓ |  |
| `last_state_change` | `timestamp without time zone` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `payment_id` | `integer` | ✓ | → `account_payment` |
| `pos_order_id` | `integer` | ✓ | → `pos_order` |
| `donation_log_message` | `text` | ✓ |  |
| `is_donation` | `boolean` | ✓ |  |

### `payment_provider` (~? rows)

| Column | Type | Null | FK |
|--------|------|------|----|
| `id` | `integer` |  |  |
| `sequence` | `integer` | ✓ |  |
| `company_id` | `integer` |  | → `res_company` |
| `redirect_form_view_id` | `integer` | ✓ | → `ir_ui_view` |
| `inline_form_view_id` | `integer` | ✓ | → `ir_ui_view` |
| `token_inline_form_view_id` | `integer` | ✓ | → `ir_ui_view` |
| `express_checkout_form_view_id` | `integer` | ✓ | → `ir_ui_view` |
| `color` | `integer` | ✓ |  |
| `module_id` | `integer` | ✓ | → `ir_module_module` |
| `create_uid` | `integer` | ✓ | → `res_users` |
| `write_uid` | `integer` | ✓ | → `res_users` |
| `code` | `character varying` |  |  |
| `state` | `character varying` |  |  |
| `name` | `jsonb` |  |  |
| `pre_msg` | `jsonb` | ✓ |  |
| `pending_msg` | `jsonb` | ✓ |  |
| `auth_msg` | `jsonb` | ✓ |  |
| `done_msg` | `jsonb` | ✓ |  |
| `cancel_msg` | `jsonb` | ✓ |  |
| `minimum_amount` | `numeric` | ✓ |  |
| `maximum_amount` | `numeric` | ✓ |  |
| `is_published` | `boolean` | ✓ |  |
| `allow_tokenization` | `boolean` | ✓ |  |
| `capture_manually` | `boolean` | ✓ |  |
| `allow_express_checkout` | `boolean` | ✓ |  |
| `create_date` | `timestamp without time zone` | ✓ |  |
| `write_date` | `timestamp without time zone` | ✓ |  |
| `so_reference_type` | `character varying` | ✓ |  |
| `website_id` | `integer` | ✓ | → `website` |
| `custom_mode` | `character varying` | ✓ |  |
| `qr_code` | `boolean` | ✓ |  |
