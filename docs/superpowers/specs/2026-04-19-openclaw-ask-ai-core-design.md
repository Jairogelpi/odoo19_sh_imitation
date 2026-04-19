# OpenClaw Ask AI Core - Declarative Runtime Design

**Date:** 2026-04-19
**Status:** Draft design, pending user review
**Scope:** `addons_custom/openclaw/` and `control-plane/app/` for the declarative Ask AI core, runtime bundle resolution, and compatibility migration away from hardcoded chat behavior

---

## 1. Goal

Define a real Ask AI core for OpenClaw that behaves more like Odoo 19 AI at the product-model level, not just at the UI level.

The target outcome is a system where:

- Odoo is the source of truth for `agents`, `topics`, `sources`, `default prompts`, and `LLM profiles`
- chat sessions resolve a deterministic, persisted `runtime bundle`
- the control-plane executes the runtime bundle instead of inventing product behavior from hardcoded routers
- the existing `openclaw.request` approval and execution cycle remains the safety backbone

This spec is intentionally focused on the core declarative runtime. It does not try to ship the full UX capillarity of Odoo 19 in the same delivery.

Official Odoo references that motivate this shape:

- Agents: https://www.odoo.com/documentation/19.0/applications/productivity/ai/agents.html
- Default prompts: https://www.odoo.com/documentation/19.0/applications/productivity/ai/default_prompts.html
- AI fields: https://www.odoo.com/documentation/19.0/applications/productivity/ai/fields.html

---

## 2. Non-goals

Explicitly out of scope for this design:

- Replacing the existing `openclaw.request` approval or executor state machine
- Shipping full Ctrl+K parity, button-global parity, and AI fields in the same first implementation
- Implementing true multi-provider runtime beyond the already-available OpenRouter backend
- Streaming chat replies
- Native provider tool-calling APIs
- A full redesign of the current chat UI shell
- Automatic re-resolution of agent/runtime in the middle of an active session

Those items can be layered on later. The first delivery must prove the declarative core first.

---

## 3. Current State and Why It Is Not Enough

The current code already contains useful building blocks, but product behavior is still too hardcoded.

Evidence in the repo:

- Session messages inject a fixed chat `system` prompt in `addons_custom/openclaw/models/openclaw_chat.py`
- `policy_context` currently carries a fixed skill taxonomy instead of a true agent model
- the control-plane injects structural behavior and domain guidance in `control-plane/app/mcp_gateway.py`
- domain routing still lives in hardcoded gateway functions instead of Odoo-administered records
- the current runtime backend is effectively OpenRouter-only in `control-plane/app/openrouter_client.py`
- the incident documented in `docs/brain/openclaw_incident_2026-04-18_unlink_became_create.md` proves that schema mismatch between LLM output and executor is already a real problem, not a hypothetical one

This means the system can propose and execute actions, but it does not yet have an Odoo-native declarative layer equivalent to:

- agents with durable prompts
- topics with instructions and tools
- sources as managed knowledge inputs
- default prompts resolved by model/context
- provider/model behavior selected by admin-configurable records

Without that layer, UI improvements alone would only make the current hardcoded behavior look better.

---

## 4. Architecture

### 4.1 High-level architecture

```text
User opens chat from global/model/record context
    ->
Odoo resolves default prompt, agent, topics, sources, and llm profile
    ->
Odoo compiles runtime_bundle_json and stores it on the session
    ->
Odoo sends messages + runtime bundle + policy context to control-plane
    ->
Control-plane executes the runtime bundle and returns:
    { reply, suggested_actions[] }
    ->
Odoo materializes openclaw.request records
    ->
Existing approval/execution flow runs unchanged
```

### 4.2 Responsibility boundaries

- `Odoo` owns product configuration and runtime resolution
- `OpenClaw chat` owns session persistence, message persistence, and UI state
- `Control-plane` owns provider calls, structured output parsing, and tool orchestration
- `Executor` owns final validation and execution of actions

### 4.3 Design principles

- Product behavior must be data-driven in Odoo, not hardcoded in the gateway
- Security must filter capabilities, not define assistant personality
- Session runtime must be persisted and reproducible
- The gateway must consume a resolved runtime, not derive business context from scratch
- The request cycle remains the single execution path for mutable Odoo actions

---

## 5. Data Model

The design introduces real models for the declarative AI layer. These are business records, not `res.config.settings` hacks.

### 5.1 `openclaw.ai.agent`

Primary unit of behavior, equivalent to the Odoo 19 agent concept.

Core fields:

- `name`
- `key`
- `active`
- `description`
- `system_prompt`
- `response_style`
- `restrict_to_sources`
- `llm_profile_id`
- `topic_ids`
- `source_ids`

Rules:

- Does not store user permissions
- Does not store secrets
- Can be assigned by multiple `default_prompt` records

### 5.2 `openclaw.ai.topic`

Operational capability grouping with instructions and allowed tools.

Core fields:

- `name`
- `key`
- `active`
- `instructions`
- `sequence`
- `mode`

Initial `mode` values:

- `info_only`
- `actionable`

Rules:

- Describes operational behavior only
- Does not define user ACLs
- May be shared across multiple agents

### 5.3 `openclaw.ai.tool`

Canonical catalog of tools or action capabilities that the runtime may expose.

Core fields:

- `name`
- `key`
- `active`
- `execution_kind`
- `gateway_name`
- `required_policy_action`
- `risk_level`
- `schema_key`
- `schema_version`

Example capabilities:

- `odoo.search_read`
- `odoo.create_request`
- `docs.search`
- `workspace.read_file`
- `web.search`

Rules:

- Tool keys are canonical and versionable
- Tool definitions must not remain scattered as magic strings across the gateway
- `required_policy_action` is the bridge between product capability and user authorization

### 5.4 `openclaw.ai.topic.tool`

Explicit through-model between topic and tool.

Core fields:

- `topic_id`
- `tool_id`
- `sequence`
- `required`
- `tool_instructions`
- `parameter_hints_json`

This is intentionally not a bare `many2many`. Per-topic tool guidance must be expressible without bloating prompts.

### 5.5 `openclaw.ai.source`

Managed knowledge source available to an agent.

Core fields:

- `name`
- `key`
- `active`
- `source_type`
- `uri`
- `status`
- `last_indexed_at`
- `index_ref`
- `metadata_json`

Initial `source_type` values:

- `url`
- `document`
- `knowledge`
- `vault_note`

Rules:

- Store pointers and indexing metadata, not large content blobs
- Source retrieval should stay externalizable

### 5.6 `openclaw.ai.default_prompt`

Rule that binds model context to agent selection and prompt specialization.

Core fields:

- `name`
- `active`
- `sequence`
- `applies_to_all_models`
- `model_ids`
- `agent_id`
- `instructions`
- `button_ids`
- `group_ids`
- `company_id`

Rules:

- Resolves conversation context
- Specializes an agent; does not replace it
- Must support both global and model-specific contexts
- `group_ids` and `company_id` are eligibility filters, not behavior-definition fields

### 5.7 `openclaw.ai.default_prompt.button`

Predefined UI buttons tied to a default prompt.

Core fields:

- `default_prompt_id`
- `label`
- `prompt_text`
- `sequence`
- `icon`

Rule:

- In v1 buttons inject prompt text into the conversation
- Buttons do not directly execute side effects

### 5.8 `openclaw.ai.llm_profile`

Admin-facing runtime profile for provider/model configuration.

Core fields:

- `name`
- `active`
- `backend`
- `model_name`
- `fallback_model_name`
- `temperature`
- `max_tokens`
- `reasoning_enabled`
- `supports_tools`
- `supports_structured_output`

Important constraint:

- The model can be generic, but the only real backend already present in this repo today is OpenRouter
- Do not claim multi-provider support in product UX until there is real runtime support behind it

### 5.9 Extensions to existing models

#### `openclaw.chat.session`

Add:

- `origin_kind` with values `global`, `model`, `record`
- `origin_model`
- `origin_res_id`
- `resolved_agent_id`
- `resolved_default_prompt_id`
- `resolved_llm_profile_id`
- `runtime_bundle_version`
- `runtime_bundle_json`

Reason:

- session-level reproducibility
- explicit record of what runtime was actually used

#### `openclaw.chat.message`

Optional additions:

- `origin_button_id`
- lightweight topic snapshot only if needed for audit

Reason:

- keep message records small
- avoid turning messages into mini-orchestrators

#### `openclaw.request`

Keep the existing model and flow.

Optional additions:

- `runtime_bundle_hash`
- `compiled_schema_version`

Reason:

- execution traceability
- correlation back to the runtime that produced the action

### 5.10 Relationship summary

```text
default_prompt -> 1 agent
agent -> N topics
agent -> N sources
agent -> 1 llm_profile
topic -> N topic.tool -> 1 tool
chat.session -> 1 resolved default_prompt
chat.session -> 1 resolved agent
chat.session -> 1 resolved llm_profile
chat.session -> N messages
chat.message -> N openclaw.request
```

### 5.11 What not to do

- Do not use `res.config.settings` as the main storage for agents/topics/prompts
- Do not encode topic semantics only in prompt text
- Do not attach security policy definitions to agent records
- Do not store secrets on agents or prompts

---

## 6. Runtime Resolution and Prompt Precedence

### 6.1 Resolution algorithm

The runtime must be resolved in Odoo before the message goes to the gateway.

Deterministic order:

1. Identify conversation origin: `global`, `model`, or `record`
2. Resolve the most specific applicable `default_prompt`
3. Take the `agent` from that `default_prompt`
4. Load the agent's `llm_profile`
5. Load active agent topics ordered by `sequence`
6. Load active agent sources
7. Intersect topic tools with:
   - user policy permissions
   - llm profile capabilities
8. Build a versioned `runtime_bundle_json`
9. Persist the bundle on the session
10. Reuse that bundle for the whole session unless the user explicitly starts a new session or requests a controlled refresh

Tie-breaking for multiple prompt matches:

- A prompt is eligible only if:
  - it is active
  - `company_id` is empty or matches the current company
  - `group_ids` is empty or intersects the current user's groups
  - it is global or matches the origin model
- most specific scope first
- then lowest `sequence`
- then lowest `id`

### 6.2 Session stability rule

Once a session is created with a resolved runtime:

- the agent does not auto-switch mid-session
- the prompt hierarchy does not auto-recompute mid-session
- admin edits affect new sessions, not already-running ones

Reason:

- reproducibility
- predictable UX
- debuggability

### 6.3 Prompt hierarchy

Prompt compilation order:

1. OpenClaw structural contract
2. Agent `system_prompt`
3. Default prompt instructions
4. Topic instructions
5. Record context projection
6. Source context summary
7. Session history
8. Latest user message

This hierarchy is mandatory. The default prompt specializes the agent; it does not replace it.

### 6.4 Bundle shape

Minimum required bundle keys:

- `bundle_version`
- `session_origin`
- `agent`
- `default_prompt`
- `llm_profile`
- `topics`
- `sources`
- `allowed_tools`
- `prompt_sections`
- `record_context`
- `ui_buttons`
- `policy_projection`
- `schema_versions`

`record_context` must be a controlled projection, not a raw ORM dump.

Allowed content:

- `model`
- `id`
- `display_name`
- whitelisted fields
- summarized relation hints

Disallowed content:

- arbitrary full record graphs
- view architecture blobs
- hidden fields by default

### 6.5 Precedence rules

- `default_prompt` cannot override the OpenClaw structural contract
- `topic` cannot grant tools denied by policy
- `required_policy_action` on each tool is the key used to intersect product capability with user authorization
- `llm_profile` can limit runtime capabilities but not invent new business capabilities
- the gateway cannot add topics or tools not present in the bundle
- the executor does not trust the bundle if action schema validation fails

---

## 7. Integration with the Existing Codebase

### 7.1 What stays

Keep as the stable base:

- current chat-first UI shell
- session and message persistence
- `openclaw.request` materialization
- approval/reject flow
- local executor path
- OpenRouter backend client

### 7.2 What becomes legacy compatibility

These pieces must become transitional compatibility, not the main product engine:

- fixed session-level system prompt injection
- fixed skill taxonomy in `policy_context`
- gateway prompt injection that encodes business behavior
- hardcoded domain routers in the control-plane

### 7.3 Integration phases

#### Phase A: Declarative data layer

- add new Odoo models and admin views
- add ACLs for admin/operator management
- load seed records for at least one pilot domain
- no production runtime changes yet

#### Phase B: Shadow runtime compilation

- implement runtime resolution in Odoo
- compute `runtime_bundle_json` and persist it on sessions
- do not switch the gateway to bundle-driven behavior yet
- expose runtime details in debug/admin view if needed

#### Phase C: Gateway bundle consumption

- extend chat RPC path to send bundle
- make the gateway consume bundle-first when present
- keep legacy routers only as fallback for old or unconfigured sessions

#### Phase D: Legacy reduction

- migrate one real domain fully
- remove or shrink matching hardcoded router logic
- repeat domain by domain

### 7.4 Required code shape changes

In Odoo:

- `openclaw.chat.session._generate_reply()` must send `runtime_bundle` in addition to `messages` and `policy_context`
- runtime resolution should live in dedicated modules, not grow `openclaw_chat.py` indefinitely

In control-plane:

- `tool_chat_reply()` must accept `runtime_bundle`
- gateway prompt injection should be reduced to structural enforcement
- business routing logic should become fallback-only
- bundle parsing and validation should live outside `mcp_gateway.py` when possible

### 7.5 Compatibility contract

- old sessions without bundle -> legacy router path
- new sessions with valid bundle -> declarative runtime path
- corrupt/incomplete bundle -> explicit visible failure or tightly controlled fallback

---

## 8. Schema and Validation Contract

This is mandatory because the repo already experienced a real schema mismatch incident.

### 8.1 Single source of truth

Canonical schemas must live in one shared repo location accessible to both Odoo and control-plane.

Proposed location:

- `shared/openclaw_schemas/`

At minimum:

- `runtime_bundle.v1.json`
- `suggested_action.v1.json`
- `local_odoo_action.v1.json`

### 8.2 Validation points

Validation must happen in all three layers:

- Odoo validates compiled runtime bundle before sending
- control-plane validates structured action output before returning
- executor validates final local action before mutating Odoo

### 8.3 Non-negotiable schema rules

- version every schema
- reject ambiguous actions
- reject missing operation/action semantics
- reject unsupported tool keys
- reject malformed record context payloads

### 8.4 Why this matters

The `unlink` -> `create` incident happened because output and executor were not bound to one shared schema contract. This spec treats that as a design requirement, not a cleanup task.

---

## 9. Risks and Non-negotiable Rules

### 9.1 Main risks

- building admin models while real behavior still lives in gateway hardcode
- mixing policy and assistant behavior
- pretending to support providers/models that do not exist at runtime
- bloating `mcp_gateway.py` even further
- letting session behavior mutate after creation
- shipping UI parity before core determinism

### 9.2 Non-negotiable rules

- Odoo resolves and persists runtime bundle
- gateway does not invent functional behavior when bundle is valid
- executor validates schema before execution
- every session is reproducible from stored bundle data
- no mutable Odoo action bypasses `openclaw.request`
- default prompt buttons inject prompt text, not direct side effects
- tool catalog is canonical and versioned
- legacy fallback remains explicit and removable

---

## 10. Recommended Implementation Order

1. Add new Odoo models and admin views
2. Add `llm_profile` and `default_prompt` resolution by model
3. Implement runtime bundle compilation in Odoo
4. Persist runtime bundle on sessions
5. Extend chat RPC to send bundle to the gateway
6. Add bundle parser/validator on the control-plane
7. Add shared schema files and three-layer validation
8. Migrate one pilot domain end-to-end
9. Remove or reduce corresponding legacy router logic
10. Only then start UX capillarity work such as global launcher expansion and AI fields

Recommended pilot domain:

- `CRM contacts` or `dashboard`

Do not start with a broad multi-domain rollout.

---

## 11. Testing Strategy

### 11.1 Odoo tests

- default prompt resolution by model and specificity
- agent/topic/source/profile bundle compilation
- session persistence of runtime bundle
- policy intersection on allowed tools
- button injection behavior

### 11.2 Control-plane tests

- bundle parsing
- bundle-first behavior over legacy routing
- action validation against shared schemas
- fallback behavior for missing or invalid bundles

### 11.3 End-to-end tests

- Odoo session -> compiled bundle -> gateway reply -> request materialization
- approval path still works unchanged
- invalid action payload is blocked before execution
- old sessions still use legacy path

### 11.4 Regression focus

Protect against:

- silent action coercion
- session runtime drift
- topic/tool expansion beyond policy
- bundle corruption leading to hidden behavior changes

---

## 12. Acceptance Criteria

The design is considered successfully implemented when all of the following are true:

- admins can configure agents, topics, sources, default prompts, and llm profiles from Odoo
- opening chat from different models resolves different default prompts without hardcoded gateway routing
- each session stores the effective runtime bundle used for that conversation
- the control-plane consumes the runtime bundle when present
- mutable Odoo actions still go through `openclaw.request`
- schema validation blocks ambiguous or malformed actions
- at least one pilot domain runs end-to-end without relying on the old hardcoded router path

---

## 13. Planning Notes

This spec is deliberately scoped to the Ask AI core. It is ready for implementation planning as a single project because it focuses on one bounded objective:

- moving OpenClaw from hardcoded conversational behavior to a declarative, Odoo-administered runtime core

Broader UX parity with Odoo 19 should be planned as a follow-on project after this core is working and stable.
