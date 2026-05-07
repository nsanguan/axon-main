---
name: odoo-external-api
description: 'Connect to Odoo from external systems using XML-RPC or JSON-RPC APIs. Use for: reading Odoo data from Python/JavaScript/any language, creating records via API, calling Odoo methods remotely, building integrations, webhooks, API authentication, working with Odoo RPC endpoint.'
argument-hint: 'Describe the integration (e.g. "read all customer invoices from Python" or "create sale order via JSON-RPC")'
---

# Odoo External API

## Server Connection Details
- **URL**: `http://localhost:8069` (or `http://<server-ip>:8069`)
- **DB**: as configured in `/u01/erp/Odoo/odoo.conf`
- **Admin user**: `admin` with password from DB
- **RPC module**: `/u01/erp/Odoo/odoo-server/addons/rpc/`

## Odoo RPC Endpoints

| Endpoint | Protocol | Description |
|----------|----------|-------------|
| `/xmlrpc/2/common` | XML-RPC | Authentication (no login required) |
| `/xmlrpc/2/object` | XML-RPC | Model operations (requires auth) |
| `/web/dataset/call_kw` | JSON-RPC | Model operations |
| `/web/dataset/call_button` | JSON-RPC | Button actions |

## Python XML-RPC (Official Odoo Way)

```python
import xmlrpc.client

# Connection settings
url = 'http://localhost:8069'
db = 'mydb'
username = 'admin'
password = 'admin_password'

# 1. Authenticate
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
print(f"Authenticated as UID: {uid}")

# 2. Create models proxy
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Convenience shorthand
def call(model, method, *args, **kwargs):
    return models.execute_kw(db, uid, password, model, method, args, kwargs)
```

## XML-RPC CRUD Examples

```python
# SEARCH
partner_ids = call('res.partner', 'search', [('customer_rank', '>', 0)])
# With options
partner_ids = call('res.partner', 'search',
    [('customer_rank', '>', 0)],
    limit=10, offset=0, order='name asc'
)

# READ
partners = call('res.partner', 'read',
    partner_ids,
    ['name', 'email', 'phone', 'street']
)

# SEARCH + READ combined
partners = call('res.partner', 'search_read',
    [('customer_rank', '>', 0)],
    {'fields': ['name', 'email'], 'limit': 10}
)

# CREATE
new_id = call('res.partner', 'create', {
    'name': 'New Customer',
    'email': 'customer@example.com',
    'customer_rank': 1,
})

# WRITE (update)
call('res.partner', 'write', [new_id], {'phone': '+1234567890'})

# UNLINK (delete)
call('res.partner', 'unlink', [new_id])

# SEARCH COUNT
count = call('res.partner', 'search_count', [('customer_rank', '>', 0)])
```

## XML-RPC: Calling Custom Methods

```python
# Call any public method on a model
result = call('sale.order', 'action_confirm', [order_id])

# Call with kwargs
result = call('account.move', 'name_get', [invoice_id])

# Get fields metadata
fields_info = call('sale.order', 'fields_get',
    [], {'attributes': ['string', 'type', 'required']}
)
```

## Python JSON-RPC

```python
import requests
import json

url = 'http://localhost:8069'
db = 'mydb'
username = 'admin'
password = 'admin_password'

session = requests.Session()

# 1. Authenticate
auth_response = session.post(f'{url}/web/session/authenticate', json={
    'jsonrpc': '2.0',
    'method': 'call',
    'params': {
        'db': db,
        'login': username,
        'password': password,
    },
})
auth_data = auth_response.json()
uid = auth_data['result']['uid']

# 2. Call model method
def rpc_call(model, method, args=None, kwargs=None):
    response = session.post(f'{url}/web/dataset/call_kw', json={
        'jsonrpc': '2.0',
        'method': 'call',
        'params': {
            'model': model,
            'method': method,
            'args': args or [],
            'kwargs': kwargs or {},
        },
    })
    result = response.json()
    if 'error' in result:
        raise Exception(result['error'])
    return result['result']

# Example usage
partners = rpc_call('res.partner', 'search_read',
    [[['customer_rank', '>', 0]]],
    {'fields': ['name', 'email'], 'limit': 5}
)
```

## JavaScript / Node.js Example

```javascript
const xmlrpc = require('xmlrpc');  // npm install xmlrpc

const url = 'http://localhost:8069';
const db = 'mydb';
const username = 'admin';
const password = 'admin_password';

// Authenticate
const common = xmlrpc.createClient({ url: `${url}/xmlrpc/2/common` });

common.methodCall('authenticate', [db, username, password, {}], (err, uid) => {
    const object = xmlrpc.createClient({ url: `${url}/xmlrpc/2/object` });

    // Search partners
    object.methodCall('execute_kw', [
        db, uid, password,
        'res.partner', 'search_read',
        [[['customer_rank', '>', 0]]],
        { fields: ['name', 'email'], limit: 10 }
    ], (err, partners) => {
        console.log(partners);
    });
});
```

## API Key Authentication (Odoo 14+)

Instead of user password, generate an API key in Odoo:
1. Settings → Users → User → Security tab → API Keys
2. Use API key as the `password` in all RPC calls

```python
api_key = 'your_api_key_here'
uid = common.authenticate(db, username, api_key, {})
```

## Working with Binary Fields (Attachments)

```python
import base64

# Upload a file as attachment
with open('/path/to/file.pdf', 'rb') as f:
    file_data = base64.b64encode(f.read()).decode()

attachment_id = call('ir.attachment', 'create', {
    'name': 'document.pdf',
    'type': 'binary',
    'datas': file_data,
    'res_model': 'sale.order',
    'res_id': order_id,
})

# Download a file
attachment = call('ir.attachment', 'read', [attachment_id], ['name', 'datas'])[0]
file_bytes = base64.b64decode(attachment['datas'])
with open('/path/to/save.pdf', 'wb') as f:
    f.write(file_bytes)
```

## HTTP Controllers (Custom REST-like Endpoints)

```python
# In controllers/main.py
from odoo import http
from odoo.http import request
import json

class MyController(http.Controller):

    @http.route('/api/my_model', type='json', auth='user', methods=['GET'])
    def get_records(self):
        records = request.env['my.model'].search_read([], ['name', 'state'])
        return records

    @http.route('/api/my_model', type='json', auth='user', methods=['POST'])
    def create_record(self, **kwargs):
        record = request.env['my.model'].create(kwargs)
        return {'id': record.id, 'name': record.name}

    @http.route('/api/webhook', type='json', auth='public', csrf=False)
    def webhook_handler(self, **post):
        # Handle incoming webhook
        data = request.jsonrequest
        # Process data...
        return {'status': 'ok'}
```

## Common Domain Operators for API Calls

```python
# Note: Domains in API calls are passed as Python lists (not Domain objects)
domain = [
    ('state', '=', 'sale'),
    ('date_order', '>=', '2026-01-01'),
    ('partner_id.country_id.code', '=', 'US'),
]

# OR condition
domain = ['|', ('name', 'ilike', 'ACME'), ('ref', 'ilike', 'ACME')]

# Nested AND/OR
domain = ['&', ('state', '=', 'sale'), '|', ('amount_total', '>', 1000), ('priority', '=', '1')]
```

## Security Notes

- Always use HTTPS in production (never send credentials over plain HTTP)
- Use API keys instead of passwords where possible
- Apply least-privilege: use a dedicated API user with minimal rights
- Validate and sanitize all data received from external systems before creating/writing records
- Never expose the admin master password (`admin_passwd` in odoo.conf) via API
