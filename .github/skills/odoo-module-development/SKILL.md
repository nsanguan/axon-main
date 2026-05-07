---
name: odoo-module-development
description: 'Create, scaffold, and develop custom Odoo modules/addons. Use for: creating a new Odoo module, adding models to an existing module, writing __manifest__.py, setting up module structure, custom addon development, extending Odoo functionality, creating custom business logic in Python.'
argument-hint: 'Describe the module to create or extend (e.g. "create a module for equipment tracking")'
---

# Odoo Module Development

## Installation Details
- **Version**: Odoo 19.4 (alpha)
- **Addons Path**: `/u01/erp/Odoo/odoo-server/addons`
- **Server Path**: `/u01/erp/Odoo/odoo-server`
- **Venv**: `/u01/erp/Odoo/venv`
- **Config**: `/u01/erp/Odoo/odoo.conf`

## When to Use
- Creating a new Odoo custom module from scratch
- Adding models, views, or controllers to an existing module
- Extending core Odoo modules with inheritance
- Writing business logic in Python for Odoo

## Module Structure

Every Odoo addon must follow this directory layout:

```
my_module/
├── __init__.py              # Import all model sub-packages
├── __manifest__.py          # Module metadata and declaration
├── models/
│   ├── __init__.py          # Import each model file
│   └── my_model.py
├── views/
│   └── my_model_views.xml
├── security/
│   ├── ir.model.access.csv  # Model-level access rights
│   └── security.xml         # Groups and record rules (optional)
├── data/
│   └── data.xml             # Demo / initial data
├── controllers/
│   ├── __init__.py
│   └── main.py              # HTTP routes
├── report/
│   └── my_report.xml
└── static/
    └── description/
        └── icon.png
```

## Procedure

### 1. Scaffold a New Module (CLI)

```bash
cd /u01/erp/Odoo/odoo-server
/u01/erp/Odoo/venv/bin/python odoo-bin scaffold my_module /u01/erp/Odoo/odoo-server/addons
```

### 2. Write `__manifest__.py`

```python
{
    'name': "My Module",
    'summary': "Short one-line description",
    'description': """
    Longer description of the module
    """,
    'author': "EraOwl",
    'website': "https://www.eraowl.com",
    'category': 'Uncategorized',   # See /u01/erp/Odoo/odoo-server/addons/base/data/ir_module_category_data.xml
    'version': '19.4.1.0.0',       # <odoo_version>.<major>.<minor>.<patch>
    'depends': ['base'],            # List prerequisite modules
    'data': [
        'security/ir.model.access.csv',
        'views/my_model_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
```

### 3. Write `__init__.py` (Root)

```python
from . import models
from . import controllers  # if controllers exist
```

### 4. Write `models/__init__.py`

```python
from . import my_model
```

### 5. Define a Model (`models/my_model.py`)

```python
from odoo import api, fields, models

class MyModel(models.Model):
    _name = 'my.model'
    _description = 'My Model'
    _order = 'name asc'

    name = fields.Char(string='Name', required=True)
    active = fields.Boolean(default=True)
    date = fields.Date(string='Date')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    line_ids = fields.One2many('my.model.line', 'parent_id', string='Lines')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], default='draft', tracking=True)

    @api.depends('partner_id')
    def _compute_something(self):
        for record in self:
            record.something = record.partner_id.name

    def action_confirm(self):
        self.state = 'confirmed'
```

### 6. Model Inheritance

**Classical (extends existing model):**
```python
class ResPartner(models.Model):
    _inherit = 'res.partner'
    custom_field = fields.Char(string='Custom Field')
```

**Delegation (db table per model):**
```python
class MyExtension(models.Model):
    _name = 'my.extension'
    _inherits = {'res.partner': 'partner_id'}
    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')
```

**Prototype (copy fields, new table):**
```python
class MyModel(models.Model):
    _name = 'my.model'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Mixin
```

### 7. Common Mixins

| Mixin | Purpose |
|-------|---------|
| `mail.thread` | Chatter, message tracking |
| `mail.activity.mixin` | Activity scheduling |
| `portal.mixin` | Customer portal access |
| `utm.mixin` | UTM campaign tracking |
| `analytic.mixin` | Analytic distribution |

### 8. Install / Upgrade Module

```bash
cd /u01/erp/Odoo/odoo-server
# Install
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf -d <database> -i my_module --stop-after-init

# Upgrade
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf -d <database> -u my_module --stop-after-init
```

## Key File References

- [Models ORM reference](./references/orm.md)
- [Field types reference](./references/fields.md)
- [Template manifest](`/u01/erp/Odoo/odoo-server/odoo/cli/templates/default/__manifest__.py.template`)
- [Template model](`/u01/erp/Odoo/odoo-server/odoo/cli/templates/default/models/models.py.template`)
- [Example: sale.order](`/u01/erp/Odoo/odoo-server/addons/sale/models/sale_order.py`)
- [Example: account module](`/u01/erp/Odoo/odoo-server/addons/account/__manifest__.py`)
