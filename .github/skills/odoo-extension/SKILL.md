---
name: odoo-extension
description: Create and extend Odoo modules, expose REST/JSON endpoints via HTTP controllers, integrate external Agentic AI systems using the JSON-2 API, and build Odoo MCP (Model Context Protocol) server modules for specific agents (mcp-buyer-agent, mcp-warehouse-agent, mcp-hr-agent). Use for: creating new Odoo modules from scratch, writing HTTP controllers, building agent-compatible API endpoints, implementing MCP tool servers inside Odoo.
argument-hint: Describe what you need — e.g. "create mcp-buyer-agent module", "expose purchase order endpoint for AI agent", "new Odoo module with REST API", "MCP tool for warehouse operations"
---

# Odoo Extension — Developer Skill

**Sources**:
- https://www.odoo.com/documentation/19.0/developer/reference/backend/http.html
- https://www.odoo.com/documentation/19.0/developer/reference/external_api.html
- https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101.html

---

## 1. Creating a New Odoo Module

### Minimal module structure

```
my_module/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── my_model.py
├── views/
│   └── my_model_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
├── controllers/
│   ├── __init__.py
│   └── main.py
└── data/
    └── data.xml
```

### `__manifest__.py`

```python
{
    'name': 'My Module',
    'version': '19.0.1.0.0',
    'summary': 'Short description',
    'author': 'EraOwl',
    'category': 'Technical',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/my_model_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
```

### `models/my_model.py`

```python
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class MyModel(models.Model):
    _name = 'my.model'
    _description = 'My Model'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    line_ids = fields.One2many('my.model.line', 'parent_id', string='Lines')
    amount_total = fields.Float(compute='_compute_amount', store=True)

    @api.depends('line_ids.price_subtotal')
    def _compute_amount(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped('price_subtotal'))

    def action_confirm(self):
        self.ensure_one()
        self.state = 'confirmed'
```

### `security/ir.model.access.csv`

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_my_model_user,my.model user,model_my_model,base.group_user,1,1,1,0
access_my_model_manager,my.model manager,model_my_model,base.group_system,1,1,1,1
```

### Install / upgrade

```bash
# Install new module
/u01/erp/Odoo/odoo-server/odoo-bin -c /u01/erp/Odoo/odoo.conf -i my_module --stop-after-init

# Upgrade after changes
/u01/erp/Odoo/odoo-server/odoo-bin -c /u01/erp/Odoo/odoo.conf -u my_module --stop-after-init
```

---

## 2. HTTP Controllers (REST Endpoints)

Expose custom endpoints inside any Odoo module via `odoo.http.Controller`.

### Basic JSON controller

```python
# controllers/main.py
import json
from odoo import http
from odoo.http import request

class MyController(http.Controller):

    @http.route('/api/my_module/orders', type='jsonrpc', auth='bearer', methods=['POST'], csrf=False)
    def get_orders(self, domain=None, fields=None, limit=100, **kwargs):
        """Returns orders matching domain — callable by AI agents via bearer API key."""
        domain = domain or []
        fields = fields or ['name', 'state', 'partner_id', 'amount_total']
        records = request.env['sale.order'].search_read(domain, fields, limit=limit)
        return records

    @http.route('/api/my_module/order/<int:order_id>/confirm', type='jsonrpc', auth='bearer', methods=['POST'], csrf=False)
    def confirm_order(self, order_id, **kwargs):
        order = request.env['sale.order'].browse(order_id)
        if not order.exists():
            return {'error': 'Order not found'}
        order.action_confirm()
        return {'id': order.id, 'state': order.state}
```

### Route options

| Parameter | Values | Notes |
|-----------|--------|-------|
| `type` | `'jsonrpc'`, `'http'` | `jsonrpc` for JSON APIs (preferred for agents) |
| `auth` | `'bearer'`, `'user'`, `'public'`, `'none'` | `bearer` = API key auth — use for agents |
| `methods` | `['GET']`, `['POST']` etc. | HTTP verbs |
| `csrf` | `True`/`False` | Always `False` for API endpoints |
| `cors` | `'*'` | Enable CORS for cross-origin clients |
| `readonly` | `True`/`False` | Route to read-only DB replica |

### HTTP response helpers

```python
# JSON response
return request.make_json_response({'status': 'ok'}, status=200)

# Error response
return request.make_json_response({'error': 'Not found'}, status=404)

# Render QWeb template
return request.render('my_module.template_name', {'key': value})
```

---

## 3. Calling Odoo from External Agentic AI Systems (JSON-2 API)

Odoo 19 introduces the **JSON-2 API** at `/json/2/<model>/<method>`. This is the **preferred API for agent integrations**.

### Authentication

```python
# Create API key: Preferences → Account Security → New API Key
API_KEY = "your_api_key_here"  # load from env, never hardcode

headers = {
    "Authorization": f"bearer {API_KEY}",
    "X-Odoo-Database": "odoo_db",
    "Content-Type": "application/json",
    "User-Agent": "EraOwl-Agent/1.0",
}
```

### Common CRUD operations

```python
import requests

BASE_URL = "http://202.71.1.13:8069/json/2"  # adjust port as needed

# --- SEARCH ---
res = requests.post(f"{BASE_URL}/sale.order/search", headers=headers, json={
    "domain": [["state", "=", "sale"], ["partner_id.name", "ilike", "ACME"]],
    "context": {"lang": "en_US"},
})
order_ids = res.json()

# --- READ ---
res = requests.post(f"{BASE_URL}/sale.order/read", headers=headers, json={
    "ids": order_ids,
    "fields": ["name", "state", "amount_total", "partner_id"],
})
orders = res.json()

# --- SEARCH_READ (single transaction) ---
res = requests.post(f"{BASE_URL}/sale.order/search_read", headers=headers, json={
    "domain": [["state", "=", "draft"]],
    "fields": ["name", "partner_id", "amount_total"],
    "limit": 50,
})

# --- CREATE ---
res = requests.post(f"{BASE_URL}/sale.order/create", headers=headers, json={
    "vals": {"partner_id": 7, "order_line": [(0, 0, {
        "product_id": 12,
        "product_uom_qty": 2.0,
        "price_unit": 100.0,
    })]},
})
new_id = res.json()

# --- WRITE ---
requests.post(f"{BASE_URL}/sale.order/write", headers=headers, json={
    "ids": [42],
    "vals": {"note": "Updated by AI agent"},
})

# --- CALL BUSINESS METHOD ---
requests.post(f"{BASE_URL}/sale.order/action_confirm", headers=headers, json={
    "ids": [42],
})
```

### Error handling for agents

```python
def odoo_call(model, method, payload, headers):
    res = requests.post(f"{BASE_URL}/{model}/{method}", headers=headers, json=payload)
    if res.status_code == 401:
        raise Exception("Invalid API key — rotate the key in Odoo preferences")
    if res.status_code >= 400:
        err = res.json()
        raise Exception(f"Odoo error: {err.get('message', res.text)}")
    return res.json()
```

### Important transaction rule for agents

> Each JSON-2 call is its own SQL transaction. If an agent needs to do multiple related operations (e.g. create order + confirm + reserve stock), implement them as a **single Odoo method** in a custom module and call that one method from the agent. This guarantees atomicity.

```python
# BAD: three separate API calls (not atomic)
create_order()
confirm_order()
reserve_stock()

# GOOD: one custom method in Odoo that does all three
requests.post(f"{BASE_URL}/sale.order/action_create_confirm_reserve", headers=headers, json={...})
```

---

## 4. MCP Server Pattern — Building Odoo MCP Agent Modules

An **Odoo MCP module** exposes tools to AI agents via the [Model Context Protocol](https://modelcontextprotocol.io/) over HTTP. Each business domain gets its own Odoo addon that acts as an MCP server.

### MCP endpoint structure

```
POST /mcp/{agent_name}/tools/list     → list available tools
POST /mcp/{agent_name}/tools/call     → call a specific tool
POST /mcp/{agent_name}/resources/list → list available resources
POST /mcp/{agent_name}/resources/read → read a resource
```

### Base MCP controller (shared mixin)

```python
# addons/mcp_base/controllers/mcp_base.py
import json
from odoo import http
from odoo.http import request

class MCPBaseController(http.Controller):
    """Base MCP controller. Override _get_tools() and _call_tool() in subclasses."""

    _mcp_agent = None  # set in subclass, e.g. 'buyer'

    def _get_tools(self):
        """Return list of MCP tool definitions. Override in each agent module."""
        return []

    def _call_tool(self, tool_name, arguments):
        """Dispatch tool call. Override in each agent module."""
        raise ValueError(f"Unknown tool: {tool_name}")

    @http.route('/mcp/<string:agent>/tools/list', type='jsonrpc', auth='bearer', methods=['POST'], csrf=False)
    def tools_list(self, agent, **kwargs):
        if agent != self._mcp_agent:
            return request.make_json_response({'error': 'Wrong agent'}, status=404)
        return {"tools": self._get_tools()}

    @http.route('/mcp/<string:agent>/tools/call', type='jsonrpc', auth='bearer', methods=['POST'], csrf=False)
    def tools_call(self, agent, name, arguments=None, **kwargs):
        if agent != self._mcp_agent:
            return request.make_json_response({'error': 'Wrong agent'}, status=404)
        try:
            result = self._call_tool(name, arguments or {})
            return {"content": [{"type": "text", "text": json.dumps(result)}]}
        except Exception as e:
            return {"isError": True, "content": [{"type": "text", "text": str(e)}]}
```

---

## 5. mcp-buyer-agent

Handles purchase orders, RFQs, vendor management, and procurement operations.

```
addons/mcp_buyer_agent/
├── __init__.py
├── __manifest__.py
└── controllers/
    ├── __init__.py
    └── buyer_mcp.py
```

### `__manifest__.py`

```python
{
    'name': 'MCP Buyer Agent',
    'version': '19.0.1.0.0',
    'summary': 'MCP server for the AI Buyer Agent — purchase orders, RFQs, vendors',
    'depends': ['purchase', 'mcp_base'],
    'installable': True,
    'license': 'LGPL-3',
}
```

### `controllers/buyer_mcp.py`

```python
from odoo import http
from odoo.http import request
from .mcp_base import MCPBaseController

class BuyerMCPController(MCPBaseController):
    _mcp_agent = 'buyer'

    def _get_tools(self):
        return [
            {
                "name": "search_rfqs",
                "description": "Search Request for Quotations (RFQs) by state, vendor, or date",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "state": {"type": "string", "enum": ["draft", "sent", "to approve", "purchase", "done", "cancel"]},
                        "vendor_name": {"type": "string"},
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            },
            {
                "name": "create_rfq",
                "description": "Create a new Request for Quotation",
                "inputSchema": {
                    "type": "object",
                    "required": ["vendor_id", "lines"],
                    "properties": {
                        "vendor_id": {"type": "integer", "description": "res.partner ID of vendor"},
                        "lines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_id": {"type": "integer"},
                                    "qty": {"type": "number"},
                                    "price_unit": {"type": "number"},
                                },
                            },
                        },
                    },
                },
            },
            {
                "name": "confirm_purchase_order",
                "description": "Confirm a purchase order (RFQ → Purchase Order)",
                "inputSchema": {
                    "type": "object",
                    "required": ["order_id"],
                    "properties": {"order_id": {"type": "integer"}},
                },
            },
            {
                "name": "get_vendor_pricelists",
                "description": "Get product prices from a specific vendor",
                "inputSchema": {
                    "type": "object",
                    "required": ["vendor_id"],
                    "properties": {
                        "vendor_id": {"type": "integer"},
                        "product_ids": {"type": "array", "items": {"type": "integer"}},
                    },
                },
            },
        ]

    def _call_tool(self, tool_name, args):
        env = request.env
        if tool_name == "search_rfqs":
            domain = []
            if args.get('state'):
                domain.append(('state', '=', args['state']))
            if args.get('vendor_name'):
                domain.append(('partner_id.name', 'ilike', args['vendor_name']))
            orders = env['purchase.order'].search_read(
                domain,
                ['name', 'partner_id', 'state', 'amount_total', 'date_order'],
                limit=args.get('limit', 20),
            )
            return orders

        elif tool_name == "create_rfq":
            lines = [(0, 0, {
                'product_id': l['product_id'],
                'product_qty': l['qty'],
                'price_unit': l.get('price_unit', 0.0),
            }) for l in args['lines']]
            order = env['purchase.order'].create({
                'partner_id': args['vendor_id'],
                'order_line': lines,
            })
            return {'id': order.id, 'name': order.name, 'state': order.state}

        elif tool_name == "confirm_purchase_order":
            order = env['purchase.order'].browse(args['order_id'])
            order.button_confirm()
            return {'id': order.id, 'state': order.state}

        elif tool_name == "get_vendor_pricelists":
            domain = [('partner_id', '=', args['vendor_id'])]
            if args.get('product_ids'):
                domain.append(('product_id', 'in', args['product_ids']))
            lines = env['product.supplierinfo'].search_read(
                domain,
                ['product_id', 'price', 'min_qty', 'delay'],
            )
            return lines

        return super()._call_tool(tool_name, args)
```

---

## 6. mcp-warehouse-agent

Handles inventory, stock moves, picking operations, and warehouse management.

```
addons/mcp_warehouse_agent/
├── __init__.py
├── __manifest__.py
└── controllers/
    ├── __init__.py
    └── warehouse_mcp.py
```

### `controllers/warehouse_mcp.py`

```python
from odoo import http
from odoo.http import request
from .mcp_base import MCPBaseController

class WarehouseMCPController(MCPBaseController):
    _mcp_agent = 'warehouse'

    def _get_tools(self):
        return [
            {
                "name": "check_stock",
                "description": "Check current stock quantity for products",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_ids": {"type": "array", "items": {"type": "integer"}},
                        "location_id": {"type": "integer", "description": "stock.location ID"},
                    },
                },
            },
            {
                "name": "list_pending_pickings",
                "description": "List incoming/outgoing transfers that need to be processed",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "picking_type": {"type": "string", "enum": ["incoming", "outgoing", "internal"]},
                        "state": {"type": "string", "enum": ["confirmed", "assigned", "waiting"]},
                        "limit": {"type": "integer", "default": 20},
                    },
                },
            },
            {
                "name": "validate_picking",
                "description": "Validate (complete) a stock transfer/picking",
                "inputSchema": {
                    "type": "object",
                    "required": ["picking_id"],
                    "properties": {"picking_id": {"type": "integer"}},
                },
            },
            {
                "name": "create_internal_transfer",
                "description": "Move products between internal locations",
                "inputSchema": {
                    "type": "object",
                    "required": ["src_location_id", "dst_location_id", "lines"],
                    "properties": {
                        "src_location_id": {"type": "integer"},
                        "dst_location_id": {"type": "integer"},
                        "lines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_id": {"type": "integer"},
                                    "qty": {"type": "number"},
                                },
                            },
                        },
                    },
                },
            },
            {
                "name": "get_reorder_rules",
                "description": "Get current reorder/replenishment rules (min/max stock rules)",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    def _call_tool(self, tool_name, args):
        env = request.env
        if tool_name == "check_stock":
            domain = []
            if args.get('product_ids'):
                domain.append(('product_id', 'in', args['product_ids']))
            if args.get('location_id'):
                domain.append(('location_id', '=', args['location_id']))
            quants = env['stock.quant'].search_read(
                domain,
                ['product_id', 'location_id', 'quantity', 'reserved_quantity'],
            )
            return quants

        elif tool_name == "list_pending_pickings":
            type_map = {'incoming': 'incoming', 'outgoing': 'outgoing', 'internal': 'internal'}
            domain = [('state', 'not in', ['done', 'cancel'])]
            if args.get('picking_type'):
                domain.append(('picking_type_id.code', '=', type_map[args['picking_type']]))
            if args.get('state'):
                domain.append(('state', '=', args['state']))
            pickings = env['stock.picking'].search_read(
                domain,
                ['name', 'picking_type_id', 'partner_id', 'state', 'scheduled_date'],
                limit=args.get('limit', 20),
            )
            return pickings

        elif tool_name == "validate_picking":
            picking = env['stock.picking'].browse(args['picking_id'])
            picking.button_validate()
            return {'id': picking.id, 'state': picking.state}

        elif tool_name == "create_internal_transfer":
            moves = [(0, 0, {
                'name': '/',
                'product_id': l['product_id'],
                'product_uom_qty': l['qty'],
                'product_uom': env['product.product'].browse(l['product_id']).uom_id.id,
                'location_id': args['src_location_id'],
                'location_dest_id': args['dst_location_id'],
            }) for l in args['lines']]
            picking = env['stock.picking'].create({
                'picking_type_id': env.ref('stock.picking_type_internal').id,
                'location_id': args['src_location_id'],
                'location_dest_id': args['dst_location_id'],
                'move_ids_without_package': moves,
            })
            picking.action_confirm()
            return {'id': picking.id, 'name': picking.name, 'state': picking.state}

        elif tool_name == "get_reorder_rules":
            rules = env['stock.warehouse.orderpoint'].search_read(
                [],
                ['product_id', 'location_id', 'product_min_qty', 'product_max_qty', 'qty_on_hand'],
            )
            return rules

        return super()._call_tool(tool_name, args)
```

---

## 7. mcp-hr-agent

Handles employee records, leave requests, payslips, and HR operations.

```
addons/mcp_hr_agent/
├── __init__.py
├── __manifest__.py
└── controllers/
    ├── __init__.py
    └── hr_mcp.py
```

### `controllers/hr_mcp.py`

```python
from odoo import http
from odoo.http import request
from .mcp_base import MCPBaseController

class HRMCPController(MCPBaseController):
    _mcp_agent = 'hr'

    def _get_tools(self):
        return [
            {
                "name": "list_employees",
                "description": "Search and list employees",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "department": {"type": "string"},
                        "job_title": {"type": "string"},
                        "active": {"type": "boolean", "default": True},
                    },
                },
            },
            {
                "name": "get_leave_balance",
                "description": "Get remaining leave days for an employee",
                "inputSchema": {
                    "type": "object",
                    "required": ["employee_id"],
                    "properties": {"employee_id": {"type": "integer"}},
                },
            },
            {
                "name": "create_leave_request",
                "description": "Create a leave request for an employee",
                "inputSchema": {
                    "type": "object",
                    "required": ["employee_id", "holiday_status_id", "date_from", "date_to"],
                    "properties": {
                        "employee_id": {"type": "integer"},
                        "holiday_status_id": {"type": "integer", "description": "Leave type ID"},
                        "date_from": {"type": "string", "format": "date"},
                        "date_to": {"type": "string", "format": "date"},
                        "name": {"type": "string", "description": "Reason"},
                    },
                },
            },
            {
                "name": "list_pending_leaves",
                "description": "List leave requests pending manager approval",
                "inputSchema": {
                    "type": "object",
                    "properties": {"department_id": {"type": "integer"}},
                },
            },
        ]

    def _call_tool(self, tool_name, args):
        env = request.env
        if tool_name == "list_employees":
            domain = [('active', '=', args.get('active', True))]
            if args.get('department'):
                domain.append(('department_id.name', 'ilike', args['department']))
            if args.get('job_title'):
                domain.append(('job_title', 'ilike', args['job_title']))
            employees = env['hr.employee'].search_read(
                domain,
                ['name', 'job_title', 'department_id', 'work_email', 'mobile_phone'],
            )
            return employees

        elif tool_name == "get_leave_balance":
            allocations = env['hr.leave.allocation'].search_read(
                [('employee_id', '=', args['employee_id']), ('state', '=', 'validate')],
                ['holiday_status_id', 'number_of_days', 'number_of_days_display'],
            )
            return allocations

        elif tool_name == "create_leave_request":
            leave = env['hr.leave'].create({
                'employee_id': args['employee_id'],
                'holiday_status_id': args['holiday_status_id'],
                'date_from': args['date_from'],
                'date_to': args['date_to'],
                'name': args.get('name', ''),
            })
            return {'id': leave.id, 'state': leave.state, 'name': leave.display_name}

        elif tool_name == "list_pending_leaves":
            domain = [('state', '=', 'confirm')]
            if args.get('department_id'):
                domain.append(('department_id', '=', args['department_id']))
            leaves = env['hr.leave'].search_read(
                domain,
                ['employee_id', 'holiday_status_id', 'date_from', 'date_to', 'state'],
            )
            return leaves

        return super()._call_tool(tool_name, args)
```

---

## 8. Calling Odoo MCP from an AI Agent (Python client)

```python
import requests

ODOO_URL = "http://202.71.1.13:8069"
API_KEY = "your_api_key"  # load from .env

headers = {
    "Authorization": f"bearer {API_KEY}",
    "X-Odoo-Database": "odoo_db",
    "Content-Type": "application/json",
}

def mcp_tools_list(agent: str) -> list:
    res = requests.post(
        f"{ODOO_URL}/mcp/{agent}/tools/list",
        headers=headers,
        json={},
    )
    res.raise_for_status()
    return res.json().get("tools", [])

def mcp_call_tool(agent: str, tool_name: str, arguments: dict) -> dict:
    res = requests.post(
        f"{ODOO_URL}/mcp/{agent}/tools/call",
        headers=headers,
        json={"name": tool_name, "arguments": arguments},
    )
    res.raise_for_status()
    result = res.json()
    if result.get("isError"):
        raise Exception(result["content"][0]["text"])
    import json
    return json.loads(result["content"][0]["text"])

# Example: Buyer agent creates an RFQ
tools = mcp_tools_list("buyer")
rfq = mcp_call_tool("buyer", "create_rfq", {
    "vendor_id": 15,
    "lines": [
        {"product_id": 42, "qty": 100, "price_unit": 9.50},
        {"product_id": 43, "qty": 50, "price_unit": 12.00},
    ]
})
print(rfq)  # {'id': 87, 'name': 'P00087', 'state': 'draft'}

# Example: Warehouse agent checks stock
stock = mcp_call_tool("warehouse", "check_stock", {"product_ids": [42, 43]})
```

---

## 9. Setting Up Bot Users for Agent Access

```python
# Create a dedicated bot user for each agent via Odoo shell
# /u01/erp/Odoo/odoo-server/odoo-bin shell -c /u01/erp/Odoo/odoo.conf -d odoo_db

# Create bot user
bot = env['res.users'].create({
    'name': 'Buyer Agent Bot',
    'login': 'buyer_agent_bot',
    'email': 'buyer_agent@eraowl.internal',
    'groups_id': [(6, 0, [
        env.ref('purchase.group_purchase_user').id,
        env.ref('base.group_user').id,
    ])],
})
bot.password = False  # Disable password login for security
env.cr.commit()

# Then generate API key from UI: Settings → Users → Buyer Agent Bot → API Keys
```

**Security best practices for agent bot users:**
- Set `password = False` — disable password login
- Grant minimum required groups only
- Set API key duration to 90 days max, rotate regularly
- Use one bot user per agent type for audit trail clarity
- Store API keys in `.env` or a secrets manager — never in source code

---

## 10. Agent MCP Manifest Summary

| Agent Module | Route prefix | Odoo depends | Key tools |
|---|---|---|---|
| `mcp_buyer_agent` | `/mcp/buyer/` | `purchase` | search_rfqs, create_rfq, confirm_purchase_order, get_vendor_pricelists |
| `mcp_warehouse_agent` | `/mcp/warehouse/` | `stock` | check_stock, list_pending_pickings, validate_picking, create_internal_transfer, get_reorder_rules |
| `mcp_hr_agent` | `/mcp/hr/` | `hr_holidays`, `hr_payroll` | list_employees, get_leave_balance, create_leave_request, list_pending_leaves |
| `mcp_sales_agent` | `/mcp/sales/` | `sale` | search_orders, create_quotation, confirm_order, get_customer_history |
| `mcp_accounting_agent` | `/mcp/accounting/` | `account` | list_invoices, create_invoice, register_payment, get_account_balance |

---

## 11. Reference Links

- [Web Controllers reference](https://www.odoo.com/documentation/19.0/developer/reference/backend/http.html)
- [External JSON-2 API (Odoo 19)](https://www.odoo.com/documentation/19.0/developer/reference/external_api.html)
- [Server Framework 101 Tutorial](https://www.odoo.com/documentation/19.0/developer/tutorials/server_framework_101.html)
- [ORM API reference](https://www.odoo.com/documentation/19.0/developer/reference/backend/orm.html)
- [Security in Odoo](https://www.odoo.com/documentation/19.0/developer/reference/backend/security.html)
- [Model Context Protocol spec](https://modelcontextprotocol.io/specification)
