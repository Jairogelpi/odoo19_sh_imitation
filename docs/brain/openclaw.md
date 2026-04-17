# OpenClaw

## Purpose

OpenClaw is the permissioned execution layer for this platform. It sits between user intent and risky actions so Odoo, docs, workspace, database, code, and shell work can be routed through explicit policies and approvals.

## Where it lives

- Odoo addon: [addons_custom/openclaw/](../../addons_custom/openclaw/)
- Control-plane gateway: [control-plane/app/mcp_gateway.py](../../control-plane/app/mcp_gateway.py)
- Local gateway URL: `http://control-plane:8082`
- MCP endpoint: `/mcp`
- Vault root: the repository [docs/](../../docs/) directory mounted into Obsidian as `ObsidianVault`

## What is installed

- The local OpenClaw addon is installed in the `odoo19` database.
- The control-plane service is running in the admin stack.
- Odoo configuration parameters point to the local gateway.
- The OpenClaw workspace instructions and skills are present in `.github/`.
- The user-facing OpenClaw app is now chat-first and stores previous conversations as sessions in Odoo.

## Validated Odoo 19 lessons from this addon

- [addons_custom/openclaw/models/res_config_settings.py](../../addons_custom/openclaw/models/res_config_settings.py) extends `res.config.settings` with `config_parameter` fields.
- In Odoo 19, `openclaw_allowed_tools` cannot be `fields.Text` in that model. That breaks `default_get()` and crashes the Settings screen before it renders fully.
- The safe pattern for this setting is:
  - backend field type `fields.Char`
  - `config_parameter='openclaw.allowed_tools'`
  - view widget `widget="text"` in [addons_custom/openclaw/views/res_config_settings_views.xml](../../addons_custom/openclaw/views/res_config_settings_views.xml)
- This behavior is covered by [addons_custom/openclaw/tests/test_res_config_settings.py](../../addons_custom/openclaw/tests/test_res_config_settings.py).
- Deep note: [Odoo 19 `res.config.settings`](odoo19_res_config_settings.md).

## Current verification observations

- During module upgrade, OpenClaw still emits the Odoo 19 registry warning about `_sql_constraints` in [addons_custom/openclaw/models/openclaw_policy.py](../../addons_custom/openclaw/models/openclaw_policy.py).
- During the same upgrade, Odoo still emits docutils/reStructuredText warnings such as `Unexpected indentation.` while parsing text from the module load path.
- In this pass, those warnings were observed and preserved as follow-up work. They were not fixed or fully source-isolated here.

## Local environment

- The control-plane reads `OPENROUTER_API_KEY` from the local `.env` file.
- The `.env` file is ignored by Git, so the key stays out of the repository.
- If the key changes, recreate the control-plane container so the new value is loaded.

## Skill map

Use the following skill when the task type matches:

- Odoo records, models, menus, settings, approvals, or ORM actions: [openclaw-odoo](../../.github/skills/openclaw-odoo/SKILL.md)
- Markdown docs, runbooks, Obsidian notes, or vault search/write: [openclaw-docs](../../.github/skills/openclaw-docs/SKILL.md)
- Repository files, tree listing, file reads/writes, or workspace search: [openclaw-workspace](../../.github/skills/openclaw-workspace/SKILL.md)
- PostgreSQL database list/create/duplicate/drop: [openclaw-db](../../.github/skills/openclaw-db/SKILL.md)
- Code drafting, refactors, or implementation notes: [openclaw-code](../../.github/skills/openclaw-code/SKILL.md)

Use the umbrella skill [openclaw](../../.github/skills/openclaw/SKILL.md) when you want the assistant to choose the specialization.

## Decision map

1. If the task changes Odoo data or configuration, route it to `openclaw-odoo`.
2. If the task edits or searches documentation, route it to `openclaw-docs`.
3. If the task touches repository files outside docs, route it to `openclaw-workspace`.
4. If the task is about PostgreSQL, route it to `openclaw-db`.
5. If the task is planning code changes, route it to `openclaw-code`.
6. If the task is high-risk, keep it behind OpenClaw policy approval before execution.

## Operating contract

- Policies define what a role can do.
- Requests capture intent, approval state, gateway response, and execution result.
- Approved requests are executed through the MCP gateway.
- Local Odoo ORM actions happen only after the gateway returns a normalized local action.
- Dangerous operations remain explicit and reviewable.

## Documentation contract

This vault should stay current when any of the following change:

- compose files or stack topology
- OpenClaw addon models, views, or security rules
- control-plane tools or allowlists
- gateway URL or environment parameters
- skill definitions or workspace instructions
- any workflow that changes how permissioned actions are executed

## Related notes

- [Odoo Brain](../00_Odoo_Brain.md)
- [OpenClaw Request Cycle](openclaw_request_cycle.md)
- [OpenClaw Tool Catalog](openclaw_tools.md)
- [OpenClaw Request Templates](openclaw_templates.md)
- [Odoo 19 `res.config.settings`](odoo19_res_config_settings.md)
- [Control Plane](control_plane.md)
- [Platform](platform.md)
- [Delivery](delivery.md)
- [Services](services.md)
- [Stack Topology](stack_topology.md)
- [Environment State Model](environment_state_model.md)
