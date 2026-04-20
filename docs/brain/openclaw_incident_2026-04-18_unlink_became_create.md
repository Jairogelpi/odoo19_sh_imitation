# Incident 2026-04-18 — OpenClaw unlink action became a silent crm.lead create

## Symptom

User asked the OpenClaw chat to delete an opportunity ("bórrame la oportunidad prueba"). The chat approved the suggested action and it came back as **"Action failed"** in the UI. Odoo logs showed:

```
ERROR: null value in column "name" of relation "crm_lead" violates not-null constraint
```

The action that the user approved was supposed to be an `unlink`, yet the SQL that ran was an `INSERT INTO crm_lead`. A lead was never created (constraint stopped it), but any model without a hard NOT NULL on a visible field would have been silently inserted.

## Root cause

The executor in `addons_custom/openclaw/models/openclaw_request.py::_local_odoo_execute` dispatched operations from `local_action['operation']`. The LLM-generated payload stored under `openclaw_request.payload_json` used a different key:

```json
{
  "model": "crm.lead",
  "domain": [["name", "=", "prueba"]],
  "action": "unlink"
}
```

Because `local_action.get('operation')` returned `None`, the original fallback was:

```python
operation = local_action.get('operation') or ('search_read' if self.action_type == 'odoo_read' else 'create')
```

The request was `odoo_write`, so the fallback branch silently switched the operation to **`create`**. The executor then read `local_action.get('values') or {}`, got `{}`, and called `model.create({})`. On `crm.lead` the DB raised the NOT NULL violation; on other models it could have created empty records.

Two bugs compounded:

1. **Schema mismatch** between the gateway/LLM output (`"action"`) and the executor (`"operation"`).
2. **Unsafe fallback**: an unrecognized/missing operation keyword degraded into a `create` on whatever model was named, rather than erroring out.

## Fix

File: `addons_custom/openclaw/models/openclaw_request.py` (inside `_local_odoo_execute`).

```python
operation = local_action.get('operation') or local_action.get('action')
if not operation:
    raise ValidationError(_('Local Odoo actions require an "operation" field (got: %s).') % sorted(local_action.keys()))
```

This:
- Accepts both `operation` and `action` as the dispatch key (backwards-compatible with any already-written payloads that used `action`).
- Removes the silent fallback to `create` / `search_read`. A malformed payload now fails loud at approval time instead of mutating data.

## Prevention / hardening ideas (not yet applied)

- **Single source of truth for the payload schema**: pick one key name (`operation`) in the gateway/LLM prompt and the Odoo executor, and add a JSON schema validation step on both sides.
- **Whitelist of allowed operations**: validate `operation in {search_read, search, create, write, write_by_domain, unlink, unlink_by_domain}` before dispatching.
- **Required-field preflight per model + operation**: e.g. `create` on `crm.lead` must include `name` (or a resolvable `partner_name` / `partner_id` that will supply the display name) before calling `model.create`.
- **Executed preview**: the chat UI already shows a suggested action detail drawer — it could refuse approval if the preflight check fails.

## Related artifacts

- Failed DB row: `openclaw_request` id=3 (state=failed) in the `esenssi` database.
- Surviving crm.lead created by request id=2 (the previous successful `create` with `{"name":"prueba"}`).
- Log excerpt from the Odoo container on 2026-04-17 23:50:55 UTC.
