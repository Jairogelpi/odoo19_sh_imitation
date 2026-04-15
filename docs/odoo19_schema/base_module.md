# Odoo Base Module

## Role
The `base` module is the foundation layer of the Odoo stack. It owns the registry, metadata, security, views, actions, scheduling, configuration, users, partners, companies, and the core model/field catalog that every other installed module relies on.

## Scope
- Logical models: 124
- Fields: 1567
- Odoo constraints: 57
- Many-to-many relation fields: 28
- Physical tables in the deduplicated catalog: 83

## Core model clusters
| Cluster | Representative models | Why they matter |
| --- | --- | --- |
| Identity and access | `res.users`, `res.groups`, `res.partner`, `res.company` | Authentication, multi-company, partner records, and group-based access control. |
| Metadata and registry | `ir.model`, `ir.model.fields`, `ir.model.data`, `ir.model.constraint`, `ir.module.module` | Odoo's model/field registry and external-id layer. |
| UI and actions | `ir.ui.view`, `ir.ui.menu`, `ir.actions.act_window`, `ir.actions.server`, `ir.actions.report`, `ir.actions.client` | Views, menus, windows, server actions, reports, and client actions. |
| Scheduler and configuration | `ir.cron`, `ir.config_parameter`, `ir.sequence`, `ir.rule` | Scheduled jobs, system parameters, numbering, and access rules. |
| Attachment and content | `ir.attachment`, `ir.binary`, `ir.asset` | Binary storage, attachments, and asset delivery. |
| Wizards and setup flows | `base.language.export`, `base.language.install`, `base.module.update`, `base.partner.merge.automatic.wizard` | Operational helpers and administrative flows. |

## Highest-density models
| Model | Fields | Constraints | M2M fields | Notes |
| --- | --- | --- | --- | --- |
| `res.users` | 97 | 1 | 2 | Main user table, company membership, group membership. |
| `res.partner` | 73 | 1 | 1 | Shared contact model used across the whole system. |
| `ir.cron` | 59 | 1 | 0 | Scheduled jobs and automation. |
| `ir.actions.server` | 48 | 1 | 2 | Server actions and webhook-related configuration. |
| `ir.model.fields` | 48 | 3 | 1 | Field metadata, groups, and custom field rules. |
| `res.company` | 48 | 1 | 1 | Multi-company settings and accepted users. |
| `ir.module.module` | 37 | 1 | 1 | App/module registry and install state. |
| `ir.actions.act_window` | 31 | 1 | 1 | Standard window actions. |
| `ir.ui.view` | 27 | 3 | 1 | View inheritance and QWeb validation. |
| `res.groups` | 26 | 2 | 6 | Access groups, implied groups, menu/view access. |
| `ir.actions.report` | 26 | 1 | 1 | Report actions and group access. |
| `ir.attachment` | 25 | 1 | 0 | Binary attachments and document storage. |

## Key many-to-many bridges
| Field | Relation table | Purpose |
| --- | --- | --- |
| `res.users.company_ids` | `res_company_users_rel` | Companies the user can access. |
| `res.users.group_ids` | `res_groups_users_rel` | Security groups assigned to the user. |
| `res.groups.implied_ids` / `implied_by_ids` | `res_groups_implied_rel` | Group inheritance and implied permissions. |
| `res.partner.category_id` | `res_partner_res_partner_category_rel` | Partner tags. |
| `ir.ui.view.group_ids` | `ir_ui_view_group_rel` | Group-restricted views. |
| `ir.ui.menu.group_ids` | `ir_ui_menu_group_rel` | Group-restricted menus. |
| `ir.actions.server.group_ids` | `ir_act_server_group_rel` | Restricted server actions. |
| `ir.model.fields.groups` | `ir_model_fields_group_rel` | Field-level access control. |
| `ir.filters.user_ids` | `ir_filters_res_users_rel` | Saved filters shared with specific users. |
| `ir.module.module.country_ids` | `module_country` | Country availability for apps. |

## Constraints and validation
`base` carries most of the global integrity rules in the database. The main ones are:
- `ir_model_obj_name_uniq` on `ir.model` to keep model names unique.
- `ir_model_fields_name_unique` and `ir_model_fields_size_gt_zero` on `ir.model.fields`.
- `ir_model_data_module_name_uniq_index` and `ir_model_data_name_nospaces` on external IDs.
- `ir_ui_view_inheritance_mode` and `ir_ui_view_qweb_required_key` on views.
- `ir_rule_no_access_rights` on record rules.
- `ir_module_module_name_uniq` on installed modules.
- `ir_cron_check_strictly_positive_interval` on scheduled jobs.
- `ir_config_parameter_key_uniq` on system parameters.
- `ir_mail_server_certificate_requires_tls` on mail server security.

## Dependencies
- Direct module dependencies: none in this dataset.
- System impact: very high. Most installed modules depend on base models, metadata, views, or access rules.

## Notes
- The base layer is not just "core data". It is the schema contract that every extension module builds on.
- Changes to `base` can affect authentication, security, scheduling, exports, and view rendering across the whole database.
- For the physical table view, see [deduplicated_tables.md](deduplicated_tables.md).
- For the full model and field export, see [all_models.csv](all_models.csv) and [all_fields.csv](all_fields.csv).
