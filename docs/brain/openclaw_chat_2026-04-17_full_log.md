# OpenClaw Chat Full Log (2026-04-17)

## Scope

This document captures the full implementation and stabilization pass for the OpenClaw chat-first experience in Odoo 19, including:

- architecture and behavior decisions
- backend, gateway, and frontend changes
- incidents found during live validation
- fixes applied in code and database
- run commands and verification results
- operational checklist and follow-up work

## Product intent

Target UX:

- user-facing OpenClaw is a simple chat
- conversations are persisted as sessions with history
- approvals and permissions remain in admin/policy layer
- suggested actions appear inline as cards with approve/reject/detail controls

## Implemented architecture

### Odoo addon (chat system of record)

Core models and chat RPCs live in:

- [addons_custom/openclaw/models/openclaw_chat.py](../../addons_custom/openclaw/models/openclaw_chat.py)
- [addons_custom/openclaw/models/openclaw_request.py](../../addons_custom/openclaw/models/openclaw_request.py)

Behavior:

- session list and active conversation retrieval
- message persistence for user/assistant turns
- LLM reply request through gateway client
- action suggestion materialization into `openclaw.request`
- approval/rejection/detail RPCs for cards in chat

### MCP control-plane (chat reply and tool routing)

Chat tool and dispatch path live in:

- [control-plane/app/mcp_gateway.py](../../control-plane/app/mcp_gateway.py)

Tool of interest:

- `chat.reply`

Contract:

- receives message history and policy context
- injects strict JSON response instruction (`reply` + `suggested_actions`)
- calls OpenRouter with fallback model support
- returns normalized envelope to Odoo

### Frontend (Owl action)

Client action and template:

- [addons_custom/openclaw/static/src/js/openclaw_chat.js](../../addons_custom/openclaw/static/src/js/openclaw_chat.js)
- [addons_custom/openclaw/static/src/xml/openclaw_chat.xml](../../addons_custom/openclaw/static/src/xml/openclaw_chat.xml)
- [addons_custom/openclaw/static/src/scss/openclaw_chat.scss](../../addons_custom/openclaw/static/src/scss/openclaw_chat.scss)

Features:

- sessions sidebar and active thread
- composer with Enter-to-send
- request cards under assistant messages
- per-card actions: approve, reject, detail
- right drawer for request payload/policy/gateway details

## Files changed in this pass

### Backend

- [addons_custom/openclaw/models/openclaw_chat.py](../../addons_custom/openclaw/models/openclaw_chat.py)
  - access check updated to modern API (`check_access('create')`)
  - compatibility guard added for environments missing `openclaw_request.message_id`
  - message payload request loading made robust when schema is stale

### Frontend

- [addons_custom/openclaw/static/src/js/openclaw_chat.js](../../addons_custom/openclaw/static/src/js/openclaw_chat.js)
  - state and handlers for request cards and detail drawer
- [addons_custom/openclaw/static/src/xml/openclaw_chat.xml](../../addons_custom/openclaw/static/src/xml/openclaw_chat.xml)
  - card rendering and action buttons
  - detail drawer structure
- [addons_custom/openclaw/static/src/scss/openclaw_chat.scss](../../addons_custom/openclaw/static/src/scss/openclaw_chat.scss)
  - full visual redesign for modern chat layout

### Manifest/assets

- [addons_custom/openclaw/__manifest__.py](../../addons_custom/openclaw/__manifest__.py)
  - ensures chat JS/XML/SCSS are in loaded web bundles
  - `web.assets_web` includes chat assets for runtime pages where needed

## Incidents observed and resolutions

### 1) Gateway tool mismatch: `Unknown tool: chat.reply`

Symptom:

- chat RPC returned gateway error with unknown tool

Root cause:

- runtime container/image mismatch with code that already defined `chat.reply`

Resolution:

- rebuild/recreate control-plane service
- revalidate tool listing and live chat call

Verification:

- chat request completed
- OpenRouter call logged 200

### 2) Chat crash: `UndefinedColumn openclaw_request.message_id`

Symptom:

- loading session triggered RPC_ERROR in `rpc_get_session`

Root cause:

- code/model expected `message_id` on `openclaw_request`
- physical DB schema lacked column in current environment

Resolution:

1. immediate database hotfix:

```sql
ALTER TABLE openclaw_request ADD COLUMN IF NOT EXISTS message_id integer;
CREATE INDEX IF NOT EXISTS openclaw_request_message_id_idx ON openclaw_request (message_id);
```

2. module update to sync metadata
3. code-level defensive fallback in chat payload path

Verification:

- OpenClaw chat action loads again
- `rpc_get_session` no longer crashes
- new messages can be sent/received

### 3) CSS not applied (unstyled chat)

Symptom:

- chat rendered with plain/legacy look despite SCSS file existing

Root cause:

- active bundle did not include OpenClaw chat stylesheet in served asset path during runtime checks

Resolution:

- manifest asset registration adjusted
- module update + runtime reload
- bundle content verified in debug assets

Verification:

- `.o_openclaw_chat` selectors present in served CSS
- computed styles confirm grid layout and themed bubble styles

## Visual/UX outcome

Current UI state:

- modern two-pane desktop layout
- stronger message hierarchy and readability
- better action-card affordances
- cleaner composer and send button
- responsive behavior for tablet/mobile widths

Still visible (non-blocking):

- push notification warning in incognito contexts (`permission denied`)

## Commands executed for stabilization

```powershell
# module updates

docker compose exec odoo odoo -c /etc/odoo/odoo.conf -d odoo19 -u openclaw --stop-after-init --log-level=warn

# service restart when required

docker compose restart odoo

# db schema hotfix for missing column

docker compose exec db psql -U odoo -d odoo19 -c "ALTER TABLE openclaw_request ADD COLUMN IF NOT EXISTS message_id integer;" -c "CREATE INDEX IF NOT EXISTS openclaw_request_message_id_idx ON openclaw_request (message_id);"
```

## Runtime validation summary

Validated successfully:

- OpenClaw chat action loads without RPC_ERROR
- session history retrieval works
- message send/receive works
- assistant response reaches UI
- styles are loaded and applied

Known warnings preserved:

- Odoo registry warning about `_sql_constraints` deprecation on policy model
- docutils warnings from other text parsing paths during module load

## Smoke test (2-minute checklist)

1. Open OpenClaw Chat action.
2. Confirm session list is visible and messages load.
3. Send: `Responde OK en una línea.`
4. Confirm assistant response appears.
5. Ask for a suggested action with a valid policy key.
6. Confirm action card appears.
7. Click `Detail` and verify JSON sections in drawer.
8. Click `Approve` or `Reject` and confirm card state updates.

## Suggested follow-ups

1. Add a formal migration script for `message_id` so manual SQL is never needed in future environments.
2. Add one integration test that asserts session payload retrieval when request links exist.
3. Isolate and resolve docutils warning source to clean module-update logs.
4. Optional UX pass: add subtle enter animations and sticky “scroll to latest” indicator.

## Related notes

- [OpenClaw](openclaw.md)
- [OpenClaw Request Cycle](openclaw_request_cycle.md)
- [OpenClaw Tool Catalog](openclaw_tools.md)
- [Control Plane](control_plane.md)
