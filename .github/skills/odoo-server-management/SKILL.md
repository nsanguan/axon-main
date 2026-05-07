---
name: odoo-server-management
description: 'Start, stop, configure, and manage the Odoo server process. Use for: starting Odoo server, stopping Odoo, restarting service, changing config, using odoo-bin CLI, running cron jobs manually, running the Odoo shell, managing databases, scaffolding modules, checking Odoo version, server logs.'
argument-hint: 'Describe the server task (e.g. "start Odoo on port 8069" or "run shell for database mydb")'
---

# Odoo Server Management

## Installation Layout

| Path | Description |
|------|-------------|
| `/u01/erp/Odoo/odoo-server` | Odoo source (git repo) |
| `/u01/erp/Odoo/odoo-server/odoo-bin` | Main entry point |
| `/u01/erp/Odoo/odoo.conf` | Server configuration file |
| `/u01/erp/Odoo/venv` | Python virtual environment |
| `/u01/erp/Odoo/odoo-server/addons` | Standard addons path |

## Configuration (`/u01/erp/Odoo/odoo.conf`)

```ini
[options]
admin_passwd = EraOwl2026
db_host = localhost
db_port = 5435
db_user = odoo_admin
db_password = EraOwl2026
addons_path = /u01/erp/Odoo/odoo-server/addons
http_port = 8069
http_interface = 0.0.0.0
netrpc_interface = 0.0.0.0
```

## Starting the Server

```bash
# Standard start (foreground)
cd /u01/erp/Odoo/odoo-server
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf

# With specific database
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf -d mydb

# With extra addons path
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf --addons-path="/u01/erp/Odoo/odoo-server/addons,/path/to/custom/addons"

# Background (daemon)
nohup /u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf > /var/log/odoo/odoo.log 2>&1 &
```

## Stopping the Server

```bash
# Find PID
ps aux | grep odoo-bin

# Kill process
kill <PID>

# If running as a systemd service
sudo systemctl stop odoo
sudo systemctl start odoo
sudo systemctl restart odoo
sudo systemctl status odoo
```

## odoo-bin CLI Commands

```bash
# Check version
/u01/erp/Odoo/venv/bin/python odoo-bin --version

# List available databases
/u01/erp/Odoo/venv/bin/python odoo-bin db --db_host=localhost --db_port=5435 --db_user=odoo_admin

# Install a module
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf -d <database> -i <module_name> --stop-after-init

# Upgrade a module
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf -d <database> -u <module_name> --stop-after-init

# Upgrade all modules
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf -d <database> -u all --stop-after-init

# Scaffold new module
/u01/erp/Odoo/venv/bin/python odoo-bin scaffold my_module /u01/erp/Odoo/odoo-server/addons
```

## Odoo Shell

```bash
/u01/erp/Odoo/venv/bin/python odoo-bin shell -c /u01/erp/Odoo/odoo.conf -d <database>
```

Inside the shell:
```python
# env is a pre-initialized Environment
partners = env['res.partner'].search([('customer_rank', '>', 0)])
print(partners.mapped('name'))

# Commit changes
env.cr.commit()
```

## Running Tests

```bash
# Run tests for a module
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf -d <testdb> --test-enable -i my_module --stop-after-init

# Run specific test class
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf -d <testdb> --test-tags my_module.TestClass --stop-after-init

# Run with log level for test output
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf -d <testdb> --test-enable --log-level=test -i my_module --stop-after-init
```

## Logging

```bash
# Set log level via CLI
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf --log-level=debug

# Log specific loggers only
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf --log-handler=odoo.addons.my_module:DEBUG

# Log to file
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf --logfile=/var/log/odoo/odoo.log
```

Config file log options:
```ini
[options]
log_level = info           # debug, info, warning, error, critical
log_handler = :INFO
logfile = /var/log/odoo/odoo.log
```

## Database Management

```bash
# Connect directly to PostgreSQL
psql -h localhost -p 5435 -U odoo_admin <database>

# Create a new database from CLI
/u01/erp/Odoo/venv/bin/python odoo-bin -c /u01/erp/Odoo/odoo.conf -d newdb --init=base --stop-after-init

# Drop (via psql)
psql -h localhost -p 5435 -U odoo_admin -c "DROP DATABASE mydb;"
```

## Worker Configuration (Production)

Add to `odoo.conf` for multi-process:
```ini
workers = 4               # Number of HTTP worker processes (set to 2x CPU cores)
max_cron_threads = 1      # Dedicated cron worker
limit_memory_hard = 2684354560   # 2.5GB hard limit
limit_memory_soft = 2147483648   # 2GB soft limit
limit_request = 8192
limit_time_cpu = 60
limit_time_real = 120
```

## Odoo Version Info
- **Version**: 19.4.0 alpha (series 19.4)
- **Requires**: Python 3.12–3.14, PostgreSQL 16+
- **Python path**: `/u01/erp/Odoo/venv/bin/python`
