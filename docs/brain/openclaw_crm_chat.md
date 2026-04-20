# OpenClaw CRM Chat

## Goal

OpenClaw Chat can now drive CRM opportunity work in a proactive way:

- create opportunities
- delete opportunities
- ask for missing information before proposing the action
- keep approval and execution behind policy

## Supported user intents

### Create opportunity

The bot should ask only for the fields it needs to proceed:

- opportunity name
- client name

Example:

- `crea una oportunidad`
- `crea una oportunidad "Demo Proactiva" para cliente "Acme Test"`

If either name or client is missing, the bot must ask for the missing field instead of guessing.

### Delete opportunity

The bot can also propose deletion when the user asks to:

- delete an opportunity
- delete a CRM opportunity
- borrar una oportunidad
- eliminar una oportunidad

Deletion should be presented as an approved action card, not executed silently.

## Policy used for CRM chat

A dedicated policy was added for chat-driven CRM operations:

- key: `crm_chat`
- groups: internal users (`base.group_user`)
- allowed action: `odoo.write`
- approval: required

This keeps chat usable for normal users while still forcing the approval trail.

## How the flow works

1. User asks to create or delete an opportunity.
2. Gateway detects the CRM intent.
3. If fields are missing, it asks for them.
4. If fields are present, it returns a suggested action.
5. Odoo materializes the suggestion into an `openclaw.request` record.
6. The user approves or rejects the request in the chat UI.
7. Approved actions are executed through Odoo ORM.

## Opportunity fields used

For create actions, OpenClaw currently uses these CRM fields:

- `name` for the opportunity title
- `type = opportunity`
- `partner_name` for the client label

For delete actions, the current flow uses a domain-based delete request keyed by:

- opportunity name
- client name

## Files involved

- [control-plane/app/mcp_gateway.py](../../control-plane/app/mcp_gateway.py)
- [addons_custom/openclaw/models/openclaw_request.py](../../addons_custom/openclaw/models/openclaw_request.py)
- [addons_custom/openclaw/data/openclaw_policy_data.xml](../../addons_custom/openclaw/data/openclaw_policy_data.xml)
- [addons_custom/openclaw/models/openclaw_chat.py](../../addons_custom/openclaw/models/openclaw_chat.py)
- [addons_custom/openclaw/static/src/js/openclaw_chat.js](../../addons_custom/openclaw/static/src/js/openclaw_chat.js)
- [addons_custom/openclaw/static/src/xml/openclaw_chat.xml](../../addons_custom/openclaw/static/src/xml/openclaw_chat.xml)
- [addons_custom/openclaw/static/src/scss/openclaw_chat.scss](../../addons_custom/openclaw/static/src/scss/openclaw_chat.scss)

## Operational notes

- The control-plane container must be synchronized with the workspace source after gateway edits.
- Module upgrade is required after policy data changes.
- Push notification warnings in incognito are unrelated and can be ignored.
