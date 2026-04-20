# OpenClaw

## Purpose

OpenClaw is the permissioned execution layer for this platform. It sits between user intent and risky actions so Odoo, docs, workspace, database, code, and shell work can be routed through explicit policies and approvals.

## Where it lives

- Odoo addon: [addons_custom/openclaw/](../../addons_custom/openclaw/)
- Control-plane gateway: [control-plane/app/mcp_gateway.py](../../control-plane/app/mcp_gateway.py)
- Local gateway URL: `http://control-plane:8082`
- MCP endpoint: `/mcp`
- Vault root: the repository [docs/](../../docs/) directory mounted into Obsidian as `ObsidianVault`

## What is installed

- The local OpenClaw addon is installed in the `odoo19` database.
- The control-plane service is running in the admin stack.
- Odoo configuration parameters point to the local gateway.
- The OpenClaw workspace instructions and skills are present in `.github/`.
- The user-facing OpenClaw app is now chat-first and stores previous conversations as sessions in Odoo.

## Ask AI core status

OpenClaw now has a first declarative Ask AI core instead of relying only on hardcoded chat behavior.

- Odoo owns runtime resolution through `openclaw.ai.agent`, `openclaw.ai.topic`, `openclaw.ai.tool`, `openclaw.ai.source`, `openclaw.ai.default_prompt`, and `openclaw.ai.llm_profile`.
- Chat sessions persist the resolved runtime snapshot in `openclaw.chat.session.runtime_bundle_json` plus the resolved agent/prompt/profile ids.
- The control-plane now accepts `runtime_bundle` on `chat.reply`, validates it against a shared schema, and takes the bundle path before the legacy router path.
- `res.partner` is the first seeded pilot domain through the `CRM Contacts` prompt/agent/topic catalog.
- Mutable work still remains behind `openclaw.request`; the new core changes assistant selection and context ownership, not the approval guardrail.

What is still partial:

- Shared schema files now exist for `runtime_bundle`, `suggested_action`, and `local_odoo_action`, but runtime-bundle validation is the only part enforced end-to-end in this pass.
- LLM profile model selection is now driven by the runtime bundle in the control-plane, but richer profile tuning is not yet fully surfaced across all layers.
- Legacy routers still exist as fallback for unmigrated or bundle-less paths; this is intentional during the migration window.

## Training loop integration

OpenClaw can also export its chat sessions as training episodes for Agent Lightning.

- Export RPCs live in [addons_custom/openclaw/models/openclaw_chat.py](../../addons_custom/openclaw/models/openclaw_chat.py)
- The export bridge lives in [addons_custom/openclaw/training/bridge.py](../../addons_custom/openclaw/training/bridge.py)
- The optional Agent Lightning runtime wrapper lives in [addons_custom/openclaw/training/agent_lightning.py](../../addons_custom/openclaw/training/agent_lightning.py)

The intended flow is:

1. Collect chat sessions, assistant replies, and request outcomes in Odoo.
2. Export them as training episodes with `rpc_export_training_session` or `rpc_export_training_dataset`.
3. Feed those episodes into an external Agent Lightning `Trainer`.
4. Use the resulting policy, traces, or prompt updates as the next iteration of the OpenClaw router/chat loop.

## Validated Odoo 19 lessons from this addon

- [addons_custom/openclaw/models/res_config_settings.py](../../addons_custom/openclaw/models/res_config_settings.py) extends `res.config.settings` with `config_parameter` fields.
- In Odoo 19, `openclaw_allowed_tools` cannot be `fields.Text` in that model. That breaks `default_get()` and crashes the Settings screen before it renders fully.
- The safe pattern for this setting is:
  - backend field type `fields.Char`
  - `config_parameter='openclaw.allowed_tools'`
  - view widget `widget="text"` in [addons_custom/openclaw/views/res_config_settings_views.xml](../../addons_custom/openclaw/views/res_config_settings_views.xml)
- This behavior is covered by [addons_custom/openclaw/tests/test_res_config_settings.py](../../addons_custom/openclaw/tests/test_res_config_settings.py).
- Deep note: [Odoo 19 `res.config.settings`](odoo19_res_config_settings.md).

## Current verification observations

- During module upgrade, OpenClaw still emits the Odoo 19 registry warning about `_sql_constraints` in [addons_custom/openclaw/models/openclaw_policy.py](../../addons_custom/openclaw/models/openclaw_policy.py).
- During the same upgrade, Odoo still emits docutils/reStructuredText warnings such as `Unexpected indentation.` while parsing text from the module load path.
- In this pass, those warnings were observed and preserved as follow-up work. They were not fixed or fully source-isolated here.

## External MCP connectors (Obsidian + Memory)

OpenClaw control-plane now supports bridging to external MCP servers for Obsidian and persistent memory.

Environment variables on the `control-plane` service:

- `OPENCLAW_OBSIDIAN_MCP_URL`
- `OPENCLAW_OBSIDIAN_MCP_TOKEN`
- `OPENCLAW_OBSIDIAN_MCP_TIMEOUT_SECONDS`
- `OPENCLAW_MEMORY_MCP_URL`
- `OPENCLAW_MEMORY_MCP_TOKEN`
- `OPENCLAW_MEMORY_MCP_TIMEOUT_SECONDS`

Gateway tools added:

- `obsidian.mcp_tools_list`
- `obsidian.mcp_call`
- `memory.mcp_tools_list`
- `memory.mcp_call`

These bridge tools are controlled by policy allowlists (operator/admin include them by default).

## Context7 for Odoo 19

OpenClaw control-plane now supports a dedicated Context7 MCP bridge for live framework/package documentation queries.

Environment variables on the `control-plane` service:

- `OPENCLAW_CONTEXT7_MCP_URL`
- `OPENCLAW_CONTEXT7_MCP_TOKEN`
- `OPENCLAW_CONTEXT7_MCP_TIMEOUT_SECONDS`
- `OPENCLAW_CONTEXT7_RESOLVE_TOOL_NAME` (default: `resolve-library-id`)
- `OPENCLAW_CONTEXT7_QUERY_TOOL_NAME` (default: `query-docs`)

Gateway tools added:

- `context7.resolve_library_id`
- `context7.query_docs`
- `context7.mcp_tools_list`
- `context7.mcp_call`

## Third-party Odoo skills from ClawHub

Third-party Odoo skills can still be useful as references, but in this repository they are not the preferred operational path.

- `openclaw-odoo` remains the preferred route for production Odoo actions because it turns work into requests, checks policy/allowlists, and executes through `openclaw.execute_request`.
- Direct XML-RPC CRUD skills do not match this repo contract when they bypass the request, approval, and gateway flow.
- The imported `.github/skills/odoo-erp-connector/` tree is kept as a reviewed third-party reference/import artifact, not as the recommended production path for this repository.
- Read-only reporting ideas may still be curated locally later if they are adapted to the same approval model.
- Current repo-specific vetting notes live in [openclaw_third_party_odoo_skills.md](openclaw_third_party_odoo_skills.md).

Imported external process skills now present in this repo:

- `self-improvement` from ClawHub slug `self-improving-agent`
- `skill-vetter` from ClawHub slug `skill-vetter`
- `ontology` from ClawHub slug `ontology`, but curated here as an optional repo-local knowledge skill rather than an authoritative platform memory layer
- `postgresql-advisor` from ClawHub slug `pg`, curated here as an advisory-only PostgreSQL review skill that does not replace `openclaw-db`
- `grafana-advisor` from ClawHub slug `grafana`, curated here as an advisory-only observability review skill that does not auto-connect to Grafana or auto-provision changes

Important guardrail:

- `self-improvement` is vendored in this repository under `.github/skills/self-improvement/` and was curated to use repo-local `.learnings/` and repo-local support paths
- `self-improvement` ships optional hooks, but they remain opt-in in this repo and are not auto-enabled; the vendored hook source is `.github/skills/self-improvement/hooks/openclaw`
- `skill-vetter` is the review step to use before importing more third-party skills into OpenClaw
- `ontology` is vendored in this repository under `.github/skills/ontology/`, including a line-by-line-audited local helper script; it is still not a source of truth for Odoo records and does not auto-sync with Odoo, Obsidian, or OpenClaw memory
- `postgresql-advisor` and `grafana-advisor` are vendored in this repository as instruction-only advisory skills; they are meant to improve reviewed operator judgment, not to create a second execution path around local OpenClaw routes

## Local environment

- The control-plane reads `OPENROUTER_API_KEY` from the local `.env` file.
- The `.env` file is ignored by Git, so the key stays out of the repository.
- If the key changes, recreate the control-plane container so the new value is loaded.

## Skill map

Use the following skill when the task type matches:

- Odoo records, models, menus, settings, approvals, or ORM actions: [openclaw-odoo](../../.github/skills/openclaw-odoo/SKILL.md)
- Markdown docs, runbooks, Obsidian notes, or vault search/write: [openclaw-docs](../../.github/skills/openclaw-docs/SKILL.md)
- Repository files, tree listing, file reads/writes, or workspace search: [openclaw-workspace](../../.github/skills/openclaw-workspace/SKILL.md)
- PostgreSQL database list/create/duplicate/drop: [openclaw-db](../../.github/skills/openclaw-db/SKILL.md)
- Code drafting, refactors, or implementation notes: [openclaw-code](../../.github/skills/openclaw-code/SKILL.md)
- Vet a third-party skill before importing it: [skill-vetter](../../.github/skills/skill-vetter/SKILL.md)
- Capture recurring learnings, corrections, or non-obvious failures: [self-improvement](../../.github/skills/self-improvement/SKILL.md)
- Model optional local knowledge graphs without treating them as authoritative system state: [ontology](../../.github/skills/ontology/SKILL.md)
- PostgreSQL query/index/plan/tuning advice without bypassing local DB workflows: [postgresql-advisor](../../.github/skills/postgresql-advisor/SKILL.md)
- Grafana dashboard/alert/provisioning advice without creating a second automation path: [grafana-advisor](../../.github/skills/grafana-advisor/SKILL.md)

Use the umbrella skill [openclaw](../../.github/skills/openclaw/SKILL.md) when you want the assistant to choose the specialization.

## Decision map

1. If the task changes Odoo data or configuration, route it to `openclaw-odoo`.
2. If the task edits or searches documentation, route it to `openclaw-docs`.
3. If the task touches repository files outside docs, route it to `openclaw-workspace`.
4. If the task is about PostgreSQL, route it to `openclaw-db`.
5. If the task is planning code changes, route it to `openclaw-code`.
6. If the task is high-risk, keep it behind OpenClaw policy approval before execution.

## Operating contract

- Policies define what a role can do.
- Requests capture intent, approval state, gateway response, and execution result.
- Approved requests are executed through the MCP gateway.
- Local Odoo ORM actions happen only after the gateway returns a normalized local action.
- Dangerous operations remain explicit and reviewable.

## Documentation contract

This vault should stay current when any of the following change:

- compose files or stack topology
- OpenClaw addon models, views, or security rules
- control-plane tools or allowlists
- gateway URL or environment parameters
- skill definitions or workspace instructions
- any workflow that changes how permissioned actions are executed

## Related notes

- [Odoo Brain](../00_Odoo_Brain.md)
- [OpenClaw Ask AI Core](openclaw_ask_ai_core.md)
- [OpenClaw Chat Full Log (2026-04-17)](openclaw_chat_2026-04-17_full_log.md)
- [OpenClaw Incident: `create_dashboard` alias blocked (2026-04-18)](openclaw_incident_2026-04-18_create_dashboard_alias_blocked.md)
- [OpenClaw CRM Chat](openclaw_crm_chat.md)
- [OpenClaw Dashboard Chat Defaults](openclaw_dashboard_chat_defaults.md)
- [OpenClaw Request Cycle](openclaw_request_cycle.md)
- [OpenClaw Tool Catalog](openclaw_tools.md)
- [OpenClaw Request Templates](openclaw_templates.md)
- [OpenClaw Ontology Skill](openclaw_ontology.md)
- [OpenClaw Advisory Skills](openclaw_advisory_skills.md)
- [Agent Lightning Integration](../runbooks/agent-lightning-integration.md)
- [Odoo 19 `res.config.settings`](odoo19_res_config_settings.md)
- [Control Plane](control_plane.md)
- [Platform](platform.md)
- [Delivery](delivery.md)
- [Services](services.md)
- [Stack Topology](stack_topology.md)
- [Environment State Model](environment_state_model.md)
- [HF Training Status (2026-04-18)](hf_training_status_2026-04-18.md)
