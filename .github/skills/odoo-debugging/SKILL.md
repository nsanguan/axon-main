---
name: odoo-debugging
description: 'Debug Odoo issues: tracing errors, reading logs, using the Odoo shell, writing unit tests, enabling debug mode, profiling performance, diagnosing SQL queries, analyzing stack traces. Use for: fixing Python errors in Odoo, testing business logic, investigating database queries, inspecting model state, resolving view or field errors.'
argument-hint: 'Describe the problem to debug (e.g. "traceback in sale order confirmation" or "slow query on res.partner")'
---

# Odoo Debugging

## Server Paths
- Binary: `/u01/erp/Odoo/odoo-server/odoo-bin`
- Config: `/u01/erp/Odoo/odoo.conf`
- Python: `/u01/erp/Odoo/venv/bin/python`

## 1. Enable Debug Mode (UI)

Add `?debug=1` to the URL:
```
http://localhost:8069/web?debug=1
http://localhost:8069/web?debug=assets   # also recompiles JS/CSS
```

Or via Settings → Activate Developer Mode.

## 2. Log Levels

Start server with increased logging:
```bash
# Debug all Odoo logs
/u01/erp/Odoo/venv/bin/python /u01/erp/Odoo/odoo-server/odoo-bin \
    -c /u01/erp/Odoo/odoo.conf \
    --log-level=debug

# Debug specific module only
/u01/erp/Odoo/venv/bin/python /u01/erp/Odoo/odoo-server/odoo-bin \
    -c /u01/erp/Odoo/odoo.conf \
    --log-handler=odoo.addons.my_module:DEBUG \
    --log-handler=odoo.models:DEBUG

# Log SQL queries (WARNING: very verbose)
/u01/erp/Odoo/venv/bin/python /u01/erp/Odoo/odoo-server/odoo-bin \
    -c /u01/erp/Odoo/odoo.conf \
    --log-handler=odoo.sql_db:DEBUG
```

In Python code, use standard logging:
```python
import logging
_logger = logging.getLogger(__name__)

_logger.debug("Debug: value = %s", value)
_logger.info("Processing record %d", record.id)
_logger.warning("Unexpected state: %s", state)
_logger.error("Error processing record %d: %s", record.id, str(e))
```

## 3. Odoo Shell (Interactive Debugging)

```bash
/u01/erp/Odoo/venv/bin/python /u01/erp/Odoo/odoo-server/odoo-bin \
    shell -c /u01/erp/Odoo/odoo.conf -d <database>
```

Useful shell commands:
```python
# env is pre-initialized
# Inspect a model
order = env['sale.order'].browse(1)
print(order.read())

# Inspect fields
env['sale.order'].fields_get(['state', 'name', 'partner_id'])

# Check computed field
order.amount_total
order._compute_amount()

# Inspect SQL
env.cr.execute("SELECT id, name FROM sale_order WHERE state = 'sale' LIMIT 5")
rows = env.cr.fetchall()
print(rows)

# Trace method resolution
import inspect
print(inspect.getmro(type(order)))

# Get all methods/fields
print([m for m in dir(order) if not m.startswith('_')])

# Commit changes (needed for writes in shell)
env.cr.commit()

# Rollback (discard changes)
env.cr.rollback()
```

## 4. Python Debugger (pdb)

Insert a breakpoint in code:
```python
import pdb; pdb.set_trace()     # Classic breakpoint
breakpoint()                     # Python 3.7+ equivalent
```

Then start Odoo in the foreground (not as daemon). When breakpoint is hit:
- `n` — next line
- `s` — step into function
- `c` — continue
- `q` — quit debugger
- `p variable` — print variable
- `pp variable` — pretty-print

## 5. Writing Unit Tests

```python
# my_module/tests/test_my_model.py
from odoo.tests import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestMyModel(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})

    def test_create_record(self):
        record = self.env['my.model'].create({
            'name': 'Test',
            'partner_id': self.partner.id,
        })
        self.assertEqual(record.state, 'draft')
        self.assertTrue(record.name)

    def test_confirm(self):
        record = self.env['my.model'].create({
            'name': 'Test',
            'partner_id': self.partner.id,
        })
        record.action_confirm()
        self.assertEqual(record.state, 'confirmed')

    def test_invalid_dates(self):
        from odoo.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            self.env['my.model'].create({
                'name': 'Test',
                'partner_id': self.partner.id,
                'date_start': '2026-06-01',
                'date_end': '2026-01-01',  # end before start
            })
```

Run tests:
```bash
/u01/erp/Odoo/venv/bin/python /u01/erp/Odoo/odoo-server/odoo-bin \
    -c /u01/erp/Odoo/odoo.conf \
    -d <testdb> \
    --test-enable \
    --test-tags my_module \
    --stop-after-init \
    --log-level=test
```

## 6. Common Error Types

### AccessError
```
odoo.exceptions.AccessError: You do not have access to 'sale.order'. Contact your administrator.
```
**Fix**: Check `ir.model.access.csv` and record rules for the user's groups.

### MissingError / RecordNotFound
```
odoo.exceptions.MissingError: Record does not exist or has been deleted.
```
**Fix**: The record was deleted or not committed. Reload with `record.exists()`.

### ValidationError
```
odoo.exceptions.ValidationError: Constraint violated: CHECK...
```
**Fix**: Check `@api.constrains` methods and SQL CHECK constraints.

### UserError
```
odoo.exceptions.UserError: ...
```
**Fix**: Intentional user-facing error. Read the message. Check business logic.

### IntegrityError (psycopg2)
```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint
```
**Fix**: Duplicate record creation. Check model's `_sql_constraints`.

## 7. SQL Debugging

Direct SQL inspection:
```python
# In Odoo shell
env.cr.execute("""
    SELECT so.name, rp.name as partner, so.state, so.amount_total
    FROM sale_order so
    JOIN res_partner rp ON so.partner_id = rp.id
    WHERE so.state = 'sale'
    ORDER BY so.date_order DESC
    LIMIT 20
""")
for row in env.cr.dictfetchall():
    print(row)
```

From terminal:
```bash
psql -h localhost -p 5435 -U odoo_admin <database>
# Then run SQL queries
\d sale_order         # Describe table
\d+ sale_order_line   # Describe with details
```

## 8. Performance Profiling

```python
# In code: measure execution time
import time
start = time.time()
records = env['sale.order'].search([('state', '=', 'sale')])
elapsed = time.time() - start
_logger.info("Query took %.3f seconds", elapsed)
```

Enable `--log-handler=odoo.sql_db:DEBUG` to see all SQL with timing.

Use Odoo's built-in profiler:
- Debug mode → Settings → Technical → Profiler
- Or programmatically with `odoo.tools.profiler`

## 9. Check Module State

```python
# In shell: check if a module is installed
module = env['ir.module.module'].search([('name', '=', 'my_module')])
print(module.state)   # 'installed', 'uninstalled', 'to upgrade'

# Upgrade a module from shell (careful: commits to DB)
module.button_immediate_upgrade()
```

## 10. View Rendering Errors

```bash
# Check for XML view errors on server start - look for:
# odoo.addons.base.models.ir_ui_view: Could not render view
# SyntaxError in XML: ...

# Validate views from shell
env['ir.ui.view'].check_view_ids([view_id])

# Get the compiled arch for a view
view = env['ir.ui.view'].search([('model', '=', 'sale.order'), ('type', '=', 'form')], limit=1)
print(view.arch)
```
