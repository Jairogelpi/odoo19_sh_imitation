# Odoo 19 Compatibility Notes

## Purpose
This note records the Odoo 19-specific behaviors that broke custom addon work in this workspace.
Read it before changing XML, security groups, settings views, or ORM constraints.

Observed on Odoo 19.0-20260409 in this workspace.

## Fast rules
- Prefer Odoo 19 conventions over older forum snippets.
- If a parse error mentions `tree`, `states`, `attrs`, or `settings`, assume the snippet is using pre-19 syntax.
- When a module install fails on the first parse error, fix that first issue and reinstall before chasing secondary errors.

## Breaking changes observed

### Access groups
- `res.groups` no longer accepts `category_id`.
- Categories now live on `res.groups.privilege`, and groups reference them with `privilege_id`.
- Use `sequence` on both the privilege and group records to control display order.
- Failure signature: `Invalid field 'category_id' in 'res.groups'`.

Example:

```xml
<record id="privilege_openclaw" model="res.groups.privilege">
  <field name="name">OpenClaw</field>
  <field name="sequence">35</field>
  <field name="category_id" ref="openclaw.module_category_openclaw"/>
</record>

<record id="group_openclaw_user" model="res.groups">
  <field name="name">OpenClaw User</field>
  <field name="sequence">10</field>
  <field name="privilege_id" ref="openclaw.privilege_openclaw"/>
</record>
```

### List views
- `<tree>` is no longer valid in view XML.
- Use `<list>` for list-style tables.
- `ir.actions.act_window.view_mode` must use `list,form`.
- Failure signature: `Invalid view type: 'tree'. You might have used an invalid starting tag in the architecture.`

### Settings views
- `res.config.settings` no longer inherits through `//div[hasclass('settings')]`.
- The root container to target is `//app[@name='general_settings']`.
- The page structure is built with `app`, `block`, and `setting` elements.
- Failure signature: `Element '<xpath expr="//div[hasclass('settings')]">' cannot be located in parent view`.

### `res.config.settings` fields with `config_parameter`
- In Odoo 19, `res.config.settings` classifies these fields during `default_get()`.
- A `config_parameter` field declared as `fields.Text` fails in that path.
- Validated accepted types in this workspace: `boolean`, `integer`, `float`, `char`, `selection`, `many2one`, and `datetime`.
- If the value must be edited as multiline text, keep the backend field as `fields.Char` and use `widget="text"` in the view.
- Failure signature: `Field res.config.settings.<field_name> must have type 'boolean', 'integer', 'float', 'char', 'selection', 'many2one' or 'datetime'`.
- Deep note: [Odoo 19 `res.config.settings`](odoo19_res_config_settings.md).

### View modifiers
- `states` and `attrs` are not used in Odoo 19 view XML.
- Replace them with inline boolean expressions.

Example:

```xml
<button name="action_submit" type="object" string="Submit" invisible="state != 'draft'"/>
```

- Failure signature: `Since 17.0, the "attrs" and "states" attributes are no longer used.`

### Model constraints
- `_sql_constraints` is deprecated in the model class.
- Use `models.Constraint(...)` instead.
- Failure signature: a registry warning that `_sql_constraints` is no longer supported.

## CRM note
- `crm.lead` still uses `type` with the values `lead` and `opportunity`.
- Default type is `opportunity`.
- For a customer opportunity, set `partner_id`, `type='opportunity'`, and a valid `team_id`.
- This workspace validated `team_id = 1` for the default Sales team.

## Odoo + control plane integration
- OpenClaw requests that write data should use `action_type = 'odoo_write'`.
- The control-plane gateway normalizes action names before allowlist checks, so `odoo_write` maps to `odoo.write`.
- The MCP gateway lives behind `POST /mcp`.
- When source changes under `control-plane/app/`, rebuild the container. `docker restart` is not enough.

## Safe edit checklist
- Search for `<tree>` and `view_mode="tree,form"`.
- Search for `states=` and `attrs=`.
- Search for `//div[hasclass('settings')]`.
- Search for `config_parameter=` fields declared as `fields.Text` under `res.config.settings`.
- Search for settings fields that should stay multiline in the UI and render them with `widget="text"` when the backend type must stay `char`.
- Search for `category_id` on `res.groups`.
- Search for `_sql_constraints`.
- Reinstall the addon and fix the first parse error before moving on.

## Related notes
- [Base](base.md)
- [CRM](crm.md)
- [Schema Atlas](schema.md)
- [Control Plane](control_plane.md)
- [Odoo 19 `res.config.settings`](odoo19_res_config_settings.md)
- [Odoo 19 inventory README](../odoo19_schema/README.md)
- [Odoo schema overview](../odoo19_schema/erd.md)
