---
name: odoo-accounting
description: 'Work with Odoo Accounting and Invoicing: account.move (invoices/bills), account.move.line (journal entries), account.journal, account.account, payments, reconciliation, taxes, chart of accounts, bank statements. Use for: creating invoices programmatically, posting journal entries, registering payments, understanding account types, reconciling payments, setting up taxes, analytic accounting.'
argument-hint: 'Describe the accounting task (e.g. "create and post a customer invoice" or "reconcile a payment")'
---

# Odoo Accounting

## Key Models
- `account.move` — Invoice, Bill, Credit Note, Journal Entry
- `account.move.line` — Journal entry lines / invoice lines
- `account.journal` — Journals (Sales, Purchase, Bank, Cash, Misc)
- `account.account` — Chart of Accounts entries
- `account.payment` — Customer/vendor payments
- `account.tax` — Tax definitions
- `account.bank.statement` — Bank statement import
- `account.analytic.account` — Analytic accounts (projects/cost centers)

## Source Files
- `/u01/erp/Odoo/odoo-server/addons/account/models/account_move.py`
- `/u01/erp/Odoo/odoo-server/addons/account/models/account_move_line.py`
- `/u01/erp/Odoo/odoo-server/addons/account/models/account_payment.py`
- `/u01/erp/Odoo/odoo-server/addons/account/models/account_journal.py`
- `/u01/erp/Odoo/odoo-server/addons/account/models/account_account.py`

## account.move: Invoice Types

| move_type | Description |
|-----------|-------------|
| `out_invoice` | Customer Invoice |
| `out_refund` | Customer Credit Note |
| `in_invoice` | Vendor Bill |
| `in_refund` | Vendor Credit Note |
| `entry` | Misc Journal Entry |
| `out_receipt` | Sale Receipt |
| `in_receipt` | Purchase Receipt |

## Invoice States

| state | Description |
|-------|-------------|
| `draft` | Draft (unposted) |
| `posted` | Posted (confirmed) |
| `cancel` | Cancelled |

## Payment States

| payment_state | Description |
|---------------|-------------|
| `not_paid` | Not paid |
| `partial` | Partially paid |
| `paid` | Fully paid |
| `in_payment` | In payment process |
| `reversed` | Reversed by credit note |

## Creating a Customer Invoice Programmatically

```python
from odoo import fields

# Create draft invoice
invoice = env['account.move'].create({
    'move_type': 'out_invoice',
    'partner_id': env.ref('base.res_partner_1').id,
    'invoice_date': fields.Date.today(),
    'journal_id': env['account.journal'].search([('type', '=', 'sale')], limit=1).id,
    'invoice_line_ids': [
        (0, 0, {
            'product_id': env.ref('product.product_product_1').id,
            'quantity': 2.0,
            'price_unit': 150.0,
            'tax_ids': [(6, 0, product.taxes_id.ids)],
        }),
    ],
})

# Validate (post) the invoice
invoice.action_post()
print(invoice.name)           # e.g. 'INV/2026/00001'
print(invoice.amount_total)   # Total incl. tax
```

## Creating a Vendor Bill

```python
bill = env['account.move'].create({
    'move_type': 'in_invoice',
    'partner_id': vendor.id,
    'invoice_date': fields.Date.today(),
    'ref': 'Vendor Reference 123',   # Vendor bill reference
    'invoice_line_ids': [
        (0, 0, {
            'name': 'Service Description',
            'account_id': env['account.account'].search([
                ('account_type', '=', 'expense')
            ], limit=1).id,
            'quantity': 1.0,
            'price_unit': 500.0,
        }),
    ],
})
bill.action_post()
```

## Registering a Payment

```python
# Register payment for a posted invoice
payment_wizard = env['account.payment.register'].with_context(
    active_model='account.move',
    active_ids=invoice.ids,
).create({
    'payment_date': fields.Date.today(),
    'journal_id': env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
    'amount': invoice.amount_residual,
})
payment_wizard.action_create_payments()
```

## Direct Payment Creation

```python
payment = env['account.payment'].create({
    'payment_type': 'inbound',          # inbound = receive money, outbound = send money
    'partner_type': 'customer',         # customer or supplier
    'partner_id': partner.id,
    'amount': 1000.0,
    'date': fields.Date.today(),
    'journal_id': bank_journal.id,
    'memo': 'Payment for INV/2026/00001',
})
payment.action_post()
```

## Searching Invoices

```python
# All unpaid customer invoices
unpaid = env['account.move'].search([
    ('move_type', '=', 'out_invoice'),
    ('state', '=', 'posted'),
    ('payment_state', 'not in', ['paid', 'reversed']),
])

# Overdue invoices
from datetime import date
overdue = env['account.move'].search([
    ('move_type', '=', 'out_invoice'),
    ('state', '=', 'posted'),
    ('payment_state', '!=', 'paid'),
    ('invoice_date_due', '<', date.today()),
])

# Bills for a specific vendor
vendor_bills = env['account.move'].search([
    ('move_type', '=', 'in_invoice'),
    ('partner_id', '=', vendor.id),
])
```

## Chart of Accounts: Account Types

| account_type | Description |
|--------------|-------------|
| `asset_receivable` | Accounts Receivable |
| `asset_cash` | Cash and Bank |
| `asset_current` | Current Asset |
| `asset_non_current` | Non-Current Asset |
| `asset_prepayments` | Prepaid Expenses |
| `asset_fixed` | Fixed Asset |
| `liability_payable` | Accounts Payable |
| `liability_credit_card` | Credit Card |
| `liability_current` | Current Liability |
| `liability_non_current` | Non-Current Liability |
| `equity` | Equity |
| `equity_unaffected` | Retained Earnings |
| `income` | Income |
| `income_other` | Other Income |
| `expense` | Expenses |
| `expense_depreciation` | Depreciation |
| `expense_direct_cost` | Cost of Revenue |
| `off_balance` | Off-Balance Sheet |

## Journals

```python
# Get specific journal types
sales_journal  = env['account.journal'].search([('type', '=', 'sale')], limit=1)
purchase_journal = env['account.journal'].search([('type', '=', 'purchase')], limit=1)
bank_journal   = env['account.journal'].search([('type', '=', 'bank')], limit=1)
cash_journal   = env['account.journal'].search([('type', '=', 'cash')], limit=1)
misc_journal   = env['account.journal'].search([('type', '=', 'general')], limit=1)
```

## Journal Entry (Manual)

```python
move = env['account.move'].create({
    'move_type': 'entry',
    'journal_id': misc_journal.id,
    'date': fields.Date.today(),
    'ref': 'Manual adjustment',
    'line_ids': [
        (0, 0, {
            'account_id': debit_account.id,
            'debit': 1000.0,
            'credit': 0.0,
            'name': 'Debit line',
        }),
        (0, 0, {
            'account_id': credit_account.id,
            'debit': 0.0,
            'credit': 1000.0,
            'name': 'Credit line',
        }),
    ],
})
move.action_post()
```

## Analytic Accounting

```python
# Assign analytic distribution to invoice line
invoice_line.write({
    'analytic_distribution': {
        str(analytic_account.id): 100.0,  # account_id: percentage
    }
})

# Multi-analytic split
invoice_line.write({
    'analytic_distribution': {
        str(project_account.id): 60.0,
        str(dept_account.id): 40.0,
    }
})
```

## Key Related Modules in Addons

| Module | Purpose |
|--------|---------|
| `account` | Core accounting/invoicing |
| `account_payment` | Payment acquirers |
| `account_check_printing` | Check printing |
| `account_debit_note` | Debit notes |
| `account_edi` | Electronic invoicing |
| `analytic` | Analytic accounts |
| `account_peppol` | PEPPOL e-invoicing |
| `account_tax_python` | Python-based tax computation |
