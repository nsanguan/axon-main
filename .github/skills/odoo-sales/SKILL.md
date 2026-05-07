---
name: odoo-sales
description: 'Work with Odoo Sales module: sale.order (quotations/sales orders), sale.order.line, pricelists, products, invoicing from sales, CRM pipeline, customer management. Use for: creating quotations, confirming sales orders, generating invoices from orders, working with pricelists, understanding order states, managing customers and products.'
argument-hint: 'Describe the sales task (e.g. "create a quotation for customer X with 3 product lines")'
---

# Odoo Sales

## Key Models
- `sale.order` — Quotation / Sales Order
- `sale.order.line` — Order lines
- `product.template` — Product template (configurable)
- `product.product` — Product variant (actual stockable item)
- `res.partner` — Customer/Partner
- `product.pricelist` — Pricelists
- `crm.lead` — CRM opportunities (→ sale)

## Source Files
- `/u01/erp/Odoo/odoo-server/addons/sale/models/sale_order.py`
- `/u01/erp/Odoo/odoo-server/addons/sale/models/sale_order_line.py`
- `/u01/erp/Odoo/odoo-server/addons/sale/models/product_template.py`
- `/u01/erp/Odoo/odoo-server/addons/sale/models/res_partner.py`

## Sale Order States

| state | Description |
|-------|-------------|
| `draft` | Quotation |
| `sent` | Quotation Sent (email sent to customer) |
| `sale` | Sales Order (confirmed) |
| `cancel` | Cancelled |

## Invoice Status

| invoice_status | Description |
|----------------|-------------|
| `upselling` | Upselling Opportunity |
| `invoiced` | Fully Invoiced |
| `to invoice` | Ready to Invoice |
| `no` | Nothing to Invoice |

## Creating a Quotation Programmatically

```python
from odoo import fields

# Get customer
partner = env['res.partner'].search([('name', 'ilike', 'Azure')], limit=1)

# Get product
product = env['product.product'].search([('name', 'ilike', 'Laptop')], limit=1)

# Create quotation
order = env['sale.order'].create({
    'partner_id': partner.id,
    'date_order': fields.Datetime.now(),
    'validity_date': fields.Date.today() + timedelta(days=30),
    'note': 'Thank you for your business.',
    'order_line': [
        (0, 0, {
            'product_id': product.id,
            'product_uom_qty': 2.0,
            'price_unit': product.lst_price,
            'name': product.name,
            'product_uom': product.uom_id.id,
            'tax_id': [(6, 0, product.taxes_id.ids)],
        }),
    ],
})
print(order.name)   # e.g. 'S00001'
```

## Confirming a Sales Order

```python
# Confirm order (draft → sale)
order.action_confirm()
print(order.state)  # 'sale'
```

## Sending a Quotation by Email

```python
order.action_quotation_send()
# This opens a mail compose wizard — call with context for automated sending:
order.with_context(send_email=True).action_quotation_sent()
```

## Generating Invoices from Sales Orders

```python
# Mark orders as 'to invoice' first (state='sale', invoice_status='to invoice')
# Then create invoices:
invoice_wizard = env['sale.advance.payment.inv'].with_context(
    active_ids=order.ids,
    active_model='sale.order',
).create({
    'advance_payment_method': 'delivered',  # or 'percentage', 'fixed'
})
invoice_wizard.create_invoices()

# Get created invoices
invoices = order.invoice_ids
```

## Sale Order Line Fields

```python
line = order.order_line[0]
line.product_id           # product.product
line.name                 # Description
line.product_uom_qty      # Ordered quantity
line.qty_delivered         # Delivered quantity
line.qty_invoiced          # Invoiced quantity
line.qty_to_invoice        # Remaining to invoice
line.price_unit            # Unit price
line.discount              # Discount %
line.tax_id                # Tax(es)
line.price_subtotal        # Subtotal before tax
line.price_total           # Total incl. tax
```

## Searching Orders

```python
# All confirmed orders
confirmed = env['sale.order'].search([('state', '=', 'sale')])

# Orders ready to invoice
to_invoice = env['sale.order'].search([
    ('state', '=', 'sale'),
    ('invoice_status', '=', 'to invoice'),
])

# Orders for a specific customer
customer_orders = env['sale.order'].search([
    ('partner_id', '=', partner.id),
    ('state', 'not in', ['cancel']),
])

# Orders created this month
from datetime import date
first_of_month = date.today().replace(day=1)
this_month = env['sale.order'].search([
    ('date_order', '>=', first_of_month),
    ('state', '=', 'sale'),
])
```

## Products

```python
# product.template = configurable product (color, size, etc.)
template = env['product.template'].search([('type', '=', 'consu')], limit=1)

# product.product = specific variant
product = template.product_variant_id   # default variant

# Product types
# 'consu'  = consumable (no stock tracking)
# 'service' = service
# 'combo'   = combo product

# Compute price for a customer/pricelist
price = product.with_context(
    pricelist=partner.property_product_pricelist.id,
    quantity=5.0,
    date=fields.Date.today(),
).price_compute('list_price')[product.id]
```

## Customer (res.partner) Key Fields

```python
partner = env['res.partner'].browse(1)
partner.customer_rank       # > 0 means is a customer
partner.supplier_rank       # > 0 means is a vendor
partner.property_product_pricelist  # assigned pricelist
partner.property_payment_term_id    # payment terms
partner.property_account_receivable_id  # AR account
partner.credit_limit        # credit limit (if set)
partner.total_due           # outstanding balance
```

## Pricelists

```python
# Get pricelist
pricelist = env['product.pricelist'].search([('name', 'ilike', 'Public')], limit=1)

# Apply pricelist to order
order.write({'pricelist_id': pricelist.id})
order._recompute_prices()   # Recalculate line prices
```

## CRM → Sales Flow

```python
# Lead/Opportunity to quotation
lead = env['crm.lead'].browse(lead_id)
lead.action_new_quotation()   # Opens new quotation linked to lead

# Get quotations/orders from a lead
orders = env['sale.order'].search([('opportunity_id', '=', lead.id)])
```

## Related Sale Modules

| Module | Purpose |
|--------|---------|
| `sale` | Core sales machinery |
| `sale_management` | Sales UI & settings |
| `sale_stock` | Delivery from sales |
| `sale_crm` | CRM-Sales integration |
| `sale_loyalty` | Discount/loyalty programs |
| `sale_pdf_quote_builder` | PDF quote builder |
| `sale_margin` | Margin calculation |
| `sale_timesheet` | Timesheet on sales |
| `sale_service` | Service products |
| `sale_purchase` | Purchase from sale |
| `sale_mrp` | Manufacturing from sale |
