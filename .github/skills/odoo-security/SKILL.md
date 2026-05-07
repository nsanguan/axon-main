---
name: odoo-security
description: 'Configure Odoo access rights, groups, and record rules. Use for: creating security groups, defining model-level access (ir.model.access.csv), writing record rules for row-level security, assigning menu visibility to groups, multi-company rules, field-level access control, sudo bypass.'
argument-hint: 'Describe the security requirement (e.g. "only managers can delete records" or "users can only see their own records")'
---

# Odoo Security

## Security Source Examples
- `/u01/erp/Odoo/odoo-server/addons/sale/security/`
- `/u01/erp/Odoo/odoo-server/addons/account/security/`
- Base groups: `/u01/erp/Odoo/odoo-server/addons/base/security/base_groups.xml`

## Security Architecture

```
Groups (ir.res.groups)
  └── Users are assigned to groups
  
ir.model.access (access rights)
  └── Read/Write/Create/Unlink per model per group
  
Record Rules (ir.rule)
  └── Domain-based row-level filtering per model per group
```

## 1. Define Groups (`security/security.xml`)

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data>
        <!-- Base user group -->
        <record id="group_my_module_user" model="res.groups">
            <field name="name">User</field>
            <field name="category_id" ref="base.module_category_my_module"/>
            <field name="implied_ids" eval="[(4, ref('base.group_user'))]"/>
        </record>

        <!-- Manager group (implies user) -->
        <record id="group_my_module_manager" model="res.groups">
            <field name="name">Manager</field>
            <field name="category_id" ref="base.module_category_my_module"/>
            <field name="implied_ids" eval="[(4, ref('group_my_module_user'))]"/>
            <field name="users" eval="[(4, ref('base.user_root')), (4, ref('base.user_admin'))]"/>
        </record>
    </data>
</odoo>
```

Register in `__manifest__.py`:
```python
'data': [
    'security/security.xml',
    'security/ir.model.access.csv',
    ...
]
```

## 2. Model Access Rights (`security/ir.model.access.csv`)

Column order: `id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink`

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_my_model_user,my.model user,model_my_model,my_module.group_my_module_user,1,1,1,0
access_my_model_manager,my.model manager,model_my_model,my_module.group_my_module_manager,1,1,1,1
access_my_model_public,my.model public,model_my_model,,1,0,0,0
```

**Naming convention for model_id:id**: Replace `.` with `_` and prefix with `model_`. 
- Model `my.model` → `model_my_model`
- Model `sale.order` → `model_sale_order`
- Model `account.move` → `model_account_move`

**Permissions**: 1 = allowed, 0 = denied. No group = applies to all (public).

## 3. Record Rules (`security/security.xml`)

```xml
<!-- Personal records: users see only their own -->
<record id="rule_my_model_personal" model="ir.rule">
    <field name="name">My Model: Personal</field>
    <field name="model_id" ref="model_my_model"/>
    <field name="domain_force">[('user_id', '=', user.id)]</field>
    <field name="groups" eval="[(4, ref('my_module.group_my_module_user'))]"/>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="True"/>
    <field name="perm_unlink" eval="False"/>
</record>

<!-- Managers see all records -->
<record id="rule_my_model_manager_all" model="ir.rule">
    <field name="name">My Model: Manager All</field>
    <field name="model_id" ref="model_my_model"/>
    <field name="domain_force">[(1, '=', 1)]</field>  <!-- No restriction -->
    <field name="groups" eval="[(4, ref('my_module.group_my_module_manager'))]"/>
</record>

<!-- Multi-company rule -->
<record id="rule_my_model_company" model="ir.rule">
    <field name="name">My Model: Company</field>
    <field name="model_id" ref="model_my_model"/>
    <field name="domain_force">['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]</field>
    <field name="perm_read" eval="True"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="True"/>
    <field name="perm_unlink" eval="True"/>
</record>
```

### Domain Variables in Record Rules

| Variable | Description |
|----------|-------------|
| `user` | `res.users` record of current user |
| `user.id` | Current user ID |
| `company_id` | Current company ID |
| `company_ids` | List of allowed company IDs |
| `time` | Python `time` module |

## 4. Menu Visibility by Group

```xml
<menuitem id="menu_my_model_config"
          name="Configuration"
          parent="menu_my_module_root"
          sequence="100"
          groups="my_module.group_my_module_manager"/>
```

## 5. Field-Level Groups in Views

```xml
<field name="cost_price" groups="my_module.group_my_module_manager"/>
<button name="action_delete_all" type="object" string="Reset All"
        groups="base.group_system"/>
```

## 6. Field-Level Access in Python

```python
from odoo import fields

cost_price = fields.Float(
    string='Cost Price',
    groups='my_module.group_my_module_manager',  # Only this group can read/write
)
```

## 7. Programmatic Access Control

```python
# Check if user is in group
if self.env.user.has_group('my_module.group_my_module_manager'):
    # allowed
    pass

# Bypass access rules (use with caution)
records_all = self.env['my.model'].sudo().search([])

# Raise access error
from odoo.exceptions import AccessError
raise AccessError("You are not allowed to perform this action.")
```

## 8. Common Base Groups

| XML ID | Description |
|--------|-------------|
| `base.group_user` | Internal user (employee) |
| `base.group_portal` | Portal user (customer) |
| `base.group_public` | Public/anonymous |
| `base.group_system` | Administrator |
| `base.group_erp_manager` | ERP Manager |
| `base.group_multi_company` | Multi-company |
| `base.group_multi_currency` | Multi-currency |

## 9. Superuser vs sudo()

```python
# sudo() runs with superuser privileges (bypasses ACL and record rules)
# Use only for technical operations that must bypass user restrictions
env['ir.attachment'].sudo().create({...})

# NEVER expose sudo() results directly to user without re-applying security
# Wrong: return self.sudo().search(domain)  # user sees data they shouldn't
# Right: return self.search(domain)         # user's own rights apply
```

## Security Checklist

- [ ] `ir.model.access.csv` exists for every model
- [ ] Groups defined with correct implications
- [ ] Record rules have correct domain expressions
- [ ] Multi-company `company_id` field and rule for shared models
- [ ] `sudo()` usage is audited and justified
- [ ] Sensitive fields have `groups=` attribute
- [ ] Admin-only menus have `groups="base.group_system"`
