# Deduplicated Odoo 19 Table View

## What this view shows
- One row per real PostgreSQL table.
- Model tables and many-to-many bridge tables are deduplicated into the same catalog.
- `base`, `crm`, and `shared` are derived from the owning module set across all installed modules.

## Counts
- Total physical tables: 281
- Model tables: 203
- Relation tables: 69
- Hybrid tables: 2
- Physical-only tables: 7
- Base category rows: 83
- CRM category rows: 19
- Shared category rows: 179

## Hybrid tables
These rows combine model-table and relation-table behavior, so they are counted separately instead of being folded into the model/relation totals.

| Table | Owners | Objects | Degree | Notes |
| --- | --- | --- | --- | --- |
| `discuss_channel_member` | `mail` | `discuss.channel.member` | 9 | shared across modules |
| `mail_notification` | `mail, sms, snailmail` | `mail.notification` | 6 | shared across modules |

## High-value shared tables
| Table | Category | Kind | Owners | Degree |
| --- | --- | --- | --- | --- |
| `res_users` | shared | model_table | `base, crm, auth_passkey, auth_signup, auth_totp, auth_totp_mail, auth_totp_portal, base_import, base_setup, bus, calendar, contacts, digest, google_gmail, mail, mail_bot, microsoft_outlook, phone_validation, resource, sales_team, web, web_tour, web_unsplash` | 444 |
| `res_partner` | shared | model_table | `base, crm, auth_signup, bus, calendar, contacts, mail, partner_autocomplete, phone_validation, portal, privacy_lookup, snailmail, web` | 49 |
| `res_company` | shared | model_table | `base, mail, partner_autocomplete, resource, sms, snailmail, web` | 31 |
| `ir_model` | shared | model_table | `base, bus, mail, sms, web` | 29 |
| `mail_message` | shared | model_table | `mail, portal, sms, snailmail` | 28 |
| `crm_lead` | shared | model_table | `crm, crm_iap_enrich, crm_iap_mine, iap_crm` | 25 |
| `ir_act_server` | shared | model_table | `base, mail, sms` | 22 |
| `res_groups` | shared | model_table | `base, bus, mail` | 19 |
| `ir_model_fields` | shared | model_table | `base, mail` | 17 |
| `mail_activity_type` | shared | model_table | `calendar, mail` | 17 |

## Files
- [all_models.csv](all_models.csv)
- [all_fields.csv](all_fields.csv)
- [all_relation_fields.csv](all_relation_fields.csv)
- [deduplicated_tables.csv](deduplicated_tables.csv)
- [erd_edges.csv](erd_edges.csv)
- [erd_base.mmd](erd_base.mmd)
- [erd_crm.mmd](erd_crm.mmd)
- [erd_shared.mmd](erd_shared.mmd)

## Notes
- `shared` includes tables extended by more than one module, including the cross-cutting Odoo support stack around CRM.
- The ERD files are focused slices so they stay navigable; the CSV contains the full deduplicated catalog.
