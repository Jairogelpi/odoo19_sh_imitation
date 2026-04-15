# Odoo CRM Module

## Role
The `crm` module implements lead and opportunity management: pipeline stages, conversion wizards, recurring qualification flows, scoring, lost-reason tracking, and sales-team orchestration. It sits on top of the mail, calendar, resource, sales-team, contacts, and utm stacks.

## Scope
- Logical models: 22
- Fields: 330
- Odoo constraints: 5
- Many-to-many relation fields: 9
- Physical tables in the deduplicated catalog: 19

## Dependencies
Installed module dependencies recorded for `crm`:
- `base_setup`
- `calendar`
- `contacts`
- `digest`
- `mail`
- `phone_validation`
- `resource`
- `sales_team`
- `utm`
- `web_tour`

## Core model clusters
| Cluster | Representative models | Why they matter |
| --- | --- | --- |
| Pipeline and leads | `crm.lead`, `crm.stage`, `crm.tag`, `crm.lost.reason` | Main CRM workflow, classification, and lost-reason tracking. |
| Team and reporting | `crm.team`, `crm.activity.report` | Team ownership, reporting, and management views. |
| Conversion wizards | `crm.lead2opportunity.partner`, `crm.lead2opportunity.partner.mass`, `crm.merge.opportunity` | Lead-to-opportunity conversion and merge flows. |
| Scoring and qualification | `crm.lead.scoring.frequency`, `crm.lead.scoring.frequency.field`, `crm.recurring.plan` | Qualification cadence and recurrence logic. |
| Configuration | `res.config.settings` | CRM settings exposed through the generic Odoo configuration layer. |

## Highest-density models
| Model | Fields | Constraints | M2M fields | Notes |
| --- | --- | --- | --- | --- |
| `crm.lead` | 108 | 4 | 1 | The main opportunity/leads table and the largest CRM object. |
| `crm.team` | 28 | 0 | 0 | Sales team management and routing. |
| `crm.activity.report` | 22 | 0 | 0 | Analytical/reporting view. |
| `res.config.settings` | 21 | 0 | 0 | Settings entry point for CRM configuration. |
| `crm.lead2opportunity.partner.mass` | 20 | 0 | 3 | Batch conversion and merge wizard. |
| `crm.lead2opportunity.partner` | 17 | 0 | 1 | Single-lead conversion wizard. |
| `crm.stage` | 15 | 0 | 1 | Pipeline stage definitions. |
| `crm.lead.scoring.frequency` | 11 | 0 | 0 | Scoring cadence control. |
| `crm.recurring.plan` | 10 | 1 | 0 | Recurrence rules for scoring or follow-up flows. |
| `crm.lead.lost` | 9 | 0 | 1 | Lost-lead wizard. |
| `crm.lead.scoring.frequency.field` | 9 | 0 | 0 | Field-level scoring input. |
| `crm.lost.reason` | 9 | 0 | 0 | Reason catalog for lost opportunities. |

## Key many-to-many bridges
| Field | Relation table | Purpose |
| --- | --- | --- |
| `crm.lead.tag_ids` | `crm_tag_rel` | Lead tags. |
| `crm.stage.team_ids` | `crm_stage_crm_team_rel` | Stage-to-sales-team assignment. |
| `crm.lead.lost.lead_ids` | `crm_lead_crm_lead_lost_rel` | Leads selected in the lost wizard. |
| `crm.lead2opportunity.partner.duplicated_lead_ids` | `crm_lead_crm_lead2opportunity_partner_rel` | Leads grouped during conversion. |
| `crm.lead2opportunity.partner.mass.duplicated_lead_ids` | `crm_lead_crm_lead2opportunity_partner_mass_rel` | Batch conversion targets. |
| `crm.lead2opportunity.partner.mass.lead_tomerge_ids` | `crm_convert_lead_mass_lead_rel` | Leads selected for merge. |
| `crm.lead2opportunity.partner.mass.user_ids` | `crm_lead2opportunity_partner_mass_res_users_rel` | Salespeople involved in conversion. |
| `crm.merge.opportunity.opportunity_ids` | `merge_opportunity_rel` | Opportunities selected for merge. |
| `crm.lead.pls.update.pls_fields` | `crm_lead_pls_update_crm_lead_scoring_frequency_field_rel` | Fields used by PLS scoring updates. |

## Constraints and validation
`crm` has a small but important set of integrity rules:
- `crm_lead_check_probability` ensures probability stays between 0 and 100.
- `crm_lead_user_id_team_id_type_index` supports assignment and routing queries.
- `crm_lead_create_date_team_id_idx` supports team/date reporting.
- `crm_lead_default_order_idx` supports the default pipeline ordering.
- `crm_recurring_plan_check_number_of_months` prevents negative recurrence periods.

## Support stack around CRM
CRM is small in model count, but it sits on a large cross-module support stack. The heaviest supporting modules by field count are:
- `mail`: 1169 fields, 78 models
- `calendar`: 226 fields, 18 models
- `sms`: 158 fields, 18 models
- `resource`: 91 fields, 7 models
- `portal`: 76 fields, 12 models
- `sales_team`: 74 fields, 4 models
- `web`: 71 fields, 15 models
- `crm_iap_mine`: 68 fields, 6 models
- `phone_validation`: 64 fields, 6 models

## Notes
- `crm` depends heavily on shared tables in the mail and partner stack, which is why many tables are classified as shared in the deduplicated catalog.
- The CRM physical table view is smaller than the logical model count because a lot of its behavior is implemented by reusable base and support models.
- For the physical table view, see [deduplicated_tables.md](deduplicated_tables.md).
- For the full model and field export, see [all_models.csv](all_models.csv) and [all_fields.csv](all_fields.csv).
