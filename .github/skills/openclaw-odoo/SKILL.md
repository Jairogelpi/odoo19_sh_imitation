---
name: openclaw-odoo
description: "Use when a task touches Odoo records, models, menus, settings, requests, approvals, or any Odoo ORM action that should pass through OpenClaw."
---

# OpenClaw Odoo

Use this skill for Odoo-specific work that should be routed through the OpenClaw permission and approval layer.

## Use for

- Creating or updating Odoo records.
- Reading Odoo configuration and request state.
- Managing OpenClaw policies, requests, and settings.
- Any action that should become an `openclaw.execute_request` payload.

## Preferred route

1. Turn the task into an OpenClaw request.
2. Check policy and allowlist.
3. Use `openclaw.execute_request` for Odoo ORM work.
4. Keep dangerous writes behind approval.

## Examples

- "Create an OpenClaw request for this contact update."
- "Read the current policy allowlist for this user."
- "Approve and execute the pending Odoo request through OpenClaw."