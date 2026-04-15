# Base vs CRM

## Executive summary
- `base` is the platform layer: 124 logical models, 1567 fields, 57 Odoo constraints, and 28 many-to-many relation fields.
- `crm` is the business layer: 22 logical models, 330 fields, 5 Odoo constraints, and 9 many-to-many relation fields.
- The physical-table overlap between both modules is small but important: 4 tables are owned by both `base` and `crm`.
- Most CRM behavior sits on top of `base` identity, metadata, view, action, and configuration objects, plus the support stack in `mail`, `calendar`, `resource`, `sales_team`, and `utm`.

## Tables shared by both modules
| Table | Why it matters | Notes |
| --- | --- | --- |
| `res_users` | Authentication, assignment, audit, approvals, and company membership. | Largest shared table in the whole catalog. |
| `res_partner` | Contact and account backbone for leads, customers, and followers. | CRM uses this constantly for lead/contact linking. |
| `res_config_settings` | Generic settings surface used by CRM configuration. | Extends the standard settings framework. |
| `ir_config_parameter` | Global system parameters. | CRM and base both rely on it for feature flags and runtime settings. |

## CRM fields built on base models
| CRM model | Field | Relation | Why it matters |
| --- | --- | --- | --- |
| `crm.lead` | `user_id`, `activity_user_id`, `create_uid`, `write_uid` | `res.users` | Ownership, assignment, workflow, and audit trail. |
| `crm.lead` | `partner_id`, `commercial_partner_id`, `message_partner_ids` | `res.partner` | Main lead/contact linkage and chatter recipients. |
| `crm.lead` | `company_id`, `user_company_ids` | `res.company` | Multi-company filtering and scoping. |
| `crm.lead2opportunity.partner` | `user_id`, `partner_id`, `commercial_partner_id`, `lead_id` | `res.users` / `res.partner` / `crm.lead` | Conversion flow from lead to opportunity. |
| `crm.lead2opportunity.partner.mass` | `user_id`, `user_ids`, `partner_id`, `commercial_partner_id`, `lead_id` | `res.users` / `res.partner` / `crm.lead` | Batch conversion and merge flow. |
| `crm.activity.report` | `author_id`, `company_id`, `partner_id`, `user_id`, `lead_id` | `res.partner` / `res.company` / `res.users` / `crm.lead` | Reporting view that spans core base records. |
| `crm.team` | `alias_model_id`, `alias_parent_model_id` | `ir.model` | Mail alias routing and team ownership semantics. |

## Base objects CRM leans on most
| Base object | Typical role in CRM |
| --- | --- |
| `res.users` | Salesperson assignment, followers, audit, and company access. |
| `res.partner` | Lead/customer identity and communication backbone. |
| `res.company` | Multi-company scoping and operational isolation. |
| `ir.model` | Alias routing and dynamic model references. |
| `ir.ui.view` | CRM settings and form/tree/search UI composition. |
| `ir.actions.act_window` | Navigation into CRM actions and wizards. |
| `ir.actions.server` | Automation and server-side workflow. |
| `ir.config_parameter` | Runtime configuration. |
| `ir.rule` | Access rules that guard records. |
| `ir.cron` | Scheduled CRM automation and cleanups. |

## What is safe to touch first
- CRM-specific models such as `crm.lead`, `crm.team`, `crm.stage`, `crm.lost.reason`, and the conversion wizards.
- CRM scoring and qualification models such as `crm.lead.scoring.frequency` and `crm.recurring.plan`.
- CRM relation fields and stage/team routing if you are changing business flow.

## What to touch carefully
- `res.users`, `res.partner`, `res.company`, `ir.model`, `ir.ui.view`, `ir.actions.server`, `ir.actions.act_window`, `ir.config_parameter`, `ir.rule`, and `ir.cron`.
- These are cross-module core objects; a small change can affect login, permissions, menus, views, automation, or reporting across the whole system.

## Related docs
- [base_module.md](base_module.md)
- [crm_module.md](crm_module.md)
- [deduplicated_tables.md](deduplicated_tables.md)
