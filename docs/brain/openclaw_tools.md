# OpenClaw Tool Catalog

## Goal

This note documents the control-plane tools exposed by [control-plane/app/mcp_gateway.py](../../control-plane/app/mcp_gateway.py).

## Core tools

### `openclaw.execute_request`

Validates and executes an OpenClaw request through the permission layer.

Use it when an Odoo request must be checked against policy and then translated into another tool call or a local ORM action.

### `db.list_databases`

Lists PostgreSQL databases managed by the local Odoo platform.

Use it for read-only inventory or to verify that a database exists before creating Odoo records against it.

### `db.create_database`

Creates a new PostgreSQL database owned by the Odoo user.

Use it only when the task explicitly requires a new database.

### `db.duplicate_database`

Duplicates an existing PostgreSQL database using `CREATE DATABASE ... WITH TEMPLATE`.

Use it for cloning one database into another exact target name.

### `db.drop_database`

Drops a PostgreSQL database after confirming the exact name.

Use it only when the name has been verified and the action is approved.

### `docs.read_markdown`

Reads a markdown file or docs folder from the Obsidian vault.

Use it for runbooks, architecture notes, or other vault content.

### `docs.write_markdown`

Writes or overwrites a markdown file in the Obsidian vault.

Use it for documentation creation and updates.

### `docs.search`

Searches the docs vault by plain-text match.

Use it to find relevant notes or prior decisions in the vault.

### `workspace.read_file`

Reads a file from the permitted workspace roots.

Use it when a task needs the contents of `docs/` or `addons_custom/`.

### `workspace.write_file`

Writes a file under `docs/` or `addons_custom/`.

Use it only when the action is allowed by policy and approval.

### `workspace.list_tree`

Lists a directory tree under `docs/` or `addons_custom/`.

Use it for structure discovery.

### `workspace.search`

Searches docs or `addons_custom` by plain-text match.

Use it for repository-wide discovery within the permitted roots.

### `web.search`

Performs a simple web search using DuckDuckGo HTML results.

Use it for quick external research when the task does not require a browser session.

### `github.list_workflows`

Lists GitHub Actions workflows for the configured repository.

Use it when you need repository CI metadata.

### `github.dispatch_workflow`

Triggers a GitHub Actions workflow dispatch on a branch.

Use it for controlled CI or delivery actions.

### `code.generate`

Drafts an agent plan or code changes using the configured OpenRouter model.

Use it for implementation planning before writing files.

### `chat.reply`

Generates a conversational reply for the OpenClaw chat UI using the configured OpenRouter model.

Use it when Odoo needs a normal chat-style assistant response with session history preserved in the addon.

### `shell.execute`

Executes a shell command only when explicitly enabled by environment policy.

Use it only for approved shell actions.

## Execution order

The gateway accepts JSON-RPC, exposes `tools/list`, and then handles `tools/call`.

Common flow:

1. Call `initialize`.
2. Call `tools/list`.
3. Call `tools/call` with the chosen tool name and arguments.

## Tool families

The control-plane groups tools into these families:

- OpenClaw request validation and routing
- PostgreSQL database actions
- documentation vault actions
- workspace file actions
- web search
- GitHub Actions operations
- code generation
- chat replies
- shell execution

## Policy guidance

- Read-only operations should prefer the narrowest tool.
- Destructive operations should require explicit approval.
- `openclaw.execute_request` is the preferred front door for Odoo-driven work.

## Related notes

- [OpenClaw](openclaw.md)
- [OpenClaw Request Cycle](openclaw_request_cycle.md)
- [OpenClaw Request Templates](openclaw_templates.md)
- [Control Plane](control_plane.md)