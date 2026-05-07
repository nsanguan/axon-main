---
name: odoo-upgrade
description: Upgrade Odoo custom modules between versions. Use for: writing upgrade/migration scripts (pre/post/end phases), using upgrade-utils helper functions, renaming fields/models/xmlids, recomputing fields, migrating data, testing upgrade scripts, upgrading a customized database step by step.
argument-hint: Describe what you need to upgrade — e.g. "rename field on sale.order", "migrate data from old model", "write pre/post migration script for my_module"
---

# Odoo Upgrade — Developer Skill

**Source**: https://www.odoo.com/documentation/19.0/developer/reference/upgrades/upgrade_scripts.html  
**Source**: https://www.odoo.com/documentation/19.0/developer/howtos/upgrade_custom_db.html  
**Source**: https://www.odoo.com/documentation/19.0/developer/reference/upgrades/upgrade_utils.html

---

## 1. Upgrade Script Basics

An upgrade script is a Python file with a `migrate(cr, version)` function. Odoo invokes it automatically when a module is updated.

```python
import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    cr.execute("UPDATE res_partner SET name = name || '!'")
    _logger.info("Updated %s partners", cr.rowcount)
```

With ORM via upgrade-utils:
```python
from odoo.upgrade import util
import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    env = util.env(cr)
    partners = env["res.partner"].search([])
    for partner in partners:
        partner.name += "!"
    _logger.info("Updated %s partners", len(partners))
```

---

## 2. File Path & Naming Convention

```
my_module/
├── migrations/          # or 'upgrades/' (preferred from Odoo 13+)
│   └── 17.0.2.0/       # Odoo major version + module minor version
│       ├── pre-10-rename_fields.py
│       ├── pre-20-cleanup.py
│       ├── post-migrate.py
│       └── end-01-recompute.py
```

- Directory name: `{odoo_major}.{module_version}` e.g. `17.0.2.0`
- Scripts run only if installed version < script version ≤ updated version
- Lexical order within each phase

---

## 3. Phases of Upgrade Scripts

| Phase | When it runs | Use for |
|-------|-------------|---------|
| `pre-` | Before module is loaded | Rename/remove fields, rename models, structural DB changes |
| `post-` | After module & dependencies are loaded | Data migration, recompute fields, update records from XML |
| `end-` | After ALL modules are updated | Cross-module operations |

**Execution order example for one module:**
1. `pre-10-do_something.py`
2. `pre-20-something_else.py`
3. `post-do_something.py`
4. `post-something.py`
5. `end-01-migrate.py`
6. `end-migrate.py`

---

## 4. Upgrade Utils — Installation

```bash
# Clone and use via --upgrade-path
./odoo-bin --upgrade-path=/path/to/upgrade-util/src,/path/to/my/upgrades [...]

# Or install via pip (for Odoo.sh or pipenv)
python3 -m pip install git+https://github.com/odoo/upgrade-util@master
```

In `requirements.txt` (for Odoo.sh):
```
odoo_upgrade @ git+https://github.com/odoo/upgrade-util@master
```

Import in any upgrade script:
```python
from odoo.upgrade import util

def migrate(cr, version):
    # use util.* functions
```

---

## 5. Upgrade Utils — Key Functions

### 5.1 Modules

```python
# Check if module is installed
util.modules_installed(cr, "sale", "stock")  # → bool
util.module_installed(cr, "sale")             # → bool

# Rename a module
util.rename_module(cr, "old_name", "new_name")

# Merge module into another
util.merge_module(cr, "old_module", "target_module")

# Force install a module
util.force_install_module(cr, "my_module")

# Remove a module completely
util.remove_module(cr, "old_module")

# Move model from one module to another
util.move_model(cr, "my.model", "from_module", "to_module")
```

> **Note**: Module operations should go in a `pre-` script of the `base` module.

### 5.2 Models

```python
# Rename a model (updates all DB references)
util.rename_model(cr, "old.model", "new.model")

# Remove a model and its references
util.remove_model(cr, "obsolete.model")

# Merge source model into target model
util.merge_model(cr, "source.model", "target.model")

# Remove an inherited mixin from a model
util.remove_inherit_from_model(cr, "my.model", "mail.thread")
```

> **Best practice**: Model operations in `pre-` scripts.

### 5.3 Fields

```python
# Rename a field (updates filters, domains, server actions, etc.)
util.rename_field(cr, "sale.order", "old_field", "new_field")

# Remove a field and all references
util.remove_field(cr, "sale.order", "obsolete_field")

# Invert a boolean field
util.invert_boolean_field(cr, "res.partner", "is_inactive", "active")

# Convert Many2one to Many2many
util.convert_m2o_field_to_m2m(cr, "sale.order", "tag_id", new_name="tag_ids")

# Change selection field values mapping
util.change_field_selection_values(cr, "sale.order", "state", {
    "old_value": "new_value"
})

# Move field ownership to another module
util.move_field_to_module(cr, "sale.order", "my_field", "old_module", "new_module")
```

### 5.4 Records & XML IDs

```python
# Rename an external identifier (xml_id)
util.rename_xmlid(cr, "module.old_xmlid", "module.new_xmlid")

# Remove a record by xml_id
util.remove_record(cr, "module.xml_id")

# Remove a view and all descendants
util.remove_view(cr, xml_id="module.view_xml_id")

# Update a record from its XML definition (ignores noupdate)
util.update_record_from_xml(cr, "module.xml_id")

# Get record ID from xml_id
record_id = util.ref(cr, "module.xml_id")

# Force noupdate flag
util.force_noupdate(cr, "module.xml_id", noupdate=True)

# Rename xml_id with collision handling
util.rename_xmlid(cr, "old.xmlid", "new.xmlid", on_collision="merge")
```

Edit a view arch in-place:
```python
with util.skippable_cm(), util.edit_view(cr, "module.view_xml_id") as arch:
    arch.attrib["string"] = "My Updated Form"
```

Replace all record references:
```python
util.replace_record_references_batch(cr, {old_id: new_id}, "res.partner")
```

### 5.5 ORM Helpers

```python
# Create ORM environment from cursor
env = util.env(cr)

# Recompute stored fields safely (chunked)
util.recompute_fields(cr, "sale.order", ["amount_total", "amount_tax"])
util.recompute_fields(cr, "sale.order", ["state"], ids=[1, 2, 3])

# Iterate large recordsets safely (chunked, auto-flush)
MyModel = util.env(cr)["sale.order"]
for record in util.iter_browse(MyModel, ids):
    record.my_field = "updated"

# Bulk update via ORM (creates in chunks safely)
util.iter_browse(MyModel, ids).create(values_list)
```

### 5.6 SQL Helpers

```python
# Safe SQL formatting (auto-quotes identifiers)
util.format_query(cr, "SELECT {col} FROM {table}", "id", table="res_users")

# Column existence check
util.column_exists(cr, "sale_order", "my_column")  # → bool
util.column_type(cr, "sale_order", "state")          # → 'varchar' etc.

# Create column if not exists
util.create_column(cr, "sale_order", "new_col", "integer")
util.create_column(cr, "sale_order", "partner_fk", "integer",
                   fk_table="res_partner", on_delete_action="SET NULL")

# Copy a column (backup before removal)
util.copy_column(cr, "sale_order", "old_field")  # → "old_field_upg_copy"

# Alter column type efficiently
util.alter_column_type(cr, "sale_order", "amount", "numeric(16,2)")

# Parallel query execution
util.parallel_execute(cr, [
    util.format_query(cr, "REINDEX TABLE {}", t) for t in tables
])

# Execute large update in parallel buckets
util.explode_execute(cr, """
    UPDATE sale_order SET state = 'cancel'
    WHERE date_order < '2020-01-01' AND {parallel_filter}
""", table="sale_order")

# Remove a table constraint
util.remove_constraint(cr, "sale_order", "my_constraint")

# Rename a table
util.rename_table(cr, "old_table", "new_table")

# Get column list
cols = util.get_columns(cr, "sale_order", ignore=("id", "create_date"))

# Bulk update table rows
util.bulk_update_table(cr, "res_users", "active", {42: False, 27: True})
util.bulk_update_table(cr, "res_users", ["active", "password"],
    {"admin": [True, "1234"], "demo": [True, "5678"]}, key_col="login")
```

### 5.7 Domain Helpers

```python
# Adapt all domain references when renaming a field
util.adapt_domains(cr, "sale.order", "old_field", "new_field")

# Normalize a domain
normalized = util.normalize_domain([("field", "=", True)])
```

### 5.8 Misc

```python
# Version checks
util.version_gte("17.0")              # is current >= 17.0?
util.version_between("16.0", "18.0")  # is current in [16.0, 18.0]?

# Split large iterables into chunks
for chunk in util.chunks(big_list, 1000, fmt=list):
    process(chunk)

# Import a function from another upgrade script
script = util.import_script("mymodule/17.0.1.0/pre-migrate.py")
script.my_util_function(cr)
```

---

## 6. Common Migration Patterns

### Rename field and migrate data
```python
# pre- script
from odoo.upgrade import util

def migrate(cr, version):
    util.rename_field(cr, "sale.order", "old_name", "new_name")
```

### Move data from removed model (post- script)
```python
def migrate(cr, version):
    # sale.subscription was merged into sale.order in Odoo 16
    cr.execute("""
        UPDATE sale_order so
        SET my_custom_col = ss.my_custom_col
        FROM sale_subscription ss
        WHERE ss.sale_order_id = so.id
    """)
```

### Recompute stored field after logic change
```python
# post- script
from odoo.upgrade import util

def migrate(cr, version):
    util.recompute_fields(cr, "account.move", ["amount_residual"])
```

### Update noupdate record from XML
```python
# post- or end- script
from odoo.upgrade import util

def migrate(cr, version):
    util.update_record_from_xml(cr, "my_module.my_record_xmlid")
```

### Conditional migration based on version
```python
from odoo.upgrade import util

def migrate(cr, version):
    if util.version_gte("17.0"):
        util.rename_field(cr, "sale.order", "field_v17", "field_new")
    else:
        util.rename_field(cr, "sale.order", "field_old", "field_new")
```

---

## 7. Upgrade Testing

### Directory structure
```
myupgrades/
└── mymodule/
    ├── 18.0.1.1.2/
    │   └── pre-myupgrade.py
    └── tests/
        ├── __init__.py
        └── test_myupgrade.py
```

### UpgradeCase (for testing script logic)
```python
from odoo.upgrade.testing import UpgradeCase, change_version

@change_version("18.0")
class DeactivateBobUsers(UpgradeCase):
    def prepare(self):
        u = self.env["res.users"].create({"login": "bob", "name": "Bob"})
        return u.id  # passed to check()

    def check(self, uid):
        self.env.cr.execute(
            "SELECT id FROM res_users WHERE id=%s AND NOT active", [uid]
        )
        self.assertEqual(self.env.cr.rowcount, 1)
```

### IntegrityCase (for production invariant checks)
```python
from odoo.upgrade.testing import IntegrityCase

class NoNewUsers(IntegrityCase):
    def invariant(self):
        return self.env["res.users"].search_count([])
```

### Running upgrade tests
```bash
# Step 1: Prepare test data
./odoo-bin -d DB --test-tags=upgrade.test_prepare \
  --upgrade-path=~/upgrade-util/src,~/myupgrades \
  --addons=~/odoo/18.0/addons,~/mymodules --stop

# Step 2: Upgrade modules
./odoo-bin -d DB -u mymodule \
  --upgrade-path=~/upgrade-util/src,~/myupgrades \
  --addons=~/odoo/18.0/addons,~/mymodules --stop

# Step 3: Check upgraded data
./odoo-bin -d DB --test-tags=upgrade.test_check \
  --upgrade-path=~/upgrade-util/src,~/myupgrades \
  --addons=~/odoo/18.0/addons,~/mymodules --stop
```

---

## 8. Step-by-Step: Upgrading a Customized Database

1. **Stop developments** — freeze codebase, remove redundancy with new Odoo standard features
2. **Request upgraded test DB** — via https://upgrade.odoo.com or CLI
3. **Empty DB validation** — install custom modules on empty new-version DB; fix tracebacks, test, clean code, run standard tests
4. **Upgraded DB validation** — write upgrade scripts for data migration, test on the upgraded DB
5. **Testing & rehearsal** — thorough end-to-end testing, repeat upgraded DB requests until clean
6. **Production upgrade** — upgrade.odoo.com → purpose=Production

### CLI upgrade (on-premise)
```bash
# Upgrade a module on existing DB
./odoo-bin -d mydb -u my_module --upgrade-path=/path/to/upgrades --stop-after-init

# With upgrade-util
./odoo-bin -d mydb -u my_module \
  --upgrade-path=/path/to/upgrade-util/src,/path/to/my/upgrades \
  --addons-path=/path/to/addons --stop-after-init
```

---

## 9. Common Issues During Upgrade

| Issue | Resolution |
|-------|-----------|
| Disabled views in upgraded DB | Reactivate via upgrade script with `util.edit_view()` or `util.remove_view()` |
| `noupdate` records not updated | Use `util.update_record_from_xml()` in post- script |
| XPath broken after view changes | Update xpath in module or remove outdated inherited view |
| Field/model renamed in standard | Use `util.rename_field()` / `util.rename_model()` in pre- script |
| Computed field wrong values | Use `util.recompute_fields()` in post- script |
| Custom field on removed model | Copy data via SQL in post- script before model is dropped |
| Module dependency no longer exists | Use `util.merge_module()` or `util.remove_module()` |

---

## 10. Reference Links

- [Upgrade scripts reference](https://www.odoo.com/documentation/19.0/developer/reference/upgrades/upgrade_scripts.html)
- [Upgrade utils reference](https://www.odoo.com/documentation/19.0/developer/reference/upgrades/upgrade_utils.html)
- [How-to: Upgrade a customized database](https://www.odoo.com/documentation/19.0/developer/howtos/upgrade_custom_db.html)
- [Administration: Upgrade](https://www.odoo.com/documentation/19.0/administration/upgrade.html)
- [upgrade-util GitHub](https://github.com/odoo/upgrade-util/)
- [Odoo Release Notes](https://www.odoo.com/odoo.com/page/release-notes)
