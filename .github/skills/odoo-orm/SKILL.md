---
name: odoo-orm
description: 'Work with the Odoo ORM: models, fields, decorators, domains, environments, recordsets, search, create, write, unlink. Use for: defining field types, writing @api.depends, @api.constrains, @api.onchange, building domain filters, working with Many2one/One2many/Many2many, recordset operations, environment context, sudo, ref.'
argument-hint: 'Describe the ORM task (e.g. "search all confirmed sales orders for partner X")'
---

# Odoo ORM

## ORM Source Paths
- Models: `/u01/erp/Odoo/odoo-server/odoo/orm/models.py`
- Fields: `/u01/erp/Odoo/odoo-server/odoo/orm/fields.py`
- Decorators/API: `/u01/erp/Odoo/odoo-server/odoo/orm/decorators.py`
- Domains: `/u01/erp/Odoo/odoo-server/odoo/orm/domains.py`
- Environments: `/u01/erp/Odoo/odoo-server/odoo/orm/environments.py`
- Commands: `/u01/erp/Odoo/odoo-server/odoo/orm/commands.py`

## Model Types

| Class | Table | Use Case |
|-------|-------|----------|
| `models.Model` | Permanent DB table | Standard persistent records |
| `models.TransientModel` | Temporary, auto-cleaned | Wizards, one-time actions |
| `models.AbstractModel` | None (mixin only) | Shared behavior via `_inherit` |

## Field Types

### Basic Fields
```python
name      = fields.Char(string='Name', required=True, size=128, translate=True)
descr     = fields.Text(string='Description')
html      = fields.Html(string='Notes', sanitize=True)
count     = fields.Integer(string='Count', default=0)
amount    = fields.Float(string='Amount', digits=(16, 2))
price     = fields.Monetary(string='Price', currency_field='currency_id')
active    = fields.Boolean(default=True)
date      = fields.Date(string='Date')
datetime  = fields.Datetime(string='Datetime')
```

### Relational Fields
```python
partner_id   = fields.Many2one('res.partner', string='Partner', ondelete='restrict')
line_ids     = fields.One2many('my.line', 'parent_id', string='Lines')
tag_ids      = fields.Many2many('res.partner.category', string='Tags')
currency_id  = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
```

### Selection and Binary
```python
state = fields.Selection([
    ('draft', 'Draft'), ('done', 'Done')
], default='draft', tracking=True)
image = fields.Binary(string='Image', attachment=True)
```

### Computed Fields
```python
total = fields.Float(compute='_compute_total', store=True, readonly=True)
name_display = fields.Char(compute='_compute_name_display')  # not stored

@api.depends('price', 'quantity')
def _compute_total(self):
    for rec in self:
        rec.total = rec.price * rec.quantity
```

### Related Fields (Shortcut)
```python
partner_name = fields.Char(related='partner_id.name', string='Partner Name', store=True)
```

## API Decorators

```python
from odoo import api

# Computed field dependency
@api.depends('field1', 'field2')
def _compute_something(self): ...

# Onchange (UI only, not triggered on create/write)
@api.onchange('partner_id')
def _onchange_partner(self):
    if self.partner_id:
        self.pricelist_id = self.partner_id.property_product_pricelist

# Constraint validation
@api.constrains('date_start', 'date_end')
def _check_dates(self):
    for rec in self:
        if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
            raise ValidationError("Start date must be before end date.")

# Model-level constraint (called on create, write, unlink)
@api.model_create_multi
def create(self, vals_list):
    for vals in vals_list:
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('my.seq') or 'New'
    return super().create(vals_list)

# Returns single instance (not recordset)
@api.model
def some_model_method(self): ...
```

## CRUD Operations

```python
# Search
records = self.env['sale.order'].search([('state', '=', 'sale'), ('partner_id', '=', partner.id)], limit=10, order='date_order desc')

# Search with count
count = self.env['sale.order'].search_count([('state', '=', 'draft')])

# Read (returns list of dicts)
data = self.env['res.partner'].search_read([('customer_rank', '>', 0)], fields=['name', 'email'])

# Create (prefer model_create_multi)
record = self.env['sale.order'].create({'partner_id': partner.id, 'state': 'draft'})

# Write
record.write({'state': 'sale', 'date_order': fields.Datetime.now()})

# Unlink
record.unlink()

# Browse by ID(s)
record = self.env['res.partner'].browse(42)
records = self.env['res.partner'].browse([1, 2, 3])
```

## Domain Filters

```python
# Operators: =, !=, <, >, <=, >=, like, ilike, in, not in, child_of, parent_of
# Logical: '&' (default AND), '|' (OR), '!' (NOT)

domain = [('state', '=', 'sale'), ('amount_total', '>', 1000)]

# OR condition
domain = ['|', ('name', 'ilike', 'test'), ('ref', 'ilike', 'test')]

# Combined AND/OR
domain = ['&', ('state', '=', 'sale'), '|', ('partner_id.country_id.code', '=', 'US'), ('amount_total', '>', 5000)]

# Programmatic Domain object (Odoo 19)
from odoo.fields import Domain
d = Domain([('state', '=', 'sale')]) & Domain([('amount_total', '>', 1000)])
```

## Many2many Commands

```python
from odoo.fields import Command

# Replace all with new list
rec.write({'tag_ids': [Command.set([1, 2, 3])]})

# Add link to existing record
rec.write({'tag_ids': [Command.link(4)]})

# Remove a link
rec.write({'tag_ids': [Command.unlink(4)]})

# Create and link a new record
rec.write({'tag_ids': [Command.create({'name': 'New Tag'})]})

# Remove all links
rec.write({'tag_ids': [Command.clear()]})
```

## One2many Commands

```python
from odoo.fields import Command

rec.write({'line_ids': [
    Command.create({'product_id': 1, 'qty': 2.0}),   # Add new line
    Command.update(line.id, {'qty': 5.0}),            # Update existing line
    Command.delete(line.id),                          # Delete a line
]})
```

## Environment and Context

```python
# Current environment
env = self.env
user = env.user              # res.users record
company = env.company        # res.company record
lang = env.lang              # e.g. 'en_US'
today = fields.Date.today()

# Superuser bypass
rec.sudo().write({'field': value})

# With context
rec.with_context(lang='fr_FR').name_get()
rec.with_context({'no_recompute': True}).write({'field': value})

# Reference record by XML ID
partner = self.env.ref('base.res_partner_1')

# New instance with different company
rec.with_company(other_company)
```

## Recordset Operations

```python
# Set operations
combined = recordset1 | recordset2   # union
common   = recordset1 & recordset2   # intersection
diff     = recordset1 - recordset2   # difference

# Mapping
names = records.mapped('name')          # list of values
partners = records.mapped('partner_id') # recordset of related

# Filtering
confirmed = records.filtered(lambda r: r.state == 'confirmed')
confirmed = records.filtered('active')  # boolean shorthand

# Sorting
sorted_records = records.sorted('date_order', reverse=True)
sorted_records = records.sorted(key=lambda r: r.amount_total)
```

## Common Exceptions

```python
from odoo.exceptions import UserError, ValidationError, AccessError, MissingError

raise UserError("Something went wrong. Please check the data.")
raise ValidationError("Invalid value for field X.")
```
