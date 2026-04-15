# Base

## Role
`base` is the platform foundation for identity, metadata, views, actions, scheduling, security, and the registry.

## Why it is a hub
Most modules depend on `base` directly or indirectly. A small change here can affect login, menus, automation, access rules, and view rendering.

## Best entry points
- [Base module detail](../odoo19_schema/base_module.md)
- [Base vs CRM comparison](../odoo19_schema/base_vs_crm.md)
- [Deduplicated tables](../odoo19_schema/deduplicated_tables.md)
- [Base ERD slice](../odoo19_schema/erd_base.mmd)

## What to inspect first
- `res.users`
- `res.partner`
- `res.company`
- `ir.model`
- `ir.ui.view`
- `ir.actions.server`
- `ir.actions.act_window`
- `ir.config_parameter`
- `ir.cron`
- `ir.rule`

## Relationships that matter most
- User groups and company access.
- Partner categories and chatter links.
- View and menu security.
- Server actions and cron jobs.
- Model metadata and external IDs.
