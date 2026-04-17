# Workspace Instructions

When a task touches Odoo records, docs, workspace files, database changes, web search, or shell actions, prefer the OpenClaw workflow in this repository before taking direct low-level action.

Use the OpenClaw addon and control-plane as the primary operating path for permissioned actions:

- Odoo addon: `addons_custom/openclaw/`
- Control-plane gateway: `control-plane/app/mcp_gateway.py`
- Default gateway URL: `http://control-plane:8082`
- Gateway endpoint: `/mcp`

Treat `shell.execute`, workspace writes, and database writes as high-risk and keep them behind OpenClaw policy and approval when possible.