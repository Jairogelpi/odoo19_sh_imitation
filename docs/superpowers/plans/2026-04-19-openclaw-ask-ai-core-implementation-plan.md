# OpenClaw Ask AI Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded OpenClaw chat behavior with a declarative, Odoo-administered Ask AI core that resolves agents, topics, sources, default prompts, and runtime bundles per session while preserving the existing request approval pipeline.

**Architecture:** Keep Odoo as the product source of truth and move runtime resolution there, then send a compact `runtime_bundle` to the control-plane so the gateway executes runtime instead of defining product behavior. Preserve `openclaw.request` as the only mutation path, add shared schema validation across Odoo/control-plane/executor, and migrate one pilot domain (`CRM contacts`) end-to-end before touching broader UX parity.

**Tech Stack:** Odoo 19 ORM/XML views/ACLs, Python 3.12, OpenRouter-backed FastAPI control-plane, JSON Schema validation, Odoo `TransactionCase`, Python `unittest` and `pytest`

---

## File Map

**Odoo models**

- Create: `addons_custom/openclaw/models/openclaw_ai_agent.py`
  Responsibility: `openclaw.ai.agent` record and agent-owned relationships.
- Create: `addons_custom/openclaw/models/openclaw_ai_topic.py`
  Responsibility: `openclaw.ai.topic`, `openclaw.ai.tool`, and `openclaw.ai.topic.tool`.
- Create: `addons_custom/openclaw/models/openclaw_ai_source.py`
  Responsibility: `openclaw.ai.source`.
- Create: `addons_custom/openclaw/models/openclaw_ai_default_prompt.py`
  Responsibility: `openclaw.ai.default_prompt` and `openclaw.ai.default_prompt.button`.
- Create: `addons_custom/openclaw/models/openclaw_ai_llm_profile.py`
  Responsibility: `openclaw.ai.llm_profile`.
- Create: `addons_custom/openclaw/models/openclaw_ai_runtime.py`
  Responsibility: runtime resolution, bundle compilation, and schema loading/validation on the Odoo side.
- Modify: `addons_custom/openclaw/models/openclaw_chat.py`
  Responsibility: session fields, runtime persistence, and gateway call integration.
- Modify: `addons_custom/openclaw/models/openclaw_request.py`
  Responsibility: optional runtime hash/schema traceability fields and executor-side validation hooks.
- Modify: `addons_custom/openclaw/models/gateway_client.py`
  Responsibility: send `runtime_bundle` to `chat.reply`.
- Modify: `addons_custom/openclaw/models/__init__.py`
  Responsibility: import the new model modules.

**Odoo security, views, data**

- Modify: `addons_custom/openclaw/security/ir.model.access.csv`
  Responsibility: CRUD access for the new declarative AI models.
- Modify: `addons_custom/openclaw/security/openclaw_security.xml`
  Responsibility: record rules if any of the new models need scoped visibility.
- Create: `addons_custom/openclaw/views/openclaw_ai_views.xml`
  Responsibility: admin menus, list/form views, and actions for agents/topics/tools/sources/default prompts/llm profiles.
- Modify: `addons_custom/openclaw/views/openclaw_views.xml`
  Responsibility: optionally link the new admin area under the existing OpenClaw root menu.
- Create: `addons_custom/openclaw/data/openclaw_ai_tool_data.xml`
  Responsibility: canonical base tool records.
- Create: `addons_custom/openclaw/data/openclaw_ai_pilot_crm_contacts.xml`
  Responsibility: pilot `CRM contacts` llm profile, agent, topics, sources, and default prompts.
- Modify: `addons_custom/openclaw/__manifest__.py`
  Responsibility: register new XML files in module data.

**Shared schemas**

- Create: `shared/openclaw_schemas/runtime_bundle.v1.json`
- Create: `shared/openclaw_schemas/suggested_action.v1.json`
- Create: `shared/openclaw_schemas/local_odoo_action.v1.json`
  Responsibility: single source of truth for the core runtime and action payloads.

**Control-plane**

- Create: `control-plane/app/chat_runtime.py`
  Responsibility: bundle validation/loading, prompt section flattening, and bundle-first runtime handling outside `mcp_gateway.py`.
- Create: `control-plane/app/schema_validation.py`
  Responsibility: shared schema loading and validation helpers.
- Modify: `control-plane/app/mcp_gateway.py`
  Responsibility: accept `runtime_bundle`, run bundle-first behavior, and keep legacy routing as fallback only.
- Modify: `control-plane/app/config.py`
  Responsibility: optional shared schema root setting if needed.
- Modify: `control-plane/requirements.txt`
  Responsibility: add JSON Schema validation dependency.

**Dependencies**

- Modify: `odoo/requirements.txt`
  Responsibility: add the same JSON Schema validation dependency used in Odoo.

**Tests**

- Create: `addons_custom/openclaw/tests/test_openclaw_ai_registry.py`
  Responsibility: model registry, required fields, and access contract.
- Create: `addons_custom/openclaw/tests/test_openclaw_ai_admin_views.py`
  Responsibility: menu/action/view loading for the new admin area.
- Create: `addons_custom/openclaw/tests/test_openclaw_ai_runtime.py`
  Responsibility: default prompt resolution, prompt precedence, and session bundle persistence.
- Create: `addons_custom/openclaw/tests/test_openclaw_ai_gateway_bundle.py`
  Responsibility: Odoo chat path sends `runtime_bundle` and handles bundle-aware replies.
- Create: `addons_custom/openclaw/tests/test_openclaw_ai_crm_contacts_pilot.py`
  Responsibility: pilot domain records resolve the expected agent/topic/tool set.
- Modify: `addons_custom/openclaw/tests/__init__.py`
  Responsibility: import the new test modules.
- Create: `control-plane/app/tests/test_chat_runtime_bundle.py`
  Responsibility: schema validation and bundle-first execution behavior.
- Modify: `control-plane/app/tests/test_tool_chat_reply_contract.py`
  Responsibility: bundle-first behavior and fallback compatibility coverage.

**Docs**

- Modify: `docs/brain/openclaw.md`
  Responsibility: document the new Ask AI core and runtime ownership split.
- Create: `docs/brain/openclaw_ask_ai_core.md`
  Responsibility: vault note for the declarative runtime model and pilot rollout.

---

### Task 1: Lock the declarative AI registry contract in Odoo tests

**Files:**
- Create: `addons_custom/openclaw/tests/test_openclaw_ai_registry.py`
- Modify: `addons_custom/openclaw/tests/__init__.py`
- Test: `addons_custom/openclaw/tests/test_openclaw_ai_registry.py`

- [ ] **Step 1: Write the failing test**

Add a `TransactionCase` that asserts:
- `openclaw.ai.agent`
- `openclaw.ai.topic`
- `openclaw.ai.tool`
- `openclaw.ai.source`
- `openclaw.ai.default_prompt`
- `openclaw.ai.default_prompt.button`
- `openclaw.ai.llm_profile`

are all registered, and that `openclaw.chat.session` exposes:
- `origin_kind`
- `origin_model`
- `origin_res_id`
- `resolved_agent_id`
- `resolved_default_prompt_id`
- `resolved_llm_profile_id`
- `runtime_bundle_version`
- `runtime_bundle_json`

```python
@tagged("post_install", "-at_install")
class TestOpenClawAiRegistry(TransactionCase):
    def test_ai_models_are_registered(self):
        for model_name in (
            "openclaw.ai.agent",
            "openclaw.ai.topic",
            "openclaw.ai.tool",
            "openclaw.ai.source",
            "openclaw.ai.default_prompt",
            "openclaw.ai.default_prompt.button",
            "openclaw.ai.llm_profile",
        ):
            self.assertIn(model_name, self.env)

    def test_chat_session_exposes_runtime_fields(self):
        session_fields = self.env["openclaw.chat.session"]._fields
        self.assertIn("runtime_bundle_json", session_fields)
        self.assertIn("resolved_agent_id", session_fields)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
docker exec odoo19_sh_imitation-odoo-1 odoo -c /etc/odoo/odoo.conf -d esenssi -u openclaw --test-enable --test-tags openclaw --stop-after-init --http-port=8071
```

Expected: FAIL because the new models and session fields do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create skeleton model files with `_name` declarations and add the new session fields to `openclaw.chat.session`.

```python
class OpenClawAiAgent(models.Model):
    _name = "openclaw.ai.agent"
    _description = "OpenClaw AI Agent"

    name = fields.Char(required=True)
    key = fields.Char(required=True)
    active = fields.Boolean(default=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run the same Odoo command again.

Expected: PASS for the new registry test; unrelated pre-existing failures must be treated as blockers and fixed before moving on.

- [ ] **Step 5: Commit**

```bash
git add addons_custom/openclaw/tests/test_openclaw_ai_registry.py addons_custom/openclaw/tests/__init__.py addons_custom/openclaw/models/openclaw_ai_agent.py addons_custom/openclaw/models/openclaw_ai_topic.py addons_custom/openclaw/models/openclaw_ai_source.py addons_custom/openclaw/models/openclaw_ai_default_prompt.py addons_custom/openclaw/models/openclaw_ai_llm_profile.py addons_custom/openclaw/models/openclaw_chat.py addons_custom/openclaw/models/__init__.py
git commit -m "test: lock OpenClaw Ask AI registry contract"
```

### Task 2: Implement the relational model layer and security contract

**Files:**
- Modify: `addons_custom/openclaw/models/openclaw_ai_agent.py`
- Modify: `addons_custom/openclaw/models/openclaw_ai_topic.py`
- Modify: `addons_custom/openclaw/models/openclaw_ai_source.py`
- Modify: `addons_custom/openclaw/models/openclaw_ai_default_prompt.py`
- Modify: `addons_custom/openclaw/models/openclaw_ai_llm_profile.py`
- Modify: `addons_custom/openclaw/security/ir.model.access.csv`
- Modify: `addons_custom/openclaw/security/openclaw_security.xml`
- Test: `addons_custom/openclaw/tests/test_openclaw_ai_registry.py`

- [ ] **Step 1: Extend the failing test with relationships and access expectations**

Add assertions for:
- `agent.topic_ids`, `agent.source_ids`, `agent.llm_profile_id`
- `topic.tool_binding_ids`
- `tool.required_policy_action`
- `default_prompt.agent_id`, `default_prompt.button_ids`
- admin can create these records
- regular internal users cannot administer them by default

```python
def test_agent_topic_tool_relationships_exist(self):
    agent_fields = self.env["openclaw.ai.agent"]._fields
    tool_fields = self.env["openclaw.ai.tool"]._fields
    self.assertIn("topic_ids", agent_fields)
    self.assertIn("required_policy_action", tool_fields)
```

- [ ] **Step 2: Run test to verify it fails**

Run the same Odoo module test command.

Expected: FAIL on missing relational fields and/or missing ACL rows.

- [ ] **Step 3: Write minimal implementation**

Implement the relational fields and ACL rows.

```python
topic_ids = fields.Many2many("openclaw.ai.topic", string="Topics")
source_ids = fields.Many2many("openclaw.ai.source", string="Sources")
llm_profile_id = fields.Many2one("openclaw.ai.llm_profile", required=True)

required_policy_action = fields.Selection([
    ("odoo_read", "Odoo Read"),
    ("odoo_write", "Odoo Write"),
    ("docs_read", "Docs Read"),
    ("docs_write", "Docs Write"),
    ("db_read", "DB Read"),
    ("db_write", "DB Write"),
    ("web_search", "Web Search"),
], required=True)
```

Add admin/operator access rows only where needed. Do not grant broad write access to `base.group_user`.

- [ ] **Step 4: Run test to verify it passes**

Run the Odoo module test command again.

Expected: PASS for the registry/relationship/access contract.

- [ ] **Step 5: Commit**

```bash
git add addons_custom/openclaw/models/openclaw_ai_agent.py addons_custom/openclaw/models/openclaw_ai_topic.py addons_custom/openclaw/models/openclaw_ai_source.py addons_custom/openclaw/models/openclaw_ai_default_prompt.py addons_custom/openclaw/models/openclaw_ai_llm_profile.py addons_custom/openclaw/security/ir.model.access.csv addons_custom/openclaw/security/openclaw_security.xml addons_custom/openclaw/tests/test_openclaw_ai_registry.py
git commit -m "feat(openclaw): add declarative AI model relations"
```

### Task 3: Add the admin views and manifest wiring

**Files:**
- Create: `addons_custom/openclaw/views/openclaw_ai_views.xml`
- Modify: `addons_custom/openclaw/views/openclaw_views.xml`
- Modify: `addons_custom/openclaw/__manifest__.py`
- Create: `addons_custom/openclaw/tests/test_openclaw_ai_admin_views.py`
- Modify: `addons_custom/openclaw/tests/__init__.py`
- Test: `addons_custom/openclaw/tests/test_openclaw_ai_admin_views.py`

- [ ] **Step 1: Write the failing test**

Add a `TransactionCase` that asserts the new XML ids resolve:
- `openclaw.action_openclaw_ai_agent`
- `openclaw.action_openclaw_ai_topic`
- `openclaw.action_openclaw_ai_default_prompt`
- `openclaw.menu_openclaw_ai`

```python
def test_admin_views_and_actions_are_registered(self):
    self.env.ref("openclaw.action_openclaw_ai_agent")
    self.env.ref("openclaw.action_openclaw_ai_topic")
    self.env.ref("openclaw.action_openclaw_ai_default_prompt")
    self.env.ref("openclaw.menu_openclaw_ai")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
docker exec odoo19_sh_imitation-odoo-1 odoo -c /etc/odoo/odoo.conf -d esenssi -u openclaw --test-enable --test-tags openclaw --stop-after-init --http-port=8071
```

Expected: FAIL because the actions/menus/views are not loaded yet.

- [ ] **Step 3: Write minimal implementation**

Add a dedicated admin XML file instead of bloating `openclaw_views.xml`.

```xml
<record id="action_openclaw_ai_agent" model="ir.actions.act_window">
  <field name="name">AI Agents</field>
  <field name="res_model">openclaw.ai.agent</field>
  <field name="view_mode">list,form</field>
</record>
```

Register the XML file in `__manifest__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run the Odoo module test command again.

Expected: PASS and module upgrade succeeds with the new admin screens loaded.

- [ ] **Step 5: Commit**

```bash
git add addons_custom/openclaw/views/openclaw_ai_views.xml addons_custom/openclaw/views/openclaw_views.xml addons_custom/openclaw/__manifest__.py addons_custom/openclaw/tests/test_openclaw_ai_admin_views.py addons_custom/openclaw/tests/__init__.py
git commit -m "feat(openclaw): add Ask AI admin views"
```

### Task 4: Lock runtime resolution and prompt precedence in Odoo tests

**Files:**
- Create: `addons_custom/openclaw/tests/test_openclaw_ai_runtime.py`
- Modify: `addons_custom/openclaw/tests/__init__.py`
- Test: `addons_custom/openclaw/tests/test_openclaw_ai_runtime.py`

- [ ] **Step 1: Write the failing test**

Add tests that prove:
- the most specific `default_prompt` wins
- `group_ids` and `company_id` filter prompt eligibility
- `runtime_bundle_json` is persisted on session creation/use
- tool exposure is the intersection of topic tools and policy-allowed actions

```python
def test_model_specific_default_prompt_beats_global(self):
    bundle = self.session._resolve_chat_runtime(origin_model="res.partner")
    self.assertEqual(bundle["default_prompt"]["key"], "crm_contacts")

def test_tool_projection_respects_policy(self):
    bundle = self.session._resolve_chat_runtime(origin_model="res.partner")
    tool_keys = [tool["key"] for tool in bundle["allowed_tools"]]
    self.assertIn("odoo.search_read", tool_keys)
    self.assertNotIn("odoo.create_request", tool_keys)
```

- [ ] **Step 2: Run test to verify it fails**

Run the Odoo module test command.

Expected: FAIL because there is no runtime resolver or bundle compiler yet.

- [ ] **Step 3: Write minimal implementation**

Create `addons_custom/openclaw/models/openclaw_ai_runtime.py` with methods like:
- `_resolve_default_prompt()`
- `_resolve_chat_runtime()`
- `_build_runtime_bundle()`

Keep the runtime bundle compact and versioned.

```python
bundle = {
    "bundle_version": 1,
    "session_origin": {"kind": origin_kind, "model": origin_model, "res_id": origin_res_id},
    "agent": {"id": agent.id, "key": agent.key},
    "allowed_tools": allowed_tools,
}
```

- [ ] **Step 4: Run test to verify it passes**

Run the Odoo module test command again.

Expected: PASS for runtime resolution and prompt precedence.

- [ ] **Step 5: Commit**

```bash
git add addons_custom/openclaw/models/openclaw_ai_runtime.py addons_custom/openclaw/tests/test_openclaw_ai_runtime.py addons_custom/openclaw/tests/__init__.py addons_custom/openclaw/models/openclaw_chat.py
git commit -m "feat(openclaw): add runtime bundle resolution"
```

### Task 5: Integrate runtime bundles into the Odoo chat path

**Files:**
- Modify: `addons_custom/openclaw/models/openclaw_chat.py`
- Modify: `addons_custom/openclaw/models/gateway_client.py`
- Modify: `addons_custom/openclaw/models/openclaw_request.py`
- Create: `addons_custom/openclaw/tests/test_openclaw_ai_gateway_bundle.py`
- Modify: `addons_custom/openclaw/tests/__init__.py`
- Test: `addons_custom/openclaw/tests/test_openclaw_ai_gateway_bundle.py`

- [ ] **Step 1: Write the failing test**

Add a test that patches `OpenClawGatewayClient.chat_reply()` and asserts `runtime_bundle` is sent and the session stores resolved ids.

```python
with patch.object(OpenClawGatewayClient, "chat_reply", return_value={"reply": "ok", "suggested_actions": []}) as chat_mock:
    Session.rpc_send_message(session.id, "hola")
args, kwargs = chat_mock.call_args
self.assertIn("runtime_bundle", kwargs)
```

Also add a fallback test for old sessions without a bundle.

- [ ] **Step 2: Run test to verify it fails**

Run the Odoo module test command.

Expected: FAIL because `gateway_client.chat_reply()` does not accept `runtime_bundle` yet.

- [ ] **Step 3: Write minimal implementation**

Extend the gateway client signature and thread the bundle through `_generate_reply()`.

```python
def chat_reply(self, messages, *, runtime_bundle=None, policy_context=None, ...):
    arguments = {"messages": messages, "runtime_bundle": runtime_bundle or {}}
```

Optionally add `runtime_bundle_hash`/`compiled_schema_version` on requests if the implementation needs request-side traceability now instead of later.

- [ ] **Step 4: Run test to verify it passes**

Run the Odoo module test command again.

Expected: PASS for bundle handoff and legacy fallback behavior.

- [ ] **Step 5: Commit**

```bash
git add addons_custom/openclaw/models/openclaw_chat.py addons_custom/openclaw/models/gateway_client.py addons_custom/openclaw/models/openclaw_request.py addons_custom/openclaw/tests/test_openclaw_ai_gateway_bundle.py addons_custom/openclaw/tests/__init__.py
git commit -m "feat(openclaw): send runtime bundles to gateway"
```

### Task 6: Lock shared schema validation and bundle-first control-plane behavior in tests

**Files:**
- Create: `control-plane/app/tests/test_chat_runtime_bundle.py`
- Modify: `control-plane/app/tests/test_tool_chat_reply_contract.py`
- Test: `control-plane/app/tests/test_chat_runtime_bundle.py`
- Test: `control-plane/app/tests/test_tool_chat_reply_contract.py`

- [ ] **Step 1: Write the failing test**

Add tests that prove:
- invalid `runtime_bundle` is rejected before provider call
- valid bundle bypasses legacy domain routing
- gateway falls back to legacy routing only when no bundle is present
- structured actions are validated against the shared schema

```python
def test_runtime_bundle_short_circuits_legacy_router(self):
    result = self._run(gateway.tool_chat_reply({
        "messages": [{"role": "user", "content": "Busca el contacto ACME"}],
        "runtime_bundle": valid_bundle,
        "policy_context": {"available_policies": [{"key": "p", "allowed_actions": ["odoo_read"]}]},
    }))
    self.assertNotEqual(result["model"], "router")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest control-plane/app/tests/test_chat_runtime_bundle.py control-plane/app/tests/test_tool_chat_reply_contract.py -q
```

Expected: FAIL because the control-plane does not parse or validate `runtime_bundle` yet.

- [ ] **Step 3: Write minimal implementation**

Create the smallest failing-to-passing parser surface in a new helper module, not directly in `mcp_gateway.py`.

```python
def validate_runtime_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    validator.validate(payload)
    return payload
```

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command again.

Expected: PASS for bundle validation and bundle-first behavior.

- [ ] **Step 5: Commit**

```bash
git add control-plane/app/tests/test_chat_runtime_bundle.py control-plane/app/tests/test_tool_chat_reply_contract.py
git commit -m "test(control-plane): lock runtime bundle contract"
```

### Task 7: Implement shared schemas and bundle-first gateway runtime

**Files:**
- Create: `shared/openclaw_schemas/runtime_bundle.v1.json`
- Create: `shared/openclaw_schemas/suggested_action.v1.json`
- Create: `shared/openclaw_schemas/local_odoo_action.v1.json`
- Create: `control-plane/app/chat_runtime.py`
- Create: `control-plane/app/schema_validation.py`
- Modify: `control-plane/app/mcp_gateway.py`
- Modify: `control-plane/app/config.py`
- Modify: `control-plane/requirements.txt`
- Modify: `odoo/requirements.txt`
- Modify: `addons_custom/openclaw/models/openclaw_ai_runtime.py`
- Test: `control-plane/app/tests/test_chat_runtime_bundle.py`
- Test: `control-plane/app/tests/test_tool_chat_reply_contract.py`
- Test: `addons_custom/openclaw/tests/test_openclaw_ai_runtime.py`

- [ ] **Step 1: Add the failing dependency/loader test**

Extend `test_chat_runtime_bundle.py` to assert the schema files are loaded from `shared/openclaw_schemas/`.

```python
def test_runtime_bundle_schema_file_exists(self):
    schema = load_schema("runtime_bundle.v1.json")
    self.assertEqual(schema["type"], "object")
```

- [ ] **Step 2: Run test to verify it fails**

Run the same pytest command.

Expected: FAIL because the shared schema files and loader do not exist.

- [ ] **Step 3: Write minimal implementation**

Add `jsonschema` to both requirements files and implement shared schema loading/validation.

```text
jsonschema==4.23.0
```

Keep bundle-specific logic in `chat_runtime.py` and let `mcp_gateway.py` delegate to it.

- [ ] **Step 4: Rebuild the affected services**

Run:

```powershell
docker compose -f compose.yaml -f compose.admin.yaml up -d --build odoo control-plane
```

Expected: both images rebuild successfully with the new dependency.

- [ ] **Step 5: Run tests to verify they pass**

Run:

```powershell
python -m pytest control-plane/app/tests/test_chat_runtime_bundle.py control-plane/app/tests/test_tool_chat_reply_contract.py -q
docker exec odoo19_sh_imitation-odoo-1 odoo -c /etc/odoo/odoo.conf -d esenssi -u openclaw --test-enable --test-tags openclaw --stop-after-init --http-port=8071
```

Expected: PASS on both sides; runtime and action schemas are enforced.

- [ ] **Step 6: Commit**

```bash
git add shared/openclaw_schemas/runtime_bundle.v1.json shared/openclaw_schemas/suggested_action.v1.json shared/openclaw_schemas/local_odoo_action.v1.json control-plane/app/chat_runtime.py control-plane/app/schema_validation.py control-plane/app/mcp_gateway.py control-plane/app/config.py control-plane/requirements.txt odoo/requirements.txt addons_custom/openclaw/models/openclaw_ai_runtime.py
git commit -m "feat(openclaw): add shared runtime schema validation"
```

### Task 8: Seed the CRM contacts pilot domain and prove end-to-end resolution

**Files:**
- Create: `addons_custom/openclaw/data/openclaw_ai_tool_data.xml`
- Create: `addons_custom/openclaw/data/openclaw_ai_pilot_crm_contacts.xml`
- Modify: `addons_custom/openclaw/__manifest__.py`
- Create: `addons_custom/openclaw/tests/test_openclaw_ai_crm_contacts_pilot.py`
- Modify: `addons_custom/openclaw/tests/__init__.py`
- Test: `addons_custom/openclaw/tests/test_openclaw_ai_crm_contacts_pilot.py`

- [ ] **Step 1: Write the failing test**

Add a test that loads the seeded pilot records and asserts:
- `CRM Contacts` default prompt resolves on `res.partner`
- the linked agent uses the expected llm profile
- the allowed tool projection contains `odoo.search_read` and `odoo.create_request`

```python
def test_res_partner_context_resolves_crm_contacts_agent(self):
    bundle = self.session._resolve_chat_runtime(origin_kind="model", origin_model="res.partner")
    self.assertEqual(bundle["agent"]["key"], "crm_contacts_agent")
```

- [ ] **Step 2: Run test to verify it fails**

Run the Odoo module test command.

Expected: FAIL because the pilot XML data is not loaded yet.

- [ ] **Step 3: Write minimal implementation**

Seed:
- base tool catalog
- one llm profile pointing at the existing OpenRouter runtime
- one `CRM contacts` topic
- one agent
- one model-specific default prompt for `res.partner`
- one or two default prompt buttons

```xml
<record id="openclaw_ai_default_prompt_crm_contacts" model="openclaw.ai.default_prompt">
  <field name="name">CRM Contacts</field>
  <field name="agent_id" ref="openclaw_ai_agent_crm_contacts"/>
</record>
```

- [ ] **Step 4: Run test to verify it passes**

Run the Odoo module test command again.

Expected: PASS and the pilot bundle resolves end-to-end.

- [ ] **Step 5: Commit**

```bash
git add addons_custom/openclaw/data/openclaw_ai_tool_data.xml addons_custom/openclaw/data/openclaw_ai_pilot_crm_contacts.xml addons_custom/openclaw/__manifest__.py addons_custom/openclaw/tests/test_openclaw_ai_crm_contacts_pilot.py addons_custom/openclaw/tests/__init__.py
git commit -m "feat(openclaw): seed CRM contacts Ask AI pilot"
```

### Task 9: Update docs and run final verification

**Files:**
- Modify: `docs/brain/openclaw.md`
- Create: `docs/brain/openclaw_ask_ai_core.md`
- Test: `addons_custom/openclaw/tests/test_openclaw_ai_registry.py`
- Test: `addons_custom/openclaw/tests/test_openclaw_ai_runtime.py`
- Test: `addons_custom/openclaw/tests/test_openclaw_ai_gateway_bundle.py`
- Test: `addons_custom/openclaw/tests/test_openclaw_ai_crm_contacts_pilot.py`
- Test: `control-plane/app/tests/test_chat_runtime_bundle.py`
- Test: `control-plane/app/tests/test_tool_chat_reply_contract.py`

- [ ] **Step 1: Document the new architecture**

Update the vault so it explains:
- Odoo owns runtime resolution
- control-plane executes bundle-first
- request cycle still guards mutations
- `CRM contacts` is the first migrated pilot

- [ ] **Step 2: Run focused Python verification**

Run:

```powershell
python -m pytest control-plane/app/tests/test_chat_runtime_bundle.py control-plane/app/tests/test_tool_chat_reply_contract.py -q
python -m py_compile control-plane/app/chat_runtime.py control-plane/app/schema_validation.py addons_custom/openclaw/models/openclaw_ai_agent.py addons_custom/openclaw/models/openclaw_ai_topic.py addons_custom/openclaw/models/openclaw_ai_source.py addons_custom/openclaw/models/openclaw_ai_default_prompt.py addons_custom/openclaw/models/openclaw_ai_llm_profile.py addons_custom/openclaw/models/openclaw_ai_runtime.py addons_custom/openclaw/models/openclaw_chat.py addons_custom/openclaw/models/gateway_client.py
```

Expected: PASS and no syntax errors.

- [ ] **Step 3: Run full Odoo verification**

Run:

```powershell
docker exec odoo19_sh_imitation-odoo-1 odoo -c /etc/odoo/odoo.conf -d esenssi -u openclaw --test-enable --test-tags openclaw --stop-after-init --http-port=8071
```

Expected: PASS for the full OpenClaw module test suite.

- [ ] **Step 4: Run service-level verification**

Run:

```powershell
docker compose -f compose.yaml -f compose.admin.yaml restart odoo control-plane
```

Then manually verify in Odoo:
- OpenClaw admin menus load
- creating a new chat on `res.partner` resolves the `CRM contacts` runtime
- proposed actions still materialize as `openclaw.request`

- [ ] **Step 5: Commit**

```bash
git add docs/brain/openclaw.md docs/brain/openclaw_ask_ai_core.md
git commit -m "docs(openclaw): document Ask AI core runtime"
```

### Task 10: Clean up legacy routing only where the pilot replaced it

**Files:**
- Modify: `control-plane/app/mcp_gateway.py`
- Test: `control-plane/app/tests/test_tool_chat_reply_contract.py`

- [ ] **Step 1: Write the failing test**

Add a test that ensures the `CRM contacts` pilot path uses the runtime bundle and does not depend on the legacy contact router when a valid bundle is present.

```python
def test_valid_bundle_bypasses_crm_contact_router(self):
    result = self._run(gateway.tool_chat_reply({...}))
    self.assertEqual(result["provider"], "openrouter")
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest control-plane/app/tests/test_tool_chat_reply_contract.py -q
```

Expected: FAIL because the legacy router still wins even when a valid bundle is available.

- [ ] **Step 3: Write minimal implementation**

Reduce only the overlapping CRM contacts hardcode to fallback behavior:
- bundle present -> bundle path
- no bundle -> legacy router path

Do not remove dashboard or other domain routers in the same commit.

- [ ] **Step 4: Run test to verify it passes**

Run the same pytest command again.

Expected: PASS and no regression in the existing fallback tests.

- [ ] **Step 5: Commit**

```bash
git add control-plane/app/mcp_gateway.py control-plane/app/tests/test_tool_chat_reply_contract.py
git commit -m "refactor(control-plane): make CRM routing bundle-first"
```

---

## Final Verification Checklist

- [ ] New Odoo AI models load and are manageable from admin views
- [ ] `runtime_bundle_json` is persisted on sessions
- [ ] Shared JSON schemas exist in `shared/openclaw_schemas/`
- [ ] Both Odoo and control-plane validate payloads against shared schemas
- [ ] `CRM contacts` resolves from `res.partner` without hardcoded business routing
- [ ] Mutable actions still flow through `openclaw.request`
- [ ] Legacy routing remains available only for unmigrated or bundle-less sessions

---

## Notes for the Implementer

- Do not try to ship `AI fields`, `Ctrl+K`, and the declarative core in the same pass.
- Do not keep expanding `control-plane/app/mcp_gateway.py` with new product logic; push new runtime helpers into dedicated modules.
- Do not let `openclaw.policy` become a proxy for agent behavior. Its job is authorization, not assistant design.
- If Odoo module tests surface unrelated pre-existing failures, stop and isolate them before continuing; do not code around unknown red tests.
