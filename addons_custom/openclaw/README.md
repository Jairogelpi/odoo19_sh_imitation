# OpenClaw

OpenClaw is the permission and approval layer for a future AI agent that operates through MCP-backed tools instead of direct low-level access.

## What this module gives you

- Odoo groups for read-only, operator, and admin access.
- Policy records that define what a role can do.
- Request records that can be submitted, approved, executed, rejected, or failed.
- Settings for the MCP gateway URL, docs root, and tool allowlist.
- A real MCP execution path through the control-plane gateway at `/mcp`.

## Intended operating model

1. A user creates a request in Odoo.
2. The request is mapped to a policy.
3. Odoo decides whether the request can auto-approve or needs manual approval.
4. Approved requests are sent to the MCP gateway.
5. External tools run in the gateway, while Odoo ORM actions are executed locally after the gateway returns a normalized local action.
6. Odoo keeps the approval trail, gateway response, and execution state.

## Default OpenRouter model

The control-plane uses `z-ai/glm-4.5-air:free` as the default OpenRouter model because it is free and explicitly tuned for agent-centric workflows, including reasoning and tool use.

Fallback model: `openrouter/elephant-alpha`.

If you want to override the default, set `OPENROUTER_MODEL` in the control-plane environment.

## Safety boundary

- This module does not expose docker.sock.
- This module does not execute raw SQL directly.
- This module does not write to the repository by itself.
- High-risk actions should remain behind approval and an external tool gateway.

## Payload patterns

The `payload_json` field stores the arguments for the chosen action type.

Examples:

```json
{
	"operation": "create",
	"model": "crm.lead",
	"values": {
		"name": "New opportunity",
		"stage_id": 3
	}
}
```

```json
{
	"path": "brain/openclaw.md",
	"content": "# OpenClaw\n\nNew note from MCP."
}
```

For custom tools, set `custom_tool_name` to a gateway tool such as `workspace.write_file` and pass its arguments in `payload_json`.
