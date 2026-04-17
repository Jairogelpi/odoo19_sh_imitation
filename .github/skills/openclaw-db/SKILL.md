---
name: openclaw-db
description: "Use when a task reads, creates, duplicates, drops, or inspects PostgreSQL databases and should be routed through OpenClaw."
---

# OpenClaw DB

Use this skill for PostgreSQL work that should go through the OpenClaw permission and approval layer.

## Use for

- Listing databases.
- Creating a new database.
- Duplicating a database.
- Dropping a database.
- Any database action that should be reviewed before execution.

## Preferred route

1. Convert the task into an OpenClaw request.
2. Check the policy and allowlist.
3. Use the gateway tools for the requested DB action.
4. Keep destructive operations behind explicit approval.

## Preferred tools

- `db.list_databases`
- `db.create_database`
- `db.duplicate_database`
- `db.drop_database`
- `openclaw.execute_request` when the request is driven by an Odoo policy or approval flow

## Examples

- "List the databases available in the local stack."
- "Create a new Odoo database through OpenClaw."
- "Duplicate this database after approval."