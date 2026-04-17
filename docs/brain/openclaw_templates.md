# OpenClaw Request Templates

## Goal

This note gives copyable request shapes for common OpenClaw work. Use these as the basis for Odoo requests or gateway payloads.

## General request shape

```json
{
  "name": "Short title",
  "instruction": "What you want done",
  "action_type": "odoo_read",
  "policy_id": 1,
  "payload_json": "{}"
}
```

## Odoo template

Use this for Odoo ORM actions that should be routed through the permission layer.

```json
{
  "name": "Update CRM contact",
  "instruction": "Update this contact with the latest company details.",
  "action_type": "odoo_write",
  "policy_id": 2,
  "target_model": "res.partner",
  "target_ref": "Example Contact",
  "payload_json": "{\n  \"operation\": \"write\",\n  \"ids\": [42],\n  \"values\": {\n    \"phone\": \"+1 555 0100\"\n  }\n}"
}
```

## Docs template

Use this for vault notes, runbooks, or markdown updates.

```json
{
  "name": "Update runbook note",
  "instruction": "Document the latest backup restore flow.",
  "action_type": "docs_write",
  "policy_id": 3,
  "payload_json": "{\n  \"path\": \"brain/backup_restore.md\",\n  \"content\": \"# Backup Restore\\n\\nUpdated notes.\"\n}"
}
```

## Workspace template

Use this for file reads or writes under the allowed workspace roots.

```json
{
  "name": "Update workspace file",
  "instruction": "Write the new skill note to the workspace.",
  "action_type": "custom",
  "policy_id": 4,
  "custom_tool_name": "workspace.write_file",
  "payload_json": "{\n  \"root\": \"docs\",\n  \"path\": \"brain/example.md\",\n  \"content\": \"# Example\\n\\nContent.\"\n}"
}
```

## Database template

Use this for database inventory or database administration.

```json
{
  "name": "Create database",
  "instruction": "Create a new PostgreSQL database for testing.",
  "action_type": "db_write",
  "policy_id": 5,
  "payload_json": "{\n  \"operation\": \"create\",\n  \"name\": \"odoo_test\"\n}"
}
```

## Code-generation template

Use this when you want a plan before writing code.

```json
{
  "name": "Draft code change",
  "instruction": "Draft the changes needed to add a new Odoo view.",
  "action_type": "code_generation",
  "policy_id": 6,
  "payload_json": "{\n  \"context\": \"Current module structure\",\n  \"target\": \"addons_custom/example_module\"\n}"
}
```

## Shell template

Use this only when shell execution is explicitly allowed.

```json
{
  "name": "Run maintenance command",
  "instruction": "Run the approved maintenance command.",
  "action_type": "shell_action",
  "policy_id": 7,
  "payload_json": "{\n  \"command\": \"docker compose ps\",\n  \"cwd\": \"/workspace\"\n}"
}
```

## Policy notes

- Keep `require_human_approval` enabled for dangerous work.
- Keep `payload_json` small and explicit.
- Use `custom_tool_name` only for supported gateway tools.
- Do not store secrets in request JSON.

## About the API key you supplied

If you meant the OpenRouter key for the control-plane, store it in environment configuration as `OPENROUTER_API_KEY`. Do not put it into a vault note or request template.

## Related notes

- [OpenClaw](openclaw.md)
- [OpenClaw Request Cycle](openclaw_request_cycle.md)
- [OpenClaw Tool Catalog](openclaw_tools.md)