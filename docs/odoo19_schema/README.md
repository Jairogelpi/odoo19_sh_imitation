# Odoo 19 Database Inventory

## Current Full Catalog
- [all_models.csv](all_models.csv)
- [all_fields.csv](all_fields.csv)
- [all_relation_fields.csv](all_relation_fields.csv)
- [deduplicated_tables.csv](deduplicated_tables.csv)
- [deduplicated_tables.md](deduplicated_tables.md)
- [erd.md](erd.md)
- [erd_edges.csv](erd_edges.csv)

## Module Docs
- [00_Odoo_Brain.md](../00_Odoo_Brain.md)
- [base_module.md](base_module.md)
- [crm_module.md](crm_module.md)
- [base_vs_crm.md](base_vs_crm.md)

## Current Summary
- 281 physical tables
- 203 model tables
- 69 relation tables
- 2 hybrid tables
- 7 physical-only tables
- 83 base-category rows
- 19 crm-category rows
- 179 shared-category rows

## Hybrid Tables
- `discuss_channel_member` (`mail`)
- `mail_notification` (`mail`, `sms`, `snailmail`)

## Scope
- Database: `esenssi`
- Stack: Odoo 19.0 on PostgreSQL 16
- Installed modules: 44
- Public tables: 281
- Public indexes: 634
- Public constraints: 1207
- PostgreSQL constraints by type: `c:34, f:834, p:281, u:58`
- Odoo metadata totals: 270 models, 4163 fields, 954 constraints

## What This Report Uses
- `ir_model_data.module` is treated as the owning module for Odoo metadata objects.
- `ir_model_data` rows with `model = 'ir.model'` classify logical models.
- `ir_model_data` rows with `model = 'ir.model.fields'` classify fields.
- `ir_model_data` rows with `model = 'ir.model.constraint'` classify Odoo-level constraints.
- Rows in `ir_model_fields` with `relation_table` populated are the many-to-many bridge tables.
- `public_indexes.csv` and `public_constraints.csv` are the physical PostgreSQL layer.

## Base vs CRM
- Base-owned logical models: 124
- CRM-owned logical models: 22
- Base-owned fields: 1567
- CRM-owned fields: 330
- Base-owned Odoo constraints: 57
- CRM-owned Odoo constraints: 5
- Base-owned many-to-many relation fields: 28
- CRM-owned many-to-many relation fields: 9

### Base Dependencies
- (none)

### CRM Dependencies
- `base_setup`, `calendar`, `contacts`, `digest`, `mail`, `phone_validation`, `resource`, `sales_team`, `utm`, `web_tour`

## Support Modules That Shape CRM
CRM depends on these installed modules: `base_setup`, `calendar`, `contacts`, `digest`, `mail`, `phone_validation`, `resource`, `sales_team`, `utm`, `web_tour`.

The biggest supporting modules by field count are:
- `mail`: 1169 fields, 78 models
- `calendar`: 226 fields, 18 models
- `sms`: 158 fields, 18 models
- `resource`: 91 fields, 7 models
- `portal`: 76 fields, 12 models
- `sales_team`: 74 fields, 4 models
- `html_editor`: 73 fields, 24 models
- `web`: 71 fields, 15 models
- `crm_iap_mine`: 68 fields, 6 models
- `phone_validation`: 64 fields, 6 models

## Exports
- [all_models.csv](all_models.csv)
- [all_fields.csv](all_fields.csv)
- [all_relation_fields.csv](all_relation_fields.csv)
- [deduplicated_tables.csv](deduplicated_tables.csv)
- [deduplicated_tables.md](deduplicated_tables.md)
- [erd.md](erd.md)
- [erd_edges.csv](erd_edges.csv)
- [modules.csv](modules.csv)
- [module_dependencies.csv](module_dependencies.csv)
- [base_crm_models.csv](base_crm_models.csv)
- [base_crm_fields.csv](base_crm_fields.csv)
- [base_crm_constraints.csv](base_crm_constraints.csv)
- [base_crm_relation_fields.csv](base_crm_relation_fields.csv)
- [public_tables.csv](public_tables.csv)
- [public_indexes.csv](public_indexes.csv)
- [public_constraints.csv](public_constraints.csv)

## Reading The CSVs
- `base_crm_models.csv` shows the logical model, its owning module, and a guessed physical table name.
- `base_crm_fields.csv` contains the field-level schema metadata for the current `base` and `crm` install.
- `base_crm_relation_fields.csv` is the filtered many-to-many bridge table list.
- `public_tables.csv` is the full physical table list in `public`.
- `public_indexes.csv` is the full PostgreSQL index inventory in `public`.
- `public_constraints.csv` is the full PostgreSQL constraint inventory in `public`.

## Notes
- The ownership counts are per metadata row, not unique physical model class. Odoo extensions can make the same model appear under more than one module.
- The `table_name_guess` column in `base_crm_models.csv` follows Odoo's default `model.replace('.', '_')` convention.
- If a model uses a custom `_table`, the guess may differ from the actual physical table name.
