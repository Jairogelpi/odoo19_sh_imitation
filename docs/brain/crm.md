# CRM

## Role
`crm` manages leads, opportunities, stages, scoring, lost reasons, and conversion wizards.

## Why it is a business layer
CRM is small compared with `base`, but it sits on top of the mail, calendar, resource, sales team, and partner stack. Most of its value comes from how it connects those systems together.

## Best entry points
- [CRM module detail](../odoo19_schema/crm_module.md)
- [Base vs CRM comparison](../odoo19_schema/base_vs_crm.md)
- [Deduplicated tables](../odoo19_schema/deduplicated_tables.md)
- [CRM ERD slice](../odoo19_schema/erd_crm.mmd)

## What to inspect first
- `crm.lead`
- `crm.team`
- `crm.stage`
- `crm.lost.reason`
- `crm.activity.report`
- `crm.lead2opportunity.partner`
- `crm.lead2opportunity.partner.mass`
- `crm.merge.opportunity`
- `crm.recurring.plan`

## Relationships that matter most
- Lead ownership through `res.users`.
- Customer and contact links through `res.partner`.
- Multi-company scoping through `res.company`.
- Team routing through `crm.team` and stage/team bridges.
- Reporting and activity tracking through `mail.activity` and `mail.activity.type`.
