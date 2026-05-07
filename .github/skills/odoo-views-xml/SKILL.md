---
name: odoo-views-xml
description: 'Create and modify Odoo XML views: form views, list/tree views, kanban views, search views, QWeb reports, and menu items. Use for: defining UI layouts, adding fields to forms, creating kanban columns, search filters and groupby, view inheritance (xpath), button actions, status bars, notebooks/tabs, one2many embedded lists, domain-based visibility.'
argument-hint: 'Describe the view to create or modify (e.g. "form view for my.model with a notebook and status bar")'
---

# Odoo Views (XML)

## Views Source Location
- Standard addons: `/u01/erp/Odoo/odoo-server/addons/<module>/views/`
- Example: `/u01/erp/Odoo/odoo-server/addons/sale/views/sale_order_views.xml`

## View File Registration

Register views in `__manifest__.py`:
```python
'data': [
    'views/my_model_views.xml',   # Always loaded
],
```

## Form View

```xml
<record id="view_my_model_form" model="ir.ui.view">
    <field name="name">my.model.form</field>
    <field name="model">my.model</field>
    <field name="arch" type="xml">
        <form string="My Model">
            <!-- Status bar -->
            <header>
                <button name="action_confirm" type="object" string="Confirm"
                        class="btn-primary" invisible="state != 'draft'"/>
                <button name="action_cancel" type="object" string="Cancel"
                        invisible="state not in ('draft', 'confirmed')"/>
                <field name="state" widget="statusbar" statusbar_visible="draft,confirmed,done"/>
            </header>
            <sheet>
                <!-- Smart buttons (top right) -->
                <div class="oe_button_box" name="button_box">
                    <button class="oe_stat_button" type="object" name="action_view_invoices"
                            icon="fa-pencil-square-o" invisible="invoice_count == 0">
                        <field name="invoice_count" string="Invoices" widget="statinfo"/>
                    </button>
                </div>
                <!-- Optional image/logo -->
                <widget name="web_ribbon" title="Archived" bg_color="text-bg-danger" invisible="active"/>
                <div class="oe_title">
                    <h1>
                        <field name="name" placeholder="Reference..."/>
                    </h1>
                </div>
                <group>
                    <group>
                        <field name="partner_id" options="{'no_create': True}"/>
                        <field name="date"/>
                    </group>
                    <group>
                        <field name="state" invisible="1"/>
                        <field name="currency_id" groups="base.group_multi_currency"/>
                        <field name="amount_total"/>
                    </group>
                </group>
                <!-- Notebook (tabs) -->
                <notebook>
                    <page string="Lines" name="lines">
                        <field name="line_ids">
                            <list editable="bottom">
                                <field name="product_id"/>
                                <field name="qty"/>
                                <field name="price_unit"/>
                                <field name="subtotal"/>
                            </list>
                        </field>
                    </page>
                    <page string="Other Info" name="other_info">
                        <group>
                            <field name="note"/>
                        </group>
                    </page>
                </notebook>
            </sheet>
            <!-- Chatter (requires mail.thread mixin) -->
            <chatter/>
        </form>
    </field>
</record>
```

## List (Tree) View

```xml
<record id="view_my_model_list" model="ir.ui.view">
    <field name="name">my.model.list</field>
    <field name="model">my.model</field>
    <field name="arch" type="xml">
        <list string="My Models" default_order="date desc"
              decoration-danger="state == 'cancel'"
              decoration-success="state == 'done'"
              decoration-muted="not active">
            <field name="name"/>
            <field name="partner_id"/>
            <field name="date"/>
            <field name="amount_total" sum="Total"/>
            <field name="state" widget="badge"
                   decoration-success="state == 'done'"
                   decoration-warning="state == 'confirmed'"
                   decoration-secondary="state == 'draft'"/>
        </list>
    </field>
</record>
```

## Kanban View

```xml
<record id="view_my_model_kanban" model="ir.ui.view">
    <field name="name">my.model.kanban</field>
    <field name="model">my.model</field>
    <field name="arch" type="xml">
        <kanban default_group_by="state" class="o_kanban_small_column">
            <field name="name"/>
            <field name="partner_id"/>
            <field name="state"/>
            <field name="amount_total"/>
            <templates>
                <t t-name="card">
                    <div class="oe_kanban_global_click">
                        <div class="oe_kanban_details">
                            <strong><field name="name"/></strong>
                            <div><field name="partner_id"/></div>
                            <div><field name="amount_total"/></div>
                        </div>
                    </div>
                </t>
            </templates>
        </kanban>
    </field>
</record>
```

## Search View

```xml
<record id="view_my_model_search" model="ir.ui.view">
    <field name="name">my.model.search</field>
    <field name="model">my.model</field>
    <field name="arch" type="xml">
        <search string="My Models">
            <field name="name" string="Reference"/>
            <field name="partner_id"/>
            <!-- Predefined filters -->
            <filter name="my_records" string="My Records"
                    domain="[('user_id', '=', uid)]"/>
            <filter name="draft" string="Draft"
                    domain="[('state', '=', 'draft')]"/>
            <separator/>
            <filter name="date_today" string="Today"
                    domain="[('date', '=', context_today().strftime('%Y-%m-%d'))]"/>
            <!-- Group by options -->
            <group expand="0" string="Group By">
                <filter name="group_by_partner" string="Partner"
                        context="{'group_by': 'partner_id'}"/>
                <filter name="group_by_state" string="State"
                        context="{'group_by': 'state'}"/>
                <filter name="group_by_date" string="Date"
                        context="{'group_by': 'date:month'}"/>
            </group>
        </search>
    </field>
</record>
```

## Window Action and Menu

```xml
<!-- Action -->
<record id="action_my_model" model="ir.actions.act_window">
    <field name="name">My Models</field>
    <field name="res_model">my.model</field>
    <field name="view_mode">list,form,kanban</field>
    <field name="context">{}</field>
    <field name="domain">[]</field>
    <field name="search_view_id" ref="view_my_model_search"/>
</record>

<!-- Top menu -->
<menuitem id="menu_my_module_root"
          name="My Module"
          sequence="50"/>

<!-- Sub menu -->
<menuitem id="menu_my_model"
          name="My Models"
          parent="menu_my_module_root"
          action="action_my_model"
          sequence="10"/>
```

## View Inheritance (XPath)

```xml
<record id="view_partner_form_custom" model="ir.ui.view">
    <field name="name">res.partner.form.custom</field>
    <field name="model">res.partner</field>
    <field name="inherit_id" ref="base.view_partner_form"/>
    <field name="arch" type="xml">
        <!-- Add field after existing field -->
        <xpath expr="//field[@name='phone']" position="after">
            <field name="custom_field"/>
        </xpath>

        <!-- Add field inside a group -->
        <xpath expr="//group[@name='grp_contact_info']" position="inside">
            <field name="custom_field2"/>
        </xpath>

        <!-- Replace an element -->
        <xpath expr="//field[@name='vat']" position="replace">
            <field name="vat" widget="char" placeholder="VAT Number"/>
        </xpath>

        <!-- Add attribute to existing element -->
        <xpath expr="//field[@name='name']" position="attributes">
            <attribute name="required">1</attribute>
        </xpath>

        <!-- Shorthand (no xpath needed for simple field references) -->
        <field name="email" position="after">
            <field name="custom_field3"/>
        </field>
    </field>
</record>
```

## Common Widgets

| Widget | Use |
|--------|-----|
| `statusbar` | State field progression display |
| `badge` | Colored badge for selection fields |
| `statinfo` | Counter in smart button |
| `monetary` | Currency-formatted amounts |
| `many2many_tags` | Tag chips for many2many |
| `handle` | Drag-to-reorder in list |
| `priority` | Star priority selector |
| `html` | Rich HTML editor |
| `binary` | File upload/download |
| `image` | Image field |
| `progressbar` | Percent bar |
| `phone` | Phone with SMS/call |
| `email` | Email link |
| `url` | Hyperlink |

## Conditional Visibility (`invisible`, `required`, `readonly`)

Uses Python-like expressions with field names (Odoo 17+):
```xml
<field name="field_name" invisible="state != 'draft'"/>
<field name="field_name" required="state == 'confirmed'"/>
<field name="field_name" readonly="state == 'done'"/>
<button name="action_x" type="object" string="Do X"
        invisible="state not in ('draft', 'confirmed')"/>
```

## QWeb Report

```xml
<template id="report_my_model">
    <t t-call="web.html_container">
        <t t-foreach="docs" t-as="doc">
            <t t-call="web.external_layout">
                <div class="page">
                    <h2><span t-field="doc.name"/></h2>
                    <p>Partner: <span t-field="doc.partner_id.name"/></p>
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Product</th>
                                <th>Qty</th>
                                <th>Price</th>
                            </tr>
                        </thead>
                        <tbody>
                            <t t-foreach="doc.line_ids" t-as="line">
                                <tr>
                                    <td><span t-field="line.product_id.name"/></td>
                                    <td><span t-field="line.qty"/></td>
                                    <td><span t-field="line.price_unit"/></td>
                                </tr>
                            </t>
                        </tbody>
                    </table>
                </div>
            </t>
        </t>
    </t>
</template>

<record id="action_report_my_model" model="ir.actions.report">
    <field name="name">My Model Report</field>
    <field name="model">my.model</field>
    <field name="report_type">qweb-pdf</field>
    <field name="report_name">my_module.report_my_model</field>
    <field name="report_file">my_module.report_my_model</field>
    <field name="binding_model_id" ref="model_my_model"/>
</record>
```
