---
name: odoo-db-schema
description: 'Live Odoo database schema for odoo_db (202.71.1.13:5435). Use for: writing SQL queries against Odoo DB, finding column names, understanding table relationships, checking installed modules, joining tables, building SQL reports, debugging ORM queries. References include all 982 tables, 10066 columns, 3635 foreign keys, 227 installed modules.'
argument-hint: 'What table or relationship do you need? (e.g. "account_move columns" or "how sale_order links to stock")'
---

# Odoo DB Schema — Live Database

## Connection

| Parameter | Value |
|-----------|-------|
| Host | `202.71.1.13` |
| Port | `5435` |
| Database | `odoo_db` |
| User | `odoo_admin` |
| SSL | TLSv1.3 (required) |

```bash
# Terminal
PGPASSWORD=EraOwl2026 psql -h 202.71.1.13 -p 5435 -U odoo_admin -d odoo_db
```

```python
# Python (psycopg2)
import psycopg2
conn = psycopg2.connect(
    host='202.71.1.13', port=5435,
    database='odoo_db', user='odoo_admin', password='EraOwl2026',
    sslmode='require'
)
cur = conn.cursor()
```

## Database Statistics

| Metric | Value |
|--------|-------|
| Total Tables | 982 |
| Total Columns | 10,066 |
| Foreign Keys | 3,635 |
| Installed Modules | 227 |
| Odoo Version | 19.4 |

## Top 50 Tables by Row Count

| Table | Rows |
|-------|------|
| `ir_model_data` | 45393 |
| `ir_model_fields` | 18064 |
| `ir_ui_view` | 4398 |
| `ir_model_constraint` | 3966 |
| `ir_model_fields_selection` | 3419 |
| `mail_message` | 3391 |
| `ir_attachment` | 2649 |
| `res_country_state` | 1962 |
| `ir_model_access` | 1499 |
| `ir_module_module_dependency` | 1367 |
| `ir_cron_progress` | 1030 |
| `ir_act_window` | 793 |
| `ir_model` | 778 |
| `ir_ui_menu` | 729 |
| `ir_model_inherit` | 698 |
| `ir_module_module` | 655 |
| `mail_followers_mail_message_subtype_rel` | 605 |
| `mail_followers` | 491 |
| `hr_work_entry_type` | 468 |
| `ir_rule` | 468 |
| `product_supplier_taxes_rel` | 453 |
| `product_taxes_rel` | 435 |
| `payment_method_res_country_rel` | 421 |
| `bus_bus` | 419 |
| `account_tax_repartition_line` | 406 |
| `ir_ui_menu_group_rel` | 371 |
| `ir_model_relation` | 368 |
| `rule_group_rel` | 354 |
| `ir_act_window_view` | 336 |
| `account_account_res_company_rel` | 335 |
| `account_account` | 335 |
| `payment_method_payment_provider_rel` | 320 |
| `payment_method_res_currency_rel` | 306 |
| `product_value` | 303 |
| `res_country` | 251 |
| `account_move_line` | 242 |
| `payment_method` | 228 |
| `product_product` | 226 |
| `mail_mail` | 208 |
| `mail_notification` | 206 |
| `res_country_res_country_group_rel` | 204 |
| `ir_actions_server_history` | 198 |
| `ir_act_server` | 191 |
| `stock_move` | 191 |
| `mail_mail_res_partner_rel` | 190 |
| `module_country` | 177 |
| `res_currency` | 170 |
| `mail_message_res_partner_rel` | 167 |
| `res_currency_rate` | 163 |
| `product_template` | 154 |

## Key Table Groups

For full column schemas, load the reference files:

| Group | Tables | Reference |
|-------|--------|-----------|
| Core / Base | res_partner, res_users, res_company, res_currency | [core-tables.md](./references/core-tables.md) |
| Accounting | account_move, account_move_line, account_account, account_journal, account_tax, account_payment | [accounting-tables.md](./references/accounting-tables.md) |
| Sales & CRM | sale_order, sale_order_line, crm_lead | [sales-tables.md](./references/sales-tables.md) |
| Purchase | purchase_order, purchase_order_line | [purchase-tables.md](./references/purchase-tables.md) |
| Inventory | stock_picking, stock_move, stock_quant, stock_location, stock_warehouse | [stock-tables.md](./references/stock-tables.md) |
| Manufacturing | mrp_production, mrp_bom, mrp_bom_line | [mrp-tables.md](./references/mrp-tables.md) |
| Products | product_template, product_product, product_category, product_pricelist | [product-tables.md](./references/product-tables.md) |
| HR & Payroll | hr_employee, hr_contract, hr_leave, hr_payslip, hr_expense | [hr-tables.md](./references/hr-tables.md) |
| Project | project_project, project_task | [project-tables.md](./references/project-tables.md) |
| POS | pos_order, pos_order_line, pos_session | [pos-tables.md](./references/pos-tables.md) |
| Payment | payment_transaction, payment_provider | [payment-tables.md](./references/payment-tables.md) |
| Mail / Activity | mail_message, mail_activity | [mail-tables.md](./references/mail-tables.md) |
| Odoo Meta | ir_model, ir_model_fields, ir_model_access, ir_module_module | [meta-tables.md](./references/meta-tables.md) |
| All Tables | All 982 tables | [all-tables.md](./references/all-tables.md) |
| All Modules | All 227 installed modules | [modules.md](./references/modules.md) |

## Common SQL Queries

### Customer invoices with partner
```sql
SELECT am.name, am.invoice_date, am.amount_total, am.payment_state,
       rp.name AS partner, rp.email
FROM account_move am
JOIN res_partner rp ON am.partner_id = rp.id
WHERE am.move_type = 'out_invoice' AND am.state = 'posted'
ORDER BY am.invoice_date DESC;
```

### Confirmed sales orders with product lines
```sql
SELECT so.name, rp.name AS customer,
       sol.product_uom_qty, sol.price_unit, sol.price_subtotal,
       pt.name AS product
FROM sale_order so
JOIN res_partner rp ON so.partner_id = rp.id
JOIN sale_order_line sol ON sol.order_id = so.id
JOIN product_product pp ON sol.product_id = pp.id
JOIN product_template pt ON pp.product_tmpl_id = pt.id
WHERE so.state = 'sale'
ORDER BY so.date_order DESC;
```

### Stock on hand by product and location
```sql
SELECT pt.name AS product, sl.complete_name AS location,
       SUM(sq.quantity) AS on_hand, SUM(sq.reserved_quantity) AS reserved
FROM stock_quant sq
JOIN product_product pp ON sq.product_id = pp.id
JOIN product_template pt ON pp.product_tmpl_id = pt.id
JOIN stock_location sl ON sq.location_id = sl.id
WHERE sl.usage = 'internal' AND sq.quantity > 0
GROUP BY pt.name, sl.complete_name
ORDER BY pt.name;
```

### Overdue vendor bills
```sql
SELECT am.name, rp.name AS vendor,
       am.invoice_date_due, am.amount_residual
FROM account_move am
JOIN res_partner rp ON am.partner_id = rp.id
WHERE am.move_type = 'in_invoice'
  AND am.state = 'posted'
  AND am.payment_state != 'paid'
  AND am.invoice_date_due < CURRENT_DATE
ORDER BY am.invoice_date_due;
```

### HR employees with department and active contract
```sql
SELECT e.name AS employee, e.job_title,
       d.name AS department, c.wage
FROM hr_employee e
LEFT JOIN hr_department d ON e.department_id = d.id
LEFT JOIN hr_contract c ON c.employee_id = e.id AND c.state = 'open'
WHERE e.active = true
ORDER BY e.name;
```

### POS session sales summary
```sql
SELECT ps.name AS session, ps.state,
       ps.start_at, ps.stop_at,
       COUNT(po.id) AS orders,
       SUM(po.amount_total) AS total
FROM pos_session ps
LEFT JOIN pos_order po ON po.session_id = ps.id
GROUP BY ps.id, ps.name, ps.state, ps.start_at, ps.stop_at
ORDER BY ps.start_at DESC;
```

## Field → Table Quick Lookup

| Field Name | Model Table | Notes |
|-----------|------------|-------|
| `partner_id` | `res_partner` | Customer / Vendor / Contact |
| `company_id` | `res_company` | Multi-company |
| `currency_id` | `res_currency` | Currency |
| `product_id` | `product_product` | Specific variant |
| `product_tmpl_id` | `product_template` | Configurable product |
| `categ_id` | `product_category` | Product category |
| `uom_id` | `uom_uom` | Unit of measure |
| `journal_id` | `account_journal` | Accounting journal |
| `account_id` | `account_account` | GL account |
| `tax_id` | `account_tax` | Tax |
| `location_id` | `stock_location` | Warehouse location |
| `employee_id` | `hr_employee` | Employee |
| `department_id` | `hr_department` | HR department |
| `project_id` | `project_project` | Project |
| `user_id` | `res_users` | Responsible user |
| `analytic_distribution` | JSONB | `{str(account_id): percent}` |
