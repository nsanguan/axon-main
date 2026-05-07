---
name: odoo-data-migration
description: 'Import, export, and migrate data in Odoo. Use for: importing records from CSV/Excel, loading initial data via XML data files, migrating data between databases, using base_import module, writing migration scripts, export to CSV from UI, loading demo/initial data, data transformation for migration.'
argument-hint: 'Describe the data task (e.g. "import 500 customers from CSV" or "migrate sale orders from old database")'
---

# Odoo Data Migration & Import/Export

## Relevant Modules
- `base_import` — CSV/Excel import UI: `/u01/erp/Odoo/odoo-server/addons/base_import/`
- `base_import_module` — Install modules as zip
- `attachment_indexation` — File content indexing

## Methods

| Method | Best For |
|--------|----------|
| UI CSV Import | Small-medium datasets, one-time import |
| XML Data Files | Module initial/demo data, config records |
| Python Script (shell) | Complex transformations, large datasets |
| External API (XML-RPC) | Integration with external systems |
| PostgreSQL COPY | Very large datasets, bulk inserts |

---

## 1. UI CSV Import

### Export from Odoo (CSV)
1. Open list view of the model (e.g. Contacts, Products)
2. Select records → Action → Export
3. Choose fields → Download CSV/XLSX

### Prepare CSV for Import
- First row: field technical names (or labels — Odoo matches both)
- Use external IDs (`.id` column) to update existing records
- Relational fields: use External ID or `name_search` value

Example `res.partner` import CSV:
```csv
External ID,Name,Street,City,Country/Country Code,Email,Phone,Customer Rank,Supplier Rank
my_module.partner_acme,ACME Corp,123 Main St,New York,US,info@acme.com,+1-555-0100,1,0
my_module.partner_tech,TechCorp,456 Elm Ave,Chicago,US,info@tech.com,+1-555-0200,1,1
```

### Import Steps (UI)
1. Open the model list view
2. Action → Import → Upload file
3. Map columns if not matched automatically
4. Click "Test Import" then "Import"

---

## 2. XML Data Files (Module Data)

### Record creation in XML
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <data noupdate="0">  <!-- noupdate="1" = don't overwrite on module upgrade -->

        <!-- Simple record -->
        <record id="product_laptop" model="product.template">
            <field name="name">Laptop Pro</field>
            <field name="type">consu</field>
            <field name="list_price">999.99</field>
            <field name="categ_id" ref="product.product_category_all"/>
        </record>

        <!-- Record with many2many -->
        <record id="res_partner_eraowl" model="res.partner">
            <field name="name">EraOwl Customer</field>
            <field name="customer_rank">1</field>
            <field name="email">contact@eraowl.com</field>
            <field name="category_id" eval="[(4, ref('base.res_partner_category_0'))]"/>
        </record>

        <!-- Function call (server action) -->
        <function model="res.partner" name="write">
            <value eval="[ref('base.res_partner_1')]"/>
            <value eval="{'comment': 'Updated by data file'}"/>
        </function>

    </data>
</odoo>
```

### Register in manifest
```python
'data': [
    'data/initial_data.xml',  # Loaded on install/upgrade
],
'demo': [
    'data/demo_data.xml',     # Only loaded in demo mode
],
```

---

## 3. Python Migration Script (Shell)

For large or complex migrations:

```python
# migration_script.py — run via Odoo shell
import sys
import odoo
from odoo import api, SUPERUSER_ID

# Setup
odoo.tools.config.parse_config(['--config=/u01/erp/Odoo/odoo.conf', '--database=mydb'])
registry = odoo.registry('mydb')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Example: migrate partners from CSV
    import csv
    with open('/tmp/partners.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Find or create
            partner = env['res.partner'].search([('ref', '=', row['ref'])], limit=1)
            if partner:
                partner.write({
                    'name': row['name'],
                    'email': row['email'],
                })
            else:
                env['res.partner'].create({
                    'name': row['name'],
                    'email': row['email'],
                    'ref': row['ref'],
                    'customer_rank': 1,
                })
    cr.commit()
    print("Migration complete")
```

Run:
```bash
/u01/erp/Odoo/venv/bin/python migration_script.py
```

---

## 4. Module Migration Scripts

For upgrading modules between Odoo versions, place scripts in `migrations/`:

```
my_module/
└── migrations/
    └── 19.4.2.0.0/
        ├── pre-migrate.py   # Before ORM update
        └── post-migrate.py  # After ORM update
```

```python
# migrations/19.4.2.0.0/post-migrate.py
import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    if not version:
        return  # fresh install, nothing to migrate
    
    _logger.info("Running post-migration for version %s", version)
    
    # Direct SQL for performance
    cr.execute("""
        UPDATE my_model
        SET new_field = old_field
        WHERE new_field IS NULL
    """)
    
    _logger.info("Migration done: %d rows updated", cr.rowcount)
```

---

## 5. Bulk Import via XML-RPC (External Data)

```python
import xmlrpc.client

url = 'http://localhost:8069'
db = 'mydb'
uid = common.authenticate(db, 'admin', 'password', {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Batch create (recommended for performance)
batch_size = 100
records_to_create = [
    {'name': f'Customer {i}', 'customer_rank': 1, 'email': f'c{i}@example.com'}
    for i in range(1000)
]

created_ids = []
for i in range(0, len(records_to_create), batch_size):
    batch = records_to_create[i:i+batch_size]
    ids = models.execute_kw(db, uid, 'password', 'res.partner', 'create', [batch])
    created_ids.extend(ids if isinstance(ids, list) else [ids])
    print(f"Created batch {i//batch_size + 1}")

print(f"Total created: {len(created_ids)}")
```

---

## 6. PostgreSQL Bulk COPY (Fastest for Large Data)

For very large datasets (>100k rows), use PostgreSQL COPY directly:

```bash
# Export from source DB
psql -h localhost -p 5435 -U odoo_admin sourcedb \
    -c "\COPY (SELECT id, name, email FROM res_partner WHERE customer_rank > 0) TO '/tmp/partners.csv' CSV HEADER"

# Import into target (after creating a staging table)
psql -h localhost -p 5435 -U odoo_admin targetdb \
    -c "\COPY staging_partners FROM '/tmp/partners.csv' CSV HEADER"

# Then process via SQL UPDATE/INSERT in Odoo shell
```

**IMPORTANT**: After direct SQL inserts, sequences must be updated:
```sql
SELECT setval('res_partner_id_seq', (SELECT MAX(id) FROM res_partner));
```

---

## 7. Exporting Data Programmatically

```python
# Export to CSV from shell
import csv

orders = env['sale.order'].search([('state', '=', 'sale')])
data = orders.read(['name', 'partner_id', 'date_order', 'amount_total'])

with open('/tmp/sales_export.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['name', 'partner_id', 'date_order', 'amount_total'])
    writer.writeheader()
    for row in data:
        # Many2one fields come as [id, name] tuples
        row['partner_id'] = row['partner_id'][1] if row['partner_id'] else ''
        writer.writerow(row)

print("Exported to /tmp/sales_export.csv")
```

---

## Common Pitfalls & Tips

- **External IDs**: Always use `module.xml_id` format for references
- **noupdate="1"**: Use for config records you don't want overwritten on upgrade
- **Batch size**: For XML-RPC creates, use batches of 50-200 records
- **Commit frequency**: In shell scripts, commit every 1000 records to avoid memory issues
- **Sequence conflicts**: After raw SQL inserts, always update PostgreSQL sequences
- **Company**: Multi-company setups require `company_id` on each record
- **Required fields**: Check model's required fields before bulk import; missing ones cause errors
- **Translations**: `translate=True` fields have separate entries in `ir.translation`
