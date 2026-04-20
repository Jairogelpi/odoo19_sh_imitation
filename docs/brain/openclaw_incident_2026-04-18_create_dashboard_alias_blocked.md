# Incident 2026-04-18 — `create_dashboard` was blocked as invalid `action_type`

## Symptom

OpenClaw chat accepted a user request to create a dashboard such as:

- dashboard name: `jairo`
- chart type: bar chart
- target module/model: sales / `sale.order`

The assistant reply showed a suggested action, but Odoo stored it as blocked with:

```text
Invalid action_type: 'create_dashboard'
```

That meant the UI looked like the agent understood the request, yet approval could not proceed because the suggestion never matched the Odoo allowlist contract.

## Root cause

This was a contract drift between the control-plane gateway and the Odoo-side validator.

- Odoo only accepts allowlisted action types such as `odoo_read` and `odoo_write` in [addons_custom/openclaw/models/openclaw_chat.py](../../addons_custom/openclaw/models/openclaw_chat.py).
- The local dashboard router in [control-plane/app/mcp_gateway.py](../../control-plane/app/mcp_gateway.py) already emitted dashboard creation as:
  - `action_type = "odoo_write"`
  - `target_model = "dashboard.dashboard"`
  - `payload.operation = "create"`
- The OpenRouter/LLM envelope parser accepted `suggested_actions` as-is, so when the model produced `action_type = "create_dashboard"` that alias passed through untouched.
- Odoo then correctly blocked it because `create_dashboard` is not part of the valid action type contract.

## Fix applied

The normalization now happens in the gateway envelope parser before Odoo sees the action.

File:

- [control-plane/app/mcp_gateway.py](../../control-plane/app/mcp_gateway.py)

Behavior:

- normalize `action_type = "create_dashboard"` into `action_type = "odoo_write"`
- default `target_model` to `dashboard.dashboard`
- default `payload.model` to `dashboard.dashboard`
- default `payload.operation` to `create`
- only do this normalization when the action is actually for `dashboard.dashboard`; inconsistent payloads remain unnormalized and will still be blocked

The system prompt was also tightened so the LLM is explicitly told not to invent action-type aliases and to express dashboard creation through the standard `odoo_write` contract.

In Odoo, legacy blocked cards can now be repaired with:

- `openclaw.request.repair_legacy_dashboard_alias_blocks()`

The repair is intentionally narrow:

- only `chat_suggestion`
- only `draft`
- only requests blocked by `Invalid action_type: 'create_dashboard'`
- only cases where the request text can be reconstructed into a reviewable dashboard payload

The chat session payload path now attempts this repair before rendering cards, so old cards can self-heal when the conversation is opened after the code is deployed.

## Verification

Contract test file:

- [control-plane/app/tests/test_tool_chat_reply_contract.py](../../control-plane/app/tests/test_tool_chat_reply_contract.py)

Covered cases:

- parsing a raw LLM envelope containing `create_dashboard`
- end-to-end `tool_chat_reply()` response normalization for the OpenRouter branch

Observed result:

```text
.\.venv\Scripts\python.exe -m pytest control-plane/app/tests/test_tool_chat_reply_contract.py -q
16 passed in 0.38s
```

Odoo verification on the live `esenssi` database:

```text
docker exec odoo19_sh_imitation-odoo-1 odoo -c /etc/odoo/odoo.conf -d esenssi -u openclaw --test-enable --test-tags openclaw --stop-after-init --http-port=8071
0 failed, 0 error(s) of 28 tests
```

## Live repair performed

On 2026-04-18, the helper was executed against blocked requests `13` and `14` in `esenssi`.

Outcome:

- both requests were converted from blocked `custom` drafts into `odoo_write` drafts
- `target_model` was set to `dashboard.dashboard`
- `policy_id` was set to the first user-accessible Odoo write policy
- `decision_note` was cleared
- `payload_json` was rebuilt with a transparent default blueprint

Applied assumptions for these two repaired records:

- `sale.order` as the source model because the request explicitly referred to the sales module
- `bar_chart` because the user explicitly asked for a bar chart
- `state` as the grouping field for a count-by-sales-records chart, and this assumption was appended to `rationale` so the user can review it before approval

This was acceptable for the live repair because the user had already said, in the same session, effectively "lo que tú quieras de módulo de ventas". The repaired requests still remain in `draft`, so nothing was executed automatically.

## Why this fix is preferable

We did **not** relax Odoo to accept arbitrary new `action_type` values. The fix keeps Odoo strict and repairs the contract at the gateway boundary, which is where the alias drift was introduced.
