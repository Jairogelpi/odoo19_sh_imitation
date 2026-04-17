# Odoo 19 `res.config.settings`

## Purpose

This note records the `res.config.settings` behavior validated in this workspace on Odoo `19.0-20260409`.

It was confirmed on April 17, 2026 while fixing the OpenClaw settings screen in the `odoo19` database.

## Verified failure mode

- A field on `res.config.settings` backed by `config_parameter=...` is classified during `default_get()`.
- In this code path, `fields.Text` is rejected.
- The failure happens before the Settings form finishes loading, so a correct XML inheritance does not save the screen.

Failure signature validated in this workspace:

```text
Exception: Field res.config.settings.openclaw_allowed_tools must have type 'boolean', 'integer', 'float', 'char', 'selection', 'many2one' or 'datetime'
```

The traceback reached:

- `odoo/addons/base/models/res_config.py`
- `_get_classified_fields()`
- `default_get()`

## Verified safe pattern

When a settings field uses `config_parameter=...` in Odoo 19:

- use one of the accepted scalar types: `boolean`, `integer`, `float`, `char`, `selection`, `many2one`, or `datetime`
- do not use `fields.Text` for that pattern
- if the value is conceptually multiline, keep the field as `fields.Char` and render it with `widget="text"` in the XML view

This gives two useful properties at the same time:

- the backend remains compatible with `res.config.settings`
- the UI still behaves like a multiline editor

## OpenClaw example

Validated implementation:

- model: [addons_custom/openclaw/models/res_config_settings.py](../../addons_custom/openclaw/models/res_config_settings.py)
- view: [addons_custom/openclaw/views/res_config_settings_views.xml](../../addons_custom/openclaw/views/res_config_settings_views.xml)
- regression test: [addons_custom/openclaw/tests/test_res_config_settings.py](../../addons_custom/openclaw/tests/test_res_config_settings.py)

The OpenClaw setting `openclaw_allowed_tools` now follows this pattern:

- backend type: `fields.Char`
- storage: `config_parameter='openclaw.allowed_tools'`
- UI widget: `widget="text"`
- value shape: newline-delimited tool names

## What was verified

1. A regression test calling `self.env["res.config.settings"].default_get(["openclaw_allowed_tools"])` failed with the same exception shown in the live UI.
2. Changing the field from `fields.Text` to `fields.Char` removed the crash.
3. Adding `widget="text"` in the view preserved multiline editing.
4. The OpenClaw test command passed after the fix:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml exec -T odoo odoo -c /etc/odoo/odoo.conf -d odoo19 -u openclaw --test-enable --test-tags /openclaw --stop-after-init --http-port=8071
```

5. The active `odoo` container was restarted and `http://localhost:8069/web/login` returned HTTP `200`.

## Operational note

For this workspace, validating a fix in a one-off Odoo process is not enough by itself.

After changing addon Python or XML used by the running server:

- upgrade the module in a verification process
- then reload or restart the active Odoo process if you want the live UI on `:8069` to pick up the change immediately

## Related notes

- [Odoo 19 Compatibility Notes](odoo19_differences.md)
- [OpenClaw](openclaw.md)
- [Base](base.md)
