---
name: openclaw
description: "Use when a task should be routed through the OpenClaw addon, the MCP control-plane, or a permissioned OpenClaw workflow for Odoo, docs, workspace, DB, web, or code actions."
---

# OpenClaw

Use this skill as the umbrella for OpenClaw-driven work in this repository. Pick the specialized skill that matches the task: `openclaw-odoo`, `openclaw-docs`, `openclaw-workspace`, `openclaw-db`, or `openclaw-code`.

## Scope

OpenClaw in this repo is the local Odoo addon plus the control-plane MCP gateway.

- Odoo addon: `addons_custom/openclaw/`
- Control-plane: `control-plane/app/mcp_gateway.py`
- Gateway URL: `http://control-plane:8082`
- MCP endpoint: `/mcp`

## Use this workflow for

- Odoo read or write actions.
- Database list, create, duplicate, or drop actions.
- Docs reads and writes.
- Workspace reads and writes.
- Web search.
- Code drafting or generation.
- Any shell action that should be explicitly approved.

## Specializations

- Odoo actions: use `openclaw-odoo`.
- Docs actions: use `openclaw-docs`.
- Workspace actions: use `openclaw-workspace`.
- Database actions: use `openclaw-db`.
- Code drafting: use `openclaw-code`.

## Preferred tool routing

- Read docs: `docs.read_markdown`
- Write docs: `docs.write_markdown`
- Read workspace files: `workspace.read_file`
- Write workspace files: `workspace.write_file`
- List workspace trees: `workspace.list_tree`
- Search workspace: `workspace.search`
- Database reads: `db.list_databases`
- Database writes: `db.create_database`, `db.duplicate_database`, `db.drop_database`
- Odoo actions: `openclaw.execute_request`
- Web research: `web.search`
- Code drafting: `code.generate`

## Operating rule

1. Translate the user request into an OpenClaw request.
2. Check the policy and allowlist before executing dangerous work.
3. Prefer the gateway tools over direct edits when a task can be expressed that way.
4. Keep `shell.execute` and workspace writes behind explicit approval.
5. If an Odoo ORM action is needed, use `openclaw.execute_request` so the gateway can normalize the local action.

## Practical guardrails

- Do not bypass OpenClaw for tasks that can be represented as a gateway tool call.
- Use the request record and policy trail when the action should be reviewed by a human.
- Keep outputs concise and state which OpenClaw tool or request type was used.