# OpenClaw Ask AI Core

Last updated: 2026-04-19

## Purpose

This note documents the new declarative Ask AI core introduced for OpenClaw so the platform no longer depends only on hardcoded chat routing.

The goal is not feature parity with Odoo 19 AI in one pass. The goal of this pass is to move runtime ownership into Odoo, make the control-plane consume a validated runtime bundle, and prove the pattern on one real pilot domain.

## Ownership split

### Odoo owns product runtime

Odoo is now the source of truth for:

- which agent should answer
- which prompt applies to the current context
- which topics and tools are exposed
- which knowledge sources are attached
- which LLM profile is selected

Core files:

- `addons_custom/openclaw/models/openclaw_ai_agent.py`
- `addons_custom/openclaw/models/openclaw_ai_topic.py`
- `addons_custom/openclaw/models/openclaw_ai_source.py`
- `addons_custom/openclaw/models/openclaw_ai_default_prompt.py`
- `addons_custom/openclaw/models/openclaw_ai_llm_profile.py`
- `addons_custom/openclaw/models/openclaw_ai_runtime.py`

Runtime snapshots are persisted on `openclaw.chat.session`:

- `resolved_agent_id`
- `resolved_default_prompt_id`
- `resolved_llm_profile_id`
- `runtime_bundle_version`
- `runtime_bundle_json`

### Control-plane owns execution of the resolved runtime

The control-plane no longer has to guess the active product runtime when a valid bundle is present.

New control-plane pieces:

- `control-plane/app/schema_validation.py`
- `control-plane/app/chat_runtime.py`
- `shared/openclaw_schemas/runtime_bundle.v1.json`

Behavior in this pass:

- `chat.reply` rejects invalid `runtime_bundle` payloads before calling the provider
- `chat.reply` takes the bundle path before the legacy router path
- the selected model can now come from `runtime_bundle.llm_profile.model_name`
- legacy router behavior remains available when no bundle is present

## Declarative catalog now present in Odoo

Admin screens were added for:

- AI Agents
- AI Topics
- AI Tools
- AI Sources
- AI Default Prompts
- AI LLM Profiles

These live under the OpenClaw root menu through `addons_custom/openclaw/views/openclaw_ai_views.xml`.

## First migrated pilot: CRM Contacts

The first seeded pilot is `CRM Contacts` for `res.partner`.

Seed files:

- `addons_custom/openclaw/data/openclaw_ai_tool_data.xml`
- `addons_custom/openclaw/data/openclaw_ai_pilot_crm_contacts.xml`

What the pilot currently seeds:

- tool: `odoo.search_read`
- tool: `odoo.create_request`
- topic: `crm_contacts`
- source: `crm_contacts_knowledge`
- llm profile: `CRM Contacts Profile`
- agent: `crm_contacts_agent`
- default prompt bound to `base.model_res_partner`
- two prompt buttons for lookup and approval-safe contact creation

Expected runtime result on `res.partner`:

- model-specific prompt resolves before global prompts
- `crm_contacts_agent` is selected
- read and approval-safe write tools are projected from the topic and active policy set

## Request-cycle contract

This Ask AI core does not remove the OpenClaw approval model.

Still true after this pass:

- assistant replies can suggest actions
- suggested actions still materialize into `openclaw.request`
- risky mutations are still reviewed through approval cards
- the control-plane still does not get direct permission to mutate Odoo arbitrarily

In other words: the assistant got a better runtime contract, not a bypass around governance.

## Verification completed in this pass

Odoo:

- `openclaw_ai_registry`
- `openclaw_ai_admin`
- `openclaw_ai_runtime`
- `openclaw_ai_gateway_bundle`
- `openclaw_ai_pilot_crm_contacts`

Control-plane:

- `control-plane/app/tests/test_chat_runtime_bundle.py`
- `control-plane/app/tests/test_tool_chat_reply_contract.py`

## Known gaps

- `suggested_action.v1.json` and `local_odoo_action.v1.json` were created, but they are not yet enforced end-to-end the way `runtime_bundle.v1.json` already is.
- The control-plane still contains legacy contact/dashboard/domain routers for fallback paths.
- Odoo runtime bundles currently drive model selection cleanly, but not every advanced profile knob is fully propagated or admin-polished yet.
- UX parity with Odoo 19 features like Ctrl+K, AI fields, and model-specific prompt administration at every touchpoint is still incomplete.

## Why this matters

Before this change, OpenClaw chat behavior lived mostly in a fixed system prompt plus router heuristics.

After this change:

- Odoo can resolve assistant behavior declaratively
- the control-plane can execute that runtime without redefining product logic
- the first migrated domain is already test-backed
- future domains can move from hardcoded router behavior into the same catalog pattern
