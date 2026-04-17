# OpenClaw Chat Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the amber chat shell with a light ChatGPT/Claude-style admin UI and wire assistant suggestions to the existing `openclaw.request` approval pipeline, so users can approve/reject/execute proposed actions from the chat.

**Architecture:** Three layers change in lockstep. (1) `openclaw.request` gets `session_id`, `message_id`, `origin`, `rationale` columns and a soft-required policy so chat-originated rows can exist in draft even without a policy. (2) `tool_chat_reply` in the control-plane gateway returns `{reply, suggested_actions}` parsed from a JSON-only LLM response. (3) The OWL chat action becomes a component tree (Sidebar, Messages, ActionCard, RequestDrawer, Composer) reskinned with the control-plane's light tokens.

**Tech Stack:** Odoo 19 (Python + OWL + SCSS), FastAPI gateway (httpx + OpenRouter), `unittest` for gateway tests, `odoo.tests.common.TransactionCase` for addon tests.

---

## Spec Reference

Full design: `docs/superpowers/specs/2026-04-17-openclaw-chat-redesign-design.md` (commit `28d7117`).

## File Structure

**Modified:**
- `addons_custom/openclaw/__manifest__.py` — unchanged unless new XML asset is required.
- `addons_custom/openclaw/models/openclaw_request.py` — add 4 fields, `_chat_card_payload()`, policy soft-required Python constraint.
- `addons_custom/openclaw/models/openclaw_chat.py` — extend session/message with reverse FKs, add `_build_policy_context`, `_materialize_suggestions`, and three new RPCs.
- `addons_custom/openclaw/models/gateway_client.py` — `chat_reply` returns `dict` (reply + suggested_actions) instead of `str`.
- `addons_custom/openclaw/static/src/js/openclaw_chat.js` — split into sub-components, add approve/reject/drawer state and actions.
- `addons_custom/openclaw/static/src/xml/openclaw_chat.xml` — new templates for ChatSidebar, ChatMessages, ActionCard, RequestDrawer, ChatComposer.
- `addons_custom/openclaw/static/src/scss/openclaw_chat.scss` — full replacement with light control-plane tokens.
- `control-plane/app/mcp_gateway.py` — extend `tool_chat_reply` input/output schema and system prompt; add `_parse_llm_envelope` helper.

**Created:**
- `addons_custom/openclaw/tests/test_openclaw_chat_suggestions.py`
- `addons_custom/openclaw/tests/test_openclaw_chat_approval.py`
- `addons_custom/openclaw/tests/test_openclaw_request_origin.py`
- `control-plane/app/tests/__init__.py`
- `control-plane/app/tests/test_tool_chat_reply_contract.py`

**Unchanged:**
- `openclaw.policy` model + form.
- `openclaw.request` state machine (`action_submit`, `action_approve`, `action_execute`, `_execute_one`).
- Security groups (`openclaw.group_openclaw_user`, `openclaw.group_openclaw_admin`).

---

## Conventions for this plan

- **Odoo tests:** use `@tagged("post_install", "-at_install")` + `TransactionCase`, matching `tests/test_res_config_settings.py`.
- **Gateway tests:** `unittest` standard library (no new dependency). Run via `python -m unittest discover control-plane/app/tests`.
- **Commits:** one commit per task after steps pass. Prefix with `feat:`, `test:`, or `refactor:` per conventional commits style the repo already uses.
- **Gateway hot-reload:** assume `docker compose restart control-plane` after gateway edits. Odoo edits require `odoo -u openclaw`.

---

### Task 1: Extend `openclaw.request` with chat fields and soft-required policy

**Files:**
- Modify: `addons_custom/openclaw/models/openclaw_request.py`
- Test: `addons_custom/openclaw/tests/test_openclaw_request_origin.py`

- [ ] **Step 1: Write the failing tests**

Create the test file:

```python
# addons_custom/openclaw/tests/test_openclaw_request_origin.py
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOpenClawRequestOrigin(TransactionCase):
    def setUp(self):
        super().setUp()
        self.policy = self.env["openclaw.policy"].create({
            "name": "Test Policy",
            "key": "test_policy",
            "sequence": 10,
        })

    def test_manual_request_defaults_to_manual_origin(self):
        request = self.env["openclaw.request"].create({
            "name": "Manual request",
            "instruction": "Do something",
            "policy_id": self.policy.id,
        })
        self.assertEqual(request.origin, "manual")
        self.assertFalse(request.session_id)
        self.assertFalse(request.message_id)
        self.assertFalse(request.rationale)

    def test_chat_suggestion_can_be_created_without_policy_in_draft(self):
        session = self.env["openclaw.chat.session"].create({"name": "s"})
        request = self.env["openclaw.request"].create({
            "name": "Blocked",
            "instruction": "Do something",
            "origin": "chat_suggestion",
            "session_id": session.id,
            "decision_note": "policy_key 'missing' not found",
        })
        self.assertFalse(request.policy_id)
        self.assertEqual(request.state, "draft")

    def test_submit_without_policy_raises(self):
        session = self.env["openclaw.chat.session"].create({"name": "s"})
        request = self.env["openclaw.request"].create({
            "name": "Blocked",
            "instruction": "Do something",
            "origin": "chat_suggestion",
            "session_id": session.id,
            "decision_note": "blocked",
        })
        with self.assertRaises(ValidationError):
            request.action_submit()

    def test_chat_card_payload_shape(self):
        request = self.env["openclaw.request"].create({
            "name": "Card",
            "instruction": "Update contact",
            "policy_id": self.policy.id,
            "origin": "chat_suggestion",
            "rationale": "user asked",
            "action_type": "odoo_write",
            "target_model": "res.partner",
            "target_ref": "42",
        })
        payload = request._chat_card_payload()
        self.assertEqual(payload["id"], request.id)
        self.assertEqual(payload["state"], "draft")
        self.assertEqual(payload["action_type"], "odoo_write")
        self.assertEqual(payload["policy_key"], "test_policy")
        self.assertEqual(payload["target_model"], "res.partner")
        self.assertEqual(payload["rationale"], "user asked")
        self.assertFalse(payload["blocked"])
```

Also register the new test module:

```python
# addons_custom/openclaw/tests/__init__.py
from . import test_res_config_settings
from . import test_openclaw_request_origin
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose exec odoo odoo --test-tags openclaw -d odoo -i openclaw --stop-after-init`

Expected: fails — fields `origin`, `session_id`, `message_id`, `rationale` do not exist; `policy_id` is required so creation without policy raises.

- [ ] **Step 3: Add the fields and make policy_id soft-required**

Edit `addons_custom/openclaw/models/openclaw_request.py`. Find the `policy_id` line and change `required=True` to `required=False`. Keep `ondelete='restrict'`. Add the new fields just below the existing `state` block. Add the constraint and helper at the end of the class.

Field additions (place near the other fields, grouped logically — after the `state`/`approval_required` block is a good spot):

```python
    session_id = fields.Many2one(
        'openclaw.chat.session',
        string='Chat Session',
        ondelete='set null',
        index=True,
    )
    message_id = fields.Many2one(
        'openclaw.chat.message',
        string='Originating Message',
        ondelete='set null',
        index=True,
    )
    origin = fields.Selection(
        [('manual', 'Manual'), ('chat_suggestion', 'Chat Suggestion')],
        required=True,
        default='manual',
    )
    rationale = fields.Text(string='Agent Rationale', readonly=True)
```

Change:

```python
    policy_id = fields.Many2one('openclaw.policy', string='Policy', required=True, ondelete='restrict')
```

to:

```python
    policy_id = fields.Many2one('openclaw.policy', string='Policy', ondelete='restrict')
```

Add the constraint (anywhere in the class body; convention in Odoo is after computed fields / before action methods). Also add the payload helper at the end of the class, before the final line of the class:

```python
    @api.constrains('state', 'policy_id')
    def _check_policy_required_for_submit(self):
        for request in self:
            if request.state != 'draft' and not request.policy_id:
                raise ValidationError(_('Cannot transition out of draft without a policy.'))

    def _chat_card_payload(self) -> dict[str, Any]:
        self.ensure_one()
        return {
            'id': self.id,
            'state': self.state,
            'action_type': self.action_type,
            'custom_tool_name': self.custom_tool_name or '',
            'policy_name': self.policy_id.name if self.policy_id else '',
            'policy_key': self.policy_id.key if self.policy_id else '',
            'target_model': self.target_model or '',
            'target_ref': self.target_ref or '',
            'rationale': self.rationale or '',
            'result_summary': self.result_summary or '',
            'error_message': self.error_message or '',
            'decision_note': self.decision_note or '',
            'blocked': (
                self.state == 'draft'
                and bool(self.decision_note)
                and not self.policy_id
            ),
        }
```

Also update `action_submit` to raise before the existing body when `policy_id` missing (the constraint catches the write, but we want a clean user-facing error):

Find:

```python
    def action_submit(self):
        for request in self:
            if request.state != 'draft':
                raise ValidationError(_('Only draft requests can be submitted.'))
```

Add after the existing check, still inside the loop:

```python
            if not request.policy_id:
                raise ValidationError(_('This request has no policy assigned and cannot be submitted.'))
```

- [ ] **Step 4: Update the policy form view to keep policy_id required from the UI**

The field on the form view at `addons_custom/openclaw/views/openclaw_views.xml` already has the field declared without explicit `required="1"`. Add `required="1"` to the `<field name="policy_id"/>` inside `view_openclaw_request_form` so manual creation via the form still forces it:

Find:

```xml
                <field name="policy_id"/>
```

in the request form (around line 170-180, inside the first `<group>`). Replace with:

```xml
                <field name="policy_id" required="1"/>
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker compose exec odoo odoo --test-tags openclaw -d odoo -u openclaw --stop-after-init`

Expected: PASS for `TestOpenClawRequestOrigin` (4 tests).

- [ ] **Step 6: Commit**

```bash
git add addons_custom/openclaw/models/openclaw_request.py \
        addons_custom/openclaw/views/openclaw_views.xml \
        addons_custom/openclaw/tests/__init__.py \
        addons_custom/openclaw/tests/test_openclaw_request_origin.py
git commit -m "feat(openclaw): add chat linkage fields and soft-required policy on requests"
```

---

### Task 2: Wire One2many on session and message + include requests in message payload

**Files:**
- Modify: `addons_custom/openclaw/models/openclaw_chat.py`
- Test: `addons_custom/openclaw/tests/test_openclaw_chat_suggestions.py` (create skeleton with one test for now; extended in later tasks)

- [ ] **Step 1: Write the failing tests**

```python
# addons_custom/openclaw/tests/test_openclaw_chat_suggestions.py
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOpenClawChatOne2Many(TransactionCase):
    def setUp(self):
        super().setUp()
        self.policy = self.env["openclaw.policy"].create({
            "name": "Test Policy",
            "key": "test_policy",
            "sequence": 10,
        })
        self.session = self.env["openclaw.chat.session"].create({"name": "s"})
        self.message = self.env["openclaw.chat.message"].create({
            "session_id": self.session.id,
            "role": "assistant",
            "content": "ok",
        })

    def test_session_exposes_request_ids(self):
        request = self.env["openclaw.request"].create({
            "name": "r",
            "instruction": "i",
            "policy_id": self.policy.id,
            "session_id": self.session.id,
            "message_id": self.message.id,
            "origin": "chat_suggestion",
        })
        self.assertIn(request, self.session.request_ids)
        self.assertIn(request, self.message.request_ids)

    def test_message_payload_includes_requests(self):
        request = self.env["openclaw.request"].create({
            "name": "r",
            "instruction": "i",
            "policy_id": self.policy.id,
            "session_id": self.session.id,
            "message_id": self.message.id,
            "origin": "chat_suggestion",
        })
        payload = self.session._message_payload(self.message)
        self.assertIn("requests", payload)
        self.assertEqual(len(payload["requests"]), 1)
        self.assertEqual(payload["requests"][0]["id"], request.id)
```

Register in `__init__.py`:

```python
# addons_custom/openclaw/tests/__init__.py
from . import test_res_config_settings
from . import test_openclaw_request_origin
from . import test_openclaw_chat_suggestions
```

- [ ] **Step 2: Run to verify they fail**

Run: `docker compose exec odoo odoo --test-tags openclaw -d odoo -u openclaw --stop-after-init`

Expected: `AttributeError: 'openclaw.chat.session' object has no attribute 'request_ids'`.

- [ ] **Step 3: Add the One2many fields and extend the payload**

In `addons_custom/openclaw/models/openclaw_chat.py`, inside `OpenClawChatSession`, add after `message_ids`:

```python
    request_ids = fields.One2many(
        'openclaw.request',
        'session_id',
        string='Chat Actions',
    )
```

Inside `OpenClawChatMessage`, add after the existing fields:

```python
    request_ids = fields.One2many(
        'openclaw.request',
        'message_id',
        string='Suggested Actions',
    )
```

Extend `_message_payload` (static method at the top of `OpenClawChatSession`). Change:

```python
    @staticmethod
    def _message_payload(message) -> dict[str, Any]:
        return {
            'id': message.id,
            'session_id': message.session_id.id,
            'role': message.role,
            'content': message.content,
            'user_id': message.user_id.id if message.user_id else False,
            'author_name': message.user_id.display_name if message.role == 'user' and message.user_id else 'OpenClaw',
            'create_date': message.create_date.isoformat() if message.create_date else False,
        }
```

to:

```python
    @staticmethod
    def _message_payload(message) -> dict[str, Any]:
        ordered_requests = message.request_ids.sorted(key=lambda r: (r.create_date or fields.Datetime.now(), r.id))
        return {
            'id': message.id,
            'session_id': message.session_id.id,
            'role': message.role,
            'content': message.content,
            'user_id': message.user_id.id if message.user_id else False,
            'author_name': message.user_id.display_name if message.role == 'user' and message.user_id else 'OpenClaw',
            'create_date': message.create_date.isoformat() if message.create_date else False,
            'requests': [request._chat_card_payload() for request in ordered_requests],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose exec odoo odoo --test-tags openclaw -d odoo -u openclaw --stop-after-init`

Expected: PASS for `TestOpenClawChatOne2Many` (2 tests) and earlier tests remain green.

- [ ] **Step 5: Commit**

```bash
git add addons_custom/openclaw/models/openclaw_chat.py \
        addons_custom/openclaw/tests/__init__.py \
        addons_custom/openclaw/tests/test_openclaw_chat_suggestions.py
git commit -m "feat(openclaw): expose chat requests via One2many and enrich message payload"
```

---

### Task 3: Gateway parser — extract `_parse_llm_envelope` helper

**Files:**
- Create: `control-plane/app/tests/__init__.py` (empty)
- Create: `control-plane/app/tests/test_tool_chat_reply_contract.py`
- Modify: `control-plane/app/mcp_gateway.py`

- [ ] **Step 1: Write the failing tests**

```python
# control-plane/app/tests/__init__.py
```

(empty file)

```python
# control-plane/app/tests/test_tool_chat_reply_contract.py
import unittest

from app.mcp_gateway import _parse_llm_envelope


class TestParseLlmEnvelope(unittest.TestCase):
    def test_parses_well_formed_json(self):
        raw = '{"reply": "hola", "suggested_actions": [{"title": "X"}]}'
        reply, actions = _parse_llm_envelope(raw)
        self.assertEqual(reply, "hola")
        self.assertEqual(actions, [{"title": "X"}])

    def test_missing_suggested_actions_defaults_empty(self):
        raw = '{"reply": "hola"}'
        reply, actions = _parse_llm_envelope(raw)
        self.assertEqual(reply, "hola")
        self.assertEqual(actions, [])

    def test_malformed_json_falls_back_to_text_reply(self):
        raw = "plain text with no json at all"
        reply, actions = _parse_llm_envelope(raw)
        self.assertEqual(reply, "plain text with no json at all")
        self.assertEqual(actions, [])

    def test_empty_text_returns_empty_reply(self):
        reply, actions = _parse_llm_envelope("")
        self.assertEqual(reply, "")
        self.assertEqual(actions, [])

    def test_suggested_actions_not_list_is_normalized_to_empty(self):
        raw = '{"reply": "ok", "suggested_actions": "not a list"}'
        reply, actions = _parse_llm_envelope(raw)
        self.assertEqual(reply, "ok")
        self.assertEqual(actions, [])

    def test_json_with_surrounding_whitespace(self):
        raw = '  \n  {"reply": "ok", "suggested_actions": []}  \n'
        reply, actions = _parse_llm_envelope(raw)
        self.assertEqual(reply, "ok")
        self.assertEqual(actions, [])

    def test_non_string_reply_is_coerced(self):
        raw = '{"reply": 123, "suggested_actions": []}'
        reply, actions = _parse_llm_envelope(raw)
        self.assertEqual(reply, "123")
        self.assertEqual(actions, [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd control-plane && python -m unittest discover app/tests -v`

Expected: `ImportError: cannot import name '_parse_llm_envelope' from 'app.mcp_gateway'`.

- [ ] **Step 3: Implement `_parse_llm_envelope`**

In `control-plane/app/mcp_gateway.py`, add near the top of the module (after the existing helper functions around line 30):

```python
def _parse_llm_envelope(raw_text: str) -> tuple[str, list[dict[str, Any]]]:
    """Parse an LLM response expected to be a JSON object with keys
    `reply` (string) and `suggested_actions` (list).

    Falls back to using the raw text as `reply` when JSON parsing fails
    or when the payload does not match the expected shape.
    """
    stripped = (raw_text or "").strip()
    if not stripped:
        return "", []
    try:
        decoded = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return stripped, []
    if not isinstance(decoded, dict):
        return stripped, []
    reply = decoded.get("reply", "")
    reply_str = "" if reply is None else str(reply)
    raw_actions = decoded.get("suggested_actions")
    actions = raw_actions if isinstance(raw_actions, list) else []
    return reply_str, actions
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd control-plane && python -m unittest discover app/tests -v`

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add control-plane/app/tests/__init__.py \
        control-plane/app/tests/test_tool_chat_reply_contract.py \
        control-plane/app/mcp_gateway.py
git commit -m "feat(control-plane): add _parse_llm_envelope helper with JSON fallback"
```

---

### Task 4: Gateway — rewire `tool_chat_reply` to emit structured envelope

**Files:**
- Modify: `control-plane/app/mcp_gateway.py` (`tool_chat_reply` around line 914)
- Modify: `control-plane/app/openrouter_client.py` (if `chat_reply` needs raw-text mode; inspect first)
- Test: `control-plane/app/tests/test_tool_chat_reply_contract.py` (add integration test)

- [ ] **Step 1: Inspect openrouter_client.chat_reply signature**

Run: `grep -n "def chat_reply" control-plane/app/openrouter_client.py`

Expected: a signature returning `str`. We will call it as-is; we only change the caller's interpretation of that string.

- [ ] **Step 2: Write the integration test**

Append to `control-plane/app/tests/test_tool_chat_reply_contract.py`:

```python
import asyncio
from unittest.mock import AsyncMock, patch

from app.mcp_gateway import McpGateway


class TestToolChatReplyOutput(unittest.TestCase):
    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def test_openrouter_reply_parsed_into_envelope(self):
        gateway = McpGateway.__new__(McpGateway)
        gateway.openrouter = type("O", (), {"configured": True})()
        async def fake_chat_reply(messages, model, temperature, max_tokens):
            return '{"reply": "hola", "suggested_actions": [{"title": "X", "action_type": "odoo_read", "policy_key": "p", "payload": {}}]}'
        gateway.openrouter.chat_reply = fake_chat_reply

        result = self._run(gateway.tool_chat_reply({
            "messages": [{"role": "user", "content": "hi"}],
        }))

        self.assertEqual(result["kind"], "completed")
        self.assertEqual(result["reply"], "hola")
        self.assertEqual(len(result["suggested_actions"]), 1)
        self.assertEqual(result["suggested_actions"][0]["title"], "X")

    def test_openrouter_plain_text_reply_emits_empty_actions(self):
        gateway = McpGateway.__new__(McpGateway)
        gateway.openrouter = type("O", (), {"configured": True})()
        async def fake_chat_reply(messages, model, temperature, max_tokens):
            return "just a text reply"
        gateway.openrouter.chat_reply = fake_chat_reply

        result = self._run(gateway.tool_chat_reply({
            "messages": [{"role": "user", "content": "hi"}],
        }))

        self.assertEqual(result["reply"], "just a text reply")
        self.assertEqual(result["suggested_actions"], [])

    def test_fallback_mode_emits_empty_actions(self):
        gateway = McpGateway.__new__(McpGateway)
        gateway.openrouter = type("O", (), {"configured": False})()

        result = self._run(gateway.tool_chat_reply({
            "messages": [{"role": "user", "content": "hello"}],
        }))

        self.assertEqual(result["suggested_actions"], [])
        self.assertIn("hello", result["reply"])
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd control-plane && python -m unittest discover app/tests -v`

Expected: the three new tests fail — `tool_chat_reply` currently returns `{"reply": "...", ...}` without `suggested_actions` and without going through `_parse_llm_envelope`.

- [ ] **Step 4: Modify `tool_chat_reply` to use the envelope parser**

In `control-plane/app/mcp_gateway.py`, replace the body of `tool_chat_reply` (starts around line 914). The new body:

```python
    async def tool_chat_reply(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw_messages = arguments.get("messages") or []
        if not isinstance(raw_messages, list) or not raw_messages:
            return {"kind": "rejected", "summary": "chat.reply requires messages."}

        messages: list[dict[str, str]] = []
        for item in raw_messages:
            if not isinstance(item, dict):
                continue
            role = item.get("role") or "user"
            if role not in {"system", "user", "assistant"}:
                role = "user"
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            messages.append({"role": role, "content": content})

        if not messages:
            return {"kind": "rejected", "summary": "chat.reply requires non-empty messages."}

        policy_context = arguments.get("policy_context") or {}
        messages = self._inject_policy_system_prompt(messages, policy_context)

        chosen_model = (arguments.get("model") or settings.openrouter_model).strip()
        temperature = float(arguments.get("temperature", 0.5))
        max_tokens = int(arguments.get("max_tokens", 800))

        if self.openrouter.configured:
            models_to_try = [chosen_model]
            if settings.openrouter_fallback_model and settings.openrouter_fallback_model not in models_to_try:
                models_to_try.append(settings.openrouter_fallback_model)

            last_error: str | None = None
            for model_name in models_to_try:
                try:
                    raw_reply = await self.openrouter.chat_reply(
                        messages,
                        model=model_name,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    reply, actions = _parse_llm_envelope(raw_reply)
                    return {
                        "kind": "completed",
                        "summary": "Generated a chat reply.",
                        "reply": reply,
                        "suggested_actions": actions,
                        "model": model_name,
                        "provider": "openrouter",
                    }
                except (OpenRouterError, httpx.HTTPError, ValueError) as exc:
                    last_error = str(exc)
                    log.warning("OpenRouter chat reply failed for %s: %s", model_name, exc)

            if last_error:
                log.warning("OpenRouter chat reply fell back to local output: %s", last_error)

        last_user_message = next((message["content"] for message in reversed(messages) if message["role"] == "user"), "")
        fallback_reply = (
            "OpenClaw chat is running in local fallback mode. "
            f"I received: {last_user_message or 'an empty message'}."
        )
        return {
            "kind": "completed",
            "summary": "Generated a local fallback chat reply.",
            "reply": fallback_reply,
            "suggested_actions": [],
            "provider": "local",
            "model": None,
        }
```

Add the helper method on the `McpGateway` class (near other helper methods; exact placement doesn't matter functionally):

```python
    def _inject_policy_system_prompt(
        self,
        messages: list[dict[str, str]],
        policy_context: dict[str, Any],
    ) -> list[dict[str, str]]:
        available = policy_context.get("available_policies") or []
        if not available:
            return messages
        policies_json = json.dumps(available, ensure_ascii=False)
        instruction = (
            "Respond as a single JSON object with keys `reply` (string) and "
            "`suggested_actions` (array). `reply` is the user-facing text. "
            "Each suggested action must have `title`, `rationale`, `action_type`, "
            "`policy_key`, and `payload` (object). Only use `policy_key` values "
            f"from this list: {policies_json}. When unsure, return an empty "
            "`suggested_actions` array. Never include text outside the JSON."
        )
        extended = list(messages)
        extended.insert(0, {"role": "system", "content": instruction})
        return extended
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd control-plane && python -m unittest discover app/tests -v`

Expected: all tests PASS (7 from Task 3 + 3 new).

- [ ] **Step 6: Commit**

```bash
git add control-plane/app/mcp_gateway.py \
        control-plane/app/tests/test_tool_chat_reply_contract.py
git commit -m "feat(control-plane): return suggested_actions envelope from tool_chat_reply"
```

---

### Task 5: Update gateway client `chat_reply` to return structured dict

**Files:**
- Modify: `addons_custom/openclaw/models/gateway_client.py`

- [ ] **Step 1: Write the failing test**

Append to `addons_custom/openclaw/tests/test_openclaw_chat_suggestions.py`:

```python
from unittest.mock import patch

from odoo.addons.openclaw.models.gateway_client import OpenClawGatewayClient


@tagged("post_install", "-at_install")
class TestGatewayClientChatReply(TransactionCase):
    def test_chat_reply_returns_reply_and_actions(self):
        client = OpenClawGatewayClient(base_url="http://fake")
        fake_result = {
            "content": [{
                "type": "text",
                "text": '{"kind": "completed", "reply": "hola", "suggested_actions": [{"title": "X"}], "provider": "openrouter"}',
            }],
        }
        with patch.object(client, "_rpc", return_value=fake_result):
            out = client.chat_reply([{"role": "user", "content": "hi"}])
        self.assertIsInstance(out, dict)
        self.assertEqual(out["reply"], "hola")
        self.assertEqual(out["suggested_actions"], [{"title": "X"}])
        self.assertEqual(out["provider"], "openrouter")

    def test_chat_reply_empty_actions_default(self):
        client = OpenClawGatewayClient(base_url="http://fake")
        fake_result = {
            "content": [{
                "type": "text",
                "text": '{"kind": "completed", "reply": "hola"}',
            }],
        }
        with patch.object(client, "_rpc", return_value=fake_result):
            out = client.chat_reply([{"role": "user", "content": "hi"}])
        self.assertEqual(out["reply"], "hola")
        self.assertEqual(out["suggested_actions"], [])
```

- [ ] **Step 2: Run to verify failure**

Run: `docker compose exec odoo odoo --test-tags openclaw -d odoo -u openclaw --stop-after-init`

Expected: fails — current `chat_reply` returns `str`, not `dict`.

- [ ] **Step 3: Update `chat_reply` signature and body**

In `addons_custom/openclaw/models/gateway_client.py`, replace the `chat_reply` method:

```python
    def chat_reply(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float = 0.5,
        max_tokens: int = 800,
        policy_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        arguments: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if model:
            arguments["model"] = model
        if policy_context:
            arguments["policy_context"] = policy_context
        result = self._rpc(
            "tools/call",
            {"name": "chat.reply", "arguments": arguments},
        )
        decoded = self._decode_result(result)
        if isinstance(decoded, dict):
            reply = decoded.get("reply") or decoded.get("summary") or ""
            raw_actions = decoded.get("suggested_actions")
            actions = raw_actions if isinstance(raw_actions, list) else []
            return {
                "reply": str(reply),
                "suggested_actions": actions,
                "provider": decoded.get("provider") or "",
                "model": decoded.get("model"),
                "kind": decoded.get("kind") or "completed",
            }
        return {
            "reply": str(decoded) if decoded is not None else "",
            "suggested_actions": [],
            "provider": "",
            "model": None,
            "kind": "completed",
        }
```

- [ ] **Step 4: Run to verify tests pass**

Run: `docker compose exec odoo odoo --test-tags openclaw -d odoo -u openclaw --stop-after-init`

Expected: PASS (the two new tests + prior).

- [ ] **Step 5: Commit**

```bash
git add addons_custom/openclaw/models/gateway_client.py \
        addons_custom/openclaw/tests/test_openclaw_chat_suggestions.py
git commit -m "refactor(openclaw): chat_reply returns structured envelope dict"
```

---

### Task 6: `_build_policy_context` and `_generate_reply` updated to return envelope

**Files:**
- Modify: `addons_custom/openclaw/models/openclaw_chat.py`

- [ ] **Step 1: Write the failing tests**

Append to `test_openclaw_chat_suggestions.py`:

```python
@tagged("post_install", "-at_install")
class TestBuildPolicyContext(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user_group = self.env.ref("openclaw.group_openclaw_user")
        self.admin_group = self.env.ref("openclaw.group_openclaw_admin")
        self.user = self.env["res.users"].create({
            "name": "Chat User",
            "login": "chatuser@example.com",
            "groups_id": [(6, 0, [self.user_group.id])],
        })
        self.policy_user_accessible = self.env["openclaw.policy"].create({
            "name": "User Policy",
            "key": "user_policy",
            "sequence": 10,
            "allow_read_db": True,
            "group_ids": [(6, 0, [self.user_group.id])],
        })
        self.policy_admin_only = self.env["openclaw.policy"].create({
            "name": "Admin Policy",
            "key": "admin_policy",
            "sequence": 20,
            "allow_write_db": True,
            "group_ids": [(6, 0, [self.admin_group.id])],
        })

    def test_policy_context_filters_to_accessible_policies(self):
        session = self.env["openclaw.chat.session"].with_user(self.user).create({
            "name": "s",
            "user_id": self.user.id,
        })
        context = session._build_policy_context()
        keys = [p["key"] for p in context["available_policies"]]
        self.assertIn("user_policy", keys)
        self.assertNotIn("admin_policy", keys)

    def test_policy_context_allowed_actions_derived_from_policy_flags(self):
        session = self.env["openclaw.chat.session"].with_user(self.user).create({
            "name": "s",
            "user_id": self.user.id,
        })
        context = session._build_policy_context()
        entry = next(p for p in context["available_policies"] if p["key"] == "user_policy")
        self.assertIn("db_read", entry["allowed_actions"])
        self.assertNotIn("db_write", entry["allowed_actions"])
```

- [ ] **Step 2: Run to verify failure**

Run: `docker compose exec odoo odoo --test-tags openclaw -d odoo -u openclaw --stop-after-init`

Expected: `AttributeError: 'openclaw.chat.session' has no method '_build_policy_context'`.

- [ ] **Step 3: Implement `_build_policy_context` and update `_generate_reply`**

In `addons_custom/openclaw/models/openclaw_chat.py`, add to `OpenClawChatSession`:

```python
    _POLICY_FLAG_TO_ACTION = {
        'allow_read_db': 'db_read',
        'allow_write_db': 'db_write',
        'allow_read_odoo': 'odoo_read',
        'allow_write_odoo': 'odoo_write',
        'allow_read_docs': 'docs_read',
        'allow_write_docs': 'docs_write',
        'allow_web_search': 'web_search',
        'allow_code_generation': 'code_generation',
        'allow_shell_actions': 'shell_action',
    }

    def _build_policy_context(self) -> dict[str, Any]:
        self.ensure_one()
        user = self.user_id or self.env.user
        policies = self.env['openclaw.policy'].sudo().search([('active', '=', True)])
        user_group_ids = set(user.groups_id.ids)
        entries: list[dict[str, Any]] = []
        for policy in policies:
            policy_groups = set(policy.group_ids.ids)
            if policy_groups and not (policy_groups & user_group_ids):
                continue
            allowed_actions = [
                action_name
                for flag, action_name in self._POLICY_FLAG_TO_ACTION.items()
                if getattr(policy, flag, False)
            ]
            entries.append({
                'key': policy.key,
                'name': policy.name,
                'allowed_actions': allowed_actions,
            })
        return {
            'available_policies': entries,
            'user_locale': user.lang or 'en_US',
        }
```

Replace `_generate_reply` to return a dict (not a string):

```python
    def _generate_reply(self, user_content: str) -> dict[str, Any]:
        self.ensure_one()
        try:
            response = self._gateway_client().chat_reply(
                self._chat_messages_for_gateway() + [{'role': 'user', 'content': user_content}],
                policy_context=self._build_policy_context(),
            )
        except OpenClawGatewayError as exc:
            return {
                'reply': _('OpenClaw could not contact the gateway: %s') % exc,
                'suggested_actions': [],
            }

        if not isinstance(response, dict):
            return {
                'reply': _('OpenClaw did not receive a usable reply.'),
                'suggested_actions': [],
            }
        reply_text = response.get('reply') or _('OpenClaw did not receive a usable reply.')
        actions = response.get('suggested_actions') or []
        return {'reply': str(reply_text), 'suggested_actions': actions}
```

Note that `_generate_reply` now uses `self._gateway_client().chat_reply(...)` (new-style). Remove the old `call_tool('chat.reply', ...)` path — replaced by the enriched `chat_reply` method in the client.

Also import `OpenClawGatewayError` properly if not already:

```python
from .gateway_client import OpenClawGatewayClient, OpenClawGatewayError
```

(already present at line 8).

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose exec odoo odoo --test-tags openclaw -d odoo -u openclaw --stop-after-init`

Expected: both new tests PASS.

- [ ] **Step 5: Commit**

```bash
git add addons_custom/openclaw/models/openclaw_chat.py \
        addons_custom/openclaw/tests/test_openclaw_chat_suggestions.py
git commit -m "feat(openclaw): build policy_context and thread suggestions through _generate_reply"
```

---

### Task 7: `_materialize_suggestions` with validation, truncation, forced approval

**Files:**
- Modify: `addons_custom/openclaw/models/openclaw_chat.py`

- [ ] **Step 1: Write the failing tests**

Append to `test_openclaw_chat_suggestions.py`:

```python
@tagged("post_install", "-at_install")
class TestMaterializeSuggestions(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user_group = self.env.ref("openclaw.group_openclaw_user")
        self.policy = self.env["openclaw.policy"].create({
            "name": "User Policy",
            "key": "user_policy",
            "sequence": 10,
            "allow_read_db": True,
            "allow_write_db": True,
            "require_human_approval": False,
            "group_ids": [(6, 0, [self.user_group.id])],
        })
        self.user = self.env["res.users"].create({
            "name": "Chat User",
            "login": "m@example.com",
            "groups_id": [(6, 0, [self.user_group.id])],
        })
        self.session = self.env["openclaw.chat.session"].with_user(self.user).create({
            "name": "s",
            "user_id": self.user.id,
        })
        self.message = self.env["openclaw.chat.message"].with_user(self.user).create({
            "session_id": self.session.id,
            "role": "assistant",
            "content": "ok",
        })

    def _suggestion(self, **overrides):
        base = {
            "title": "A",
            "rationale": "r",
            "action_type": "db_read",
            "policy_key": "user_policy",
            "payload": {"sql": "select 1"},
        }
        base.update(overrides)
        return base

    def test_valid_suggestion_creates_draft_with_forced_approval(self):
        created = self.session.with_user(self.user)._materialize_suggestions(
            self.message, [self._suggestion()],
        )
        self.assertEqual(len(created), 1)
        request = created[0]
        self.assertEqual(request.origin, "chat_suggestion")
        self.assertEqual(request.state, "draft")
        self.assertTrue(request.approval_required)
        self.assertEqual(request.session_id, self.session)
        self.assertEqual(request.message_id, self.message)
        self.assertEqual(request.policy_id, self.policy)
        self.assertEqual(request.rationale, "r")

    def test_unknown_policy_key_creates_blocked_draft(self):
        created = self.session.with_user(self.user)._materialize_suggestions(
            self.message, [self._suggestion(policy_key="nope")],
        )
        self.assertEqual(len(created), 1)
        self.assertFalse(created[0].policy_id)
        self.assertIn("nope", created[0].decision_note)

    def test_non_dict_payload_is_blocked(self):
        created = self.session.with_user(self.user)._materialize_suggestions(
            self.message, [self._suggestion(payload=["not", "a", "dict"])],
        )
        self.assertEqual(len(created), 1)
        self.assertFalse(created[0].policy_id)
        self.assertIn("payload", created[0].decision_note.lower())

    def test_invalid_action_type_is_blocked(self):
        created = self.session.with_user(self.user)._materialize_suggestions(
            self.message, [self._suggestion(action_type="not_a_real_action")],
        )
        self.assertEqual(len(created), 1)
        self.assertFalse(created[0].policy_id)
        self.assertIn("action_type", created[0].decision_note.lower())

    def test_truncation_to_five(self):
        suggestions = [self._suggestion(title=f"A{i}") for i in range(7)]
        created = self.session.with_user(self.user)._materialize_suggestions(
            self.message, suggestions,
        )
        self.assertEqual(len(created), 5)
```

- [ ] **Step 2: Run to verify failure**

Expected: `AttributeError: '_materialize_suggestions'`.

- [ ] **Step 3: Implement `_materialize_suggestions`**

Add to `OpenClawChatSession` in `openclaw_chat.py`:

```python
    _CHAT_SUGGESTION_LIMIT = 5
    _VALID_ACTION_TYPES = {
        'db_read', 'db_write', 'odoo_read', 'odoo_write',
        'docs_read', 'docs_write', 'web_search',
        'code_generation', 'shell_action', 'custom',
    }

    def _materialize_suggestions(
        self,
        message,
        suggestions: list[dict[str, Any]],
    ) -> 'models.Model':
        self.ensure_one()
        if not suggestions:
            return self.env['openclaw.request']
        Request = self.env['openclaw.request']
        try:
            Request.check_access_rights('create')
        except AccessError:
            _logger.info(
                "Skipped %s chat suggestions for non-openclaw user %s",
                len(suggestions), self.env.user.login,
            )
            return Request
        policy_context = self._build_policy_context()
        allowed_keys = {p['key']: p for p in policy_context['available_policies']}
        policies_by_key = {
            p.key: p for p in self.env['openclaw.policy'].sudo().search([
                ('key', 'in', list(allowed_keys.keys())),
                ('active', '=', True),
            ])
        }
        if len(suggestions) > self._CHAT_SUGGESTION_LIMIT:
            _logger.warning(
                "Chat session %s received %s suggestions; truncating to %s",
                self.id, len(suggestions), self._CHAT_SUGGESTION_LIMIT,
            )
            suggestions = suggestions[: self._CHAT_SUGGESTION_LIMIT]

        created = Request.browse()
        for item in suggestions:
            if not isinstance(item, dict):
                continue
            title = str(item.get('title') or 'Chat suggestion').strip() or 'Chat suggestion'
            rationale = str(item.get('rationale') or '').strip()
            action_type = item.get('action_type')
            payload = item.get('payload')
            policy_key = item.get('policy_key')
            target_model = (item.get('target_model') or '').strip() or False
            target_ref = (item.get('target_ref') or '').strip() or False
            custom_tool_name = (item.get('custom_tool_name') or '').strip() or False

            decision_notes: list[str] = []
            if action_type not in self._VALID_ACTION_TYPES:
                decision_notes.append(f"Invalid action_type: {action_type!r}")
            if not isinstance(payload, dict):
                decision_notes.append("payload must be a JSON object")
            policy = policies_by_key.get(policy_key) if policy_key else None
            if policy is None:
                decision_notes.append(f"policy_key {policy_key!r} not found")

            vals: dict[str, Any] = {
                'name': title[:255],
                'instruction': rationale or title,
                'requested_by': self.env.user.id,
                'session_id': self.id,
                'message_id': message.id,
                'origin': 'chat_suggestion',
                'rationale': rationale,
                'target_model': target_model,
                'target_ref': target_ref,
                'custom_tool_name': custom_tool_name,
                'approval_required': True,
            }
            if not decision_notes:
                vals['action_type'] = action_type
                vals['policy_id'] = policy.id
                vals['payload_json'] = json.dumps(payload, ensure_ascii=False, indent=2)
            else:
                vals['decision_note'] = '; '.join(decision_notes)
                vals['action_type'] = 'custom'

            created |= Request.create(vals)
        return created
```

Add at the top of the file:

```python
import json
import logging

_logger = logging.getLogger(__name__)

from odoo.exceptions import AccessError
```

(Merge with existing imports — `json` and `AccessError` are new; `_logger` is new.)

Also note: the constraint `_check_policy_required_for_submit` must not fire on create with `state='draft' + policy_id=False`. Reread the constraint: it only raises when `state != 'draft'`. Drafts without policy are allowed. Good.

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose exec odoo odoo --test-tags openclaw -d odoo -u openclaw --stop-after-init`

Expected: all 5 new tests PASS.

- [ ] **Step 5: Commit**

```bash
git add addons_custom/openclaw/models/openclaw_chat.py \
        addons_custom/openclaw/tests/test_openclaw_chat_suggestions.py
git commit -m "feat(openclaw): materialize chat suggestions with validation and truncation"
```

---

### Task 8: `rpc_send_message` persists suggestions and returns them

**Files:**
- Modify: `addons_custom/openclaw/models/openclaw_chat.py`

- [ ] **Step 1: Write the failing test**

Append to `test_openclaw_chat_suggestions.py`:

```python
@tagged("post_install", "-at_install")
class TestRpcSendMessageWithSuggestions(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user_group = self.env.ref("openclaw.group_openclaw_user")
        self.policy = self.env["openclaw.policy"].create({
            "name": "Policy",
            "key": "p",
            "sequence": 10,
            "allow_read_db": True,
            "group_ids": [(6, 0, [self.user_group.id])],
        })
        self.user = self.env["res.users"].create({
            "name": "U",
            "login": "u@example.com",
            "groups_id": [(6, 0, [self.user_group.id])],
        })
        self.env["ir.config_parameter"].sudo().set_param(
            "openclaw.gateway_url", "http://fake",
        )
        self.session = self.env["openclaw.chat.session"].with_user(self.user).create({
            "name": "s",
            "user_id": self.user.id,
        })

    def test_send_message_persists_and_returns_requests(self):
        fake_envelope = {
            "reply": "Te propongo leer la DB",
            "suggested_actions": [{
                "title": "Leer",
                "rationale": "el user preguntó",
                "action_type": "db_read",
                "policy_key": "p",
                "payload": {"sql": "select 1"},
            }],
        }
        Session = self.env["openclaw.chat.session"].with_user(self.user)
        with patch.object(Session.__class__, "_generate_reply", return_value=fake_envelope):
            result = Session.rpc_send_message(self.session.id, "hola")
        assistant = result["assistant_message"]
        self.assertEqual(len(assistant["requests"]), 1)
        self.assertEqual(assistant["requests"][0]["policy_key"], "p")
        self.assertEqual(assistant["requests"][0]["state"], "draft")
```

- [ ] **Step 2: Run to verify failure**

Expected: `result["assistant_message"]["requests"]` is missing or empty (current `rpc_send_message` doesn't call `_materialize_suggestions`).

- [ ] **Step 3: Update `rpc_send_message`**

In `openclaw_chat.py`, find `rpc_send_message` and update the assistant-reply section. The new body:

```python
    @api.model
    def rpc_send_message(self, session_id: int, content: str):
        session = self.browse(session_id).exists()
        if not session:
            raise ValidationError(_('Chat session not found.'))

        message_content = (content or '').strip()
        if not message_content:
            raise ValidationError(_('Message content is required.'))

        user_message = self.env['openclaw.chat.message'].create(
            {
                'session_id': session.id,
                'role': 'user',
                'user_id': self.env.user.id,
                'content': message_content,
            }
        )

        session_values: dict[str, Any] = {
            'last_message_at': fields.Datetime.now(),
            'last_message_preview': self._shorten_text(message_content),
        }
        if session.name == 'New conversation':
            session_values['name'] = self._shorten_text(message_content, limit=60) or 'New conversation'
        session.write(session_values)

        envelope = session._generate_reply(message_content)
        assistant_reply = envelope.get('reply') or _('OpenClaw did not receive a usable reply.')
        suggested_actions = envelope.get('suggested_actions') or []

        assistant_message = self.env['openclaw.chat.message'].create(
            {
                'session_id': session.id,
                'role': 'assistant',
                'content': assistant_reply,
            }
        )
        session._materialize_suggestions(assistant_message, suggested_actions)

        session.write(
            {
                'last_message_at': fields.Datetime.now(),
                'last_message_preview': self._shorten_text(assistant_reply),
            }
        )

        return {
            'session': session._session_payload(include_messages=True),
            'user_message': self._message_payload(user_message),
            'assistant_message': self._message_payload(assistant_message),
        }
```

- [ ] **Step 4: Run tests**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add addons_custom/openclaw/models/openclaw_chat.py \
        addons_custom/openclaw/tests/test_openclaw_chat_suggestions.py
git commit -m "feat(openclaw): rpc_send_message materializes chat suggestions"
```

---

### Task 9: RPCs for approve / reject / get_request_detail

**Files:**
- Modify: `addons_custom/openclaw/models/openclaw_chat.py`
- Test: `addons_custom/openclaw/tests/test_openclaw_chat_approval.py`

- [ ] **Step 1: Write the failing tests**

```python
# addons_custom/openclaw/tests/test_openclaw_chat_approval.py
import json
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestChatApprovalRpcs(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user_group = self.env.ref("openclaw.group_openclaw_user")
        self.policy = self.env["openclaw.policy"].create({
            "name": "P",
            "key": "p",
            "sequence": 10,
            "allow_read_db": True,
            "group_ids": [(6, 0, [self.user_group.id])],
        })
        self.user = self.env["res.users"].create({
            "name": "U",
            "login": "u2@example.com",
            "groups_id": [(6, 0, [self.user_group.id])],
        })
        self.session = self.env["openclaw.chat.session"].with_user(self.user).create({
            "name": "s", "user_id": self.user.id,
        })
        self.message = self.env["openclaw.chat.message"].with_user(self.user).create({
            "session_id": self.session.id, "role": "assistant", "content": "ok",
        })
        self.request = self.env["openclaw.request"].with_user(self.user).create({
            "name": "r",
            "instruction": "i",
            "policy_id": self.policy.id,
            "session_id": self.session.id,
            "message_id": self.message.id,
            "origin": "chat_suggestion",
            "action_type": "db_read",
            "payload_json": json.dumps({"sql": "select 1"}),
            "approval_required": True,
        })

    def test_rpc_approve_request_runs_full_pipeline(self):
        Session = self.env["openclaw.chat.session"].with_user(self.user)
        with patch(
            "odoo.addons.openclaw.models.openclaw_request.OpenClawRequest._execute_one",
            autospec=True,
        ) as exec_mock:
            def side_effect(request_self):
                request_self.write({"state": "executed", "result_summary": "done"})
            exec_mock.side_effect = side_effect
            payload = Session.rpc_approve_request(self.request.id)
        self.assertEqual(payload["state"], "executed")
        self.assertEqual(self.request.state, "executed")

    def test_rpc_approve_blocked_request_raises(self):
        blocked = self.env["openclaw.request"].with_user(self.user).create({
            "name": "b",
            "instruction": "b",
            "session_id": self.session.id,
            "message_id": self.message.id,
            "origin": "chat_suggestion",
            "decision_note": "no policy",
            "action_type": "custom",
        })
        Session = self.env["openclaw.chat.session"].with_user(self.user)
        with self.assertRaises(ValidationError):
            Session.rpc_approve_request(blocked.id)

    def test_rpc_reject_request_transitions_to_rejected(self):
        Session = self.env["openclaw.chat.session"].with_user(self.user)
        # rejection needs state=pending or approved. Submit first.
        self.request.action_submit()
        payload = Session.rpc_reject_request(self.request.id)
        self.assertEqual(payload["state"], "rejected")

    def test_rpc_get_request_detail_exposes_json_fields(self):
        Session = self.env["openclaw.chat.session"].with_user(self.user)
        detail = Session.rpc_get_request_detail(self.request.id)
        self.assertEqual(detail["id"], self.request.id)
        self.assertIn("payload_json", detail)
        self.assertIn("policy_snapshot_json", detail)

    def test_rpc_approve_failure_sets_failed(self):
        Session = self.env["openclaw.chat.session"].with_user(self.user)
        with patch(
            "odoo.addons.openclaw.models.openclaw_request.OpenClawRequest._execute_one",
            autospec=True,
        ) as exec_mock:
            exec_mock.side_effect = RuntimeError("gateway down")
            payload = Session.rpc_approve_request(self.request.id)
        self.assertEqual(payload["state"], "failed")
        self.assertIn("gateway down", payload["error_message"])
```

Register in `__init__.py`:

```python
from . import test_openclaw_chat_approval
```

- [ ] **Step 2: Run to verify failure**

Expected: `AttributeError: 'rpc_approve_request'`.

- [ ] **Step 3: Implement the three RPCs**

Add to `OpenClawChatSession` in `openclaw_chat.py`:

```python
    @api.model
    def rpc_approve_request(self, request_id: int):
        request = self.env['openclaw.request'].browse(request_id).exists()
        if not request:
            raise ValidationError(_('Request not found.'))
        if not request.policy_id:
            raise ValidationError(_('This request is blocked and cannot be approved.'))

        if request.state == 'draft':
            request.action_submit()
        if request.state == 'pending':
            request.action_approve()
        if request.state != 'approved':
            raise ValidationError(_('Request could not reach approved state.'))

        try:
            request.action_execute()
        except Exception as exc:
            request.write({
                'state': 'failed',
                'failed_at': fields.Datetime.now(),
                'error_message': str(exc),
            })
            _logger.warning(
                "Chat approval execution failed for request %s: %s",
                request.id, exc,
            )

        return request._chat_card_payload()

    @api.model
    def rpc_reject_request(self, request_id: int):
        request = self.env['openclaw.request'].browse(request_id).exists()
        if not request:
            raise ValidationError(_('Request not found.'))
        if request.state == 'draft':
            request.write({'state': 'rejected'})
        elif request.state in ('pending', 'approved'):
            request.action_reject()
        else:
            raise ValidationError(_('Request is not in a rejectable state.'))
        return request._chat_card_payload()

    @api.model
    def rpc_get_request_detail(self, request_id: int):
        request = self.env['openclaw.request'].browse(request_id).exists()
        if not request:
            raise ValidationError(_('Request not found.'))
        payload = request._chat_card_payload()
        payload.update({
            'instruction': request.instruction or '',
            'payload_json': request.payload_json or '',
            'policy_snapshot_json': request.policy_snapshot_json or '',
            'gateway_response_json': request.gateway_response_json or '',
            'requested_at': request.requested_at.isoformat() if request.requested_at else False,
            'submitted_at': request.submitted_at.isoformat() if request.submitted_at else False,
            'approved_at': request.approved_at.isoformat() if request.approved_at else False,
            'executed_at': request.executed_at.isoformat() if request.executed_at else False,
            'failed_at': request.failed_at.isoformat() if request.failed_at else False,
            'approved_by': request.approved_by.display_name if request.approved_by else '',
        })
        return payload
```

Note: `action_reject` currently only allows `pending` or `approved`. `rpc_reject_request` handles `draft` itself by writing state directly, since draft rejection is legitimate for chat-blocked cards and for the user ignoring a suggestion.

- [ ] **Step 4: Run tests**

Expected: PASS (5 new tests).

- [ ] **Step 5: Commit**

```bash
git add addons_custom/openclaw/models/openclaw_chat.py \
        addons_custom/openclaw/tests/__init__.py \
        addons_custom/openclaw/tests/test_openclaw_chat_approval.py
git commit -m "feat(openclaw): add rpc_approve_request, rpc_reject_request, rpc_get_request_detail"
```

---

### Task 10: SCSS — full replacement with light admin tokens

**Files:**
- Rewrite: `addons_custom/openclaw/static/src/scss/openclaw_chat.scss`

No automated test for this. The whole SCSS file is replaced; the visual check happens in Task 13 (smoke test).

- [ ] **Step 1: Replace the file contents**

Overwrite `addons_custom/openclaw/static/src/scss/openclaw_chat.scss` with:

```scss
.o_openclaw_chat {
    --openclaw-font: "Inter", ui-sans-serif, system-ui, -apple-system,
                     "Segoe UI", Roboto, sans-serif;
    --openclaw-mono: "JetBrains Mono", ui-monospace, SFMono-Regular,
                     Menlo, monospace;

    --openclaw-bg: #f7f8fa;
    --openclaw-bg-gradient:
        radial-gradient(1200px 600px at 10% -10%, #eef2f7 0%, transparent 60%),
        radial-gradient(900px 500px at 90% 0%, #e8eef7 0%, transparent 55%),
        linear-gradient(180deg, #f7f8fa 0%, #eef1f6 100%);

    --openclaw-surface: rgba(255, 255, 255, 0.82);
    --openclaw-surface-strong: rgba(255, 255, 255, 0.95);
    --openclaw-border: rgba(15, 23, 42, 0.08);
    --openclaw-border-strong: rgba(15, 23, 42, 0.14);

    --openclaw-text: #0f172a;
    --openclaw-text-muted: #475569;
    --openclaw-text-subtle: #64748b;

    --openclaw-accent: #2563eb;
    --openclaw-accent-soft: rgba(37, 99, 235, 0.08);
    --openclaw-accent-strong: #1d4ed8;

    --openclaw-success: #10b981;
    --openclaw-success-soft: rgba(16, 185, 129, 0.1);
    --openclaw-warning: #f59e0b;
    --openclaw-warning-soft: rgba(245, 158, 11, 0.12);
    --openclaw-danger: #ef4444;
    --openclaw-danger-soft: rgba(239, 68, 68, 0.1);

    --openclaw-radius: 14px;
    --openclaw-radius-sm: 10px;
    --openclaw-radius-xs: 6px;

    --openclaw-shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04),
                         0 1px 3px rgba(15, 23, 42, 0.04);
    --openclaw-shadow: 0 1px 2px rgba(15, 23, 42, 0.04),
                      0 8px 24px rgba(15, 23, 42, 0.06);

    font-family: var(--openclaw-font);
    color: var(--openclaw-text);
    background: var(--openclaw-bg);
    background-image: var(--openclaw-bg-gradient);
    display: grid;
    grid-template-columns: 260px 1fr;
    height: 100%;
    min-height: calc(100vh - 4rem);
    gap: 0;
    letter-spacing: -0.005em;
    position: relative;
}

.o_openclaw_chat_sidebar {
    background: var(--openclaw-surface);
    border-right: 1px solid var(--openclaw-border);
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    overflow: hidden;
}

.o_openclaw_chat_sidebar_header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
}

.o_openclaw_chat_sidebar_header h1 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--openclaw-text);
}

.o_openclaw_chat_kicker {
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--openclaw-text-subtle);
    font-weight: 600;
}

.o_openclaw_chat_new {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 6px 10px;
    border: 1px solid var(--openclaw-border-strong);
    border-radius: var(--openclaw-radius-sm);
    background: var(--openclaw-surface-strong);
    color: var(--openclaw-text);
    font-size: 0.82rem;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.12s ease, border-color 0.12s ease;
}

.o_openclaw_chat_new:hover {
    background: var(--openclaw-accent-soft);
    border-color: var(--openclaw-accent);
    color: var(--openclaw-accent);
}

.o_openclaw_chat_session_list {
    display: flex;
    flex-direction: column;
    gap: 2px;
    overflow-y: auto;
    padding-right: 2px;
}

.o_openclaw_chat_session_item {
    width: 100%;
    text-align: left;
    padding: 8px 10px;
    border: none;
    background: transparent;
    border-radius: var(--openclaw-radius-sm);
    color: var(--openclaw-text-muted);
    font-family: inherit;
    cursor: pointer;
    transition: background 0.12s ease, color 0.12s ease;
}

.o_openclaw_chat_session_item:hover {
    background: var(--openclaw-accent-soft);
    color: var(--openclaw-accent);
}

.o_openclaw_chat_session_item.is-active {
    background: var(--openclaw-accent);
    color: #fff;
}

.o_openclaw_chat_session_name {
    font-weight: 500;
    font-size: 0.9rem;
    line-height: 1.3;
}

.o_openclaw_chat_session_preview {
    font-size: 0.78rem;
    opacity: 0.75;
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.o_openclaw_chat_main {
    display: grid;
    grid-template-rows: auto 1fr auto;
    min-height: 0;
    min-width: 0;
    background: transparent;
}

.o_openclaw_chat_main_header {
    position: sticky;
    top: 0;
    z-index: 2;
    padding: 14px 24px;
    background: var(--openclaw-surface);
    backdrop-filter: blur(16px) saturate(160%);
    -webkit-backdrop-filter: blur(16px) saturate(160%);
    border-bottom: 1px solid var(--openclaw-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
}

.o_openclaw_chat_main_header h2 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--openclaw-text);
}

.o_openclaw_chat_status {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.82rem;
    color: var(--openclaw-text-muted);
}

.o_openclaw_chat_dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--openclaw-success);
    box-shadow: 0 0 0 3px var(--openclaw-success-soft);
}

.o_openclaw_chat_messages {
    overflow-y: auto;
    padding: 24px clamp(16px, 4vw, 48px);
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.o_openclaw_chat_message {
    display: flex;
    flex-direction: column;
    max-width: min(72ch, 100%);
}

.o_openclaw_chat_message.is-user {
    align-self: flex-end;
    align-items: flex-end;
}

.o_openclaw_chat_message.is-assistant,
.o_openclaw_chat_message.is-system {
    align-self: flex-start;
}

.o_openclaw_chat_message_meta {
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--openclaw-text-subtle);
    margin-bottom: 4px;
}

.o_openclaw_chat_bubble {
    padding: 10px 14px;
    border-radius: var(--openclaw-radius-sm);
    line-height: 1.55;
    font-size: 0.92rem;
}

.o_openclaw_chat_message.is-user .o_openclaw_chat_bubble {
    background: var(--openclaw-accent-soft);
    color: var(--openclaw-accent-strong);
}

.o_openclaw_chat_message.is-assistant .o_openclaw_chat_bubble,
.o_openclaw_chat_message.is-system .o_openclaw_chat_bubble {
    background: var(--openclaw-surface);
    border: 1px solid var(--openclaw-border);
    color: var(--openclaw-text);
}

.o_openclaw_chat_message_content {
    white-space: pre-wrap;
}

.o_openclaw_chat_cards {
    margin-top: 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.o_openclaw_action_card {
    background: var(--openclaw-surface-strong);
    border: 1px solid var(--openclaw-border-strong);
    border-radius: var(--openclaw-radius-sm);
    padding: 12px 14px;
    box-shadow: var(--openclaw-shadow-sm);
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.o_openclaw_action_card_head {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.o_openclaw_action_card_icon {
    font-family: var(--openclaw-mono);
    font-size: 0.9rem;
    color: var(--openclaw-text-muted);
}

.o_openclaw_action_card_title {
    font-weight: 600;
    font-size: 0.9rem;
    color: var(--openclaw-text);
    flex: 1;
    min-width: 0;
}

.o_openclaw_action_card_chip {
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.o_openclaw_action_card_chip.is-draft,
.o_openclaw_action_card_chip.is-pending {
    background: var(--openclaw-warning-soft);
    color: #b45309;
}

.o_openclaw_action_card_chip.is-approved {
    background: var(--openclaw-accent-soft);
    color: var(--openclaw-accent);
}

.o_openclaw_action_card_chip.is-executed {
    background: var(--openclaw-success-soft);
    color: #047857;
}

.o_openclaw_action_card_chip.is-failed {
    background: var(--openclaw-danger-soft);
    color: #b91c1c;
}

.o_openclaw_action_card_chip.is-rejected,
.o_openclaw_action_card_chip.is-blocked {
    background: rgba(100, 116, 139, 0.15);
    color: var(--openclaw-text-subtle);
}

.o_openclaw_action_card_meta {
    font-size: 0.78rem;
    color: var(--openclaw-text-muted);
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.o_openclaw_action_card_meta code {
    font-family: var(--openclaw-mono);
    font-size: 0.75rem;
    background: var(--openclaw-accent-soft);
    color: var(--openclaw-accent-strong);
    padding: 1px 6px;
    border-radius: 4px;
}

.o_openclaw_action_card_rationale {
    font-size: 0.82rem;
    color: var(--openclaw-text-muted);
    line-height: 1.45;
}

.o_openclaw_action_card_actions {
    display: flex;
    gap: 6px;
    align-items: center;
}

.o_openclaw_action_card_actions button {
    padding: 5px 10px;
    border-radius: var(--openclaw-radius-xs);
    font-size: 0.82rem;
    font-weight: 500;
    cursor: pointer;
    border: 1px solid transparent;
    font-family: inherit;
}

.o_openclaw_action_card_actions .is-approve {
    background: var(--openclaw-accent);
    color: #fff;
}

.o_openclaw_action_card_actions .is-approve:hover {
    background: var(--openclaw-accent-strong);
}

.o_openclaw_action_card_actions .is-reject {
    background: transparent;
    color: var(--openclaw-text-muted);
}

.o_openclaw_action_card_actions .is-reject:hover {
    color: var(--openclaw-danger);
}

.o_openclaw_action_card_actions .is-detail {
    background: transparent;
    color: var(--openclaw-text-subtle);
    text-decoration: underline;
}

.o_openclaw_action_card_actions button[disabled] {
    opacity: 0.6;
    cursor: not-allowed;
}

.o_openclaw_action_card_spinner {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    border: 2px solid var(--openclaw-accent-soft);
    border-top-color: var(--openclaw-accent);
    animation: o-openclaw-spin 0.8s linear infinite;
    display: inline-block;
}

@keyframes o-openclaw-spin {
    to { transform: rotate(360deg); }
}

.o_openclaw_chat_composer {
    padding: 12px 24px;
    border-top: 1px solid var(--openclaw-border);
    background: var(--openclaw-surface-strong);
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 8px;
    align-items: end;
}

.o_openclaw_chat_input {
    resize: none;
    min-height: 40px;
    max-height: 160px;
    padding: 10px 12px;
    border-radius: var(--openclaw-radius-sm);
    border: 1px solid var(--openclaw-border);
    background: #fff;
    color: var(--openclaw-text);
    font-family: inherit;
    font-size: 0.92rem;
    line-height: 1.45;
    outline: none;
}

.o_openclaw_chat_input:focus {
    border-color: var(--openclaw-accent);
    box-shadow: 0 0 0 3px var(--openclaw-accent-soft);
}

.o_openclaw_chat_send {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: var(--openclaw-accent);
    color: #fff;
    border: none;
    font-size: 1rem;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.o_openclaw_chat_send:hover {
    background: var(--openclaw-accent-strong);
}

.o_openclaw_chat_send[disabled] {
    opacity: 0.6;
    cursor: not-allowed;
}

.o_openclaw_chat_empty_state {
    margin: auto;
    padding: 40px;
    text-align: center;
    color: var(--openclaw-text-muted);
    border: 1px dashed var(--openclaw-border-strong);
    border-radius: var(--openclaw-radius);
    max-width: 420px;
}

.o_openclaw_drawer_backdrop {
    position: absolute;
    inset: 0;
    background: rgba(15, 23, 42, 0.25);
    backdrop-filter: blur(3px);
    z-index: 3;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.15s ease;
}

.o_openclaw_drawer_backdrop.is-open {
    opacity: 1;
    pointer-events: auto;
}

.o_openclaw_drawer {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    width: 420px;
    max-width: 100%;
    background: var(--openclaw-surface-strong);
    border-left: 1px solid var(--openclaw-border);
    box-shadow: var(--openclaw-shadow);
    transform: translateX(100%);
    transition: transform 0.2s ease;
    z-index: 4;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.o_openclaw_drawer.is-open {
    transform: translateX(0);
}

.o_openclaw_drawer_header {
    padding: 16px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--openclaw-border);
}

.o_openclaw_drawer_header h3 {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
}

.o_openclaw_drawer_close {
    border: none;
    background: transparent;
    font-size: 1.1rem;
    color: var(--openclaw-text-muted);
    cursor: pointer;
}

.o_openclaw_drawer_body {
    padding: 16px 20px;
    overflow-y: auto;
    font-size: 0.85rem;
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.o_openclaw_drawer_section h4 {
    margin: 0 0 6px 0;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--openclaw-text-subtle);
    font-weight: 600;
}

.o_openclaw_drawer_section pre {
    margin: 0;
    padding: 12px;
    background: #0f172a;
    color: #e2e8f0;
    border-radius: var(--openclaw-radius-sm);
    font-family: var(--openclaw-mono);
    font-size: 0.78rem;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
}

@media (max-width: 1024px) {
    .o_openclaw_chat {
        grid-template-columns: 1fr;
    }

    .o_openclaw_chat_sidebar {
        display: none;
    }

    .o_openclaw_chat.is-sidebar-open .o_openclaw_chat_sidebar {
        display: flex;
        position: absolute;
        inset: 0 auto 0 0;
        width: 260px;
        z-index: 5;
        box-shadow: var(--openclaw-shadow);
    }
}

@media (max-width: 768px) {
    .o_openclaw_drawer {
        width: 100%;
    }

    .o_openclaw_chat_messages {
        padding: 16px;
    }

    .o_openclaw_chat_composer {
        padding: 10px 16px;
    }
}
```

- [ ] **Step 2: Commit**

```bash
git add addons_custom/openclaw/static/src/scss/openclaw_chat.scss
git commit -m "feat(openclaw): light admin chat shell with control-plane tokens"
```

Visual verification happens in Task 13.

---

### Task 11: XML templates — component tree for Sidebar, Messages, ActionCard, Composer, Drawer

**Files:**
- Rewrite: `addons_custom/openclaw/static/src/xml/openclaw_chat.xml`

- [ ] **Step 1: Replace the file contents**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">

    <t t-name="openclaw.OpenClawChatAction">
        <div class="o_openclaw_chat" t-att-class="state.sidebarOpen ? 'is-sidebar-open' : ''">
            <ChatSidebar
                sessions="state.sessions"
                activeSessionId="state.activeSession and state.activeSession.id"
                onSelect.bind="selectSession"
                onCreate.bind="createSession"
            />
            <main class="o_openclaw_chat_main">
                <ChatHeader session="state.activeSession"/>
                <ChatMessages
                    messages="state.messages"
                    loading="state.loading"
                    sending="state.sending"
                    approvingRequestId="state.approvingRequestId"
                    sessionHasApproving="state.approvingRequestId !== null"
                    onApprove.bind="approveRequest"
                    onReject.bind="rejectRequest"
                    onViewDetail.bind="openRequestDetail"
                />
                <ChatComposer
                    draft="state.draft"
                    sending="state.sending"
                    onDraftChange.bind="setDraft"
                    onSend.bind="sendMessage"
                />
            </main>
            <RequestDrawer
                t-if="state.drawerRequestId !== null"
                request="state.drawerRequest"
                loading="state.drawerLoading"
                onClose.bind="closeDrawer"
            />
        </div>
    </t>

    <t t-name="openclaw.ChatSidebar">
        <aside class="o_openclaw_chat_sidebar">
            <div class="o_openclaw_chat_sidebar_header">
                <div>
                    <div class="o_openclaw_chat_kicker">OpenClaw</div>
                    <h1>Sessions</h1>
                </div>
                <button type="button" class="o_openclaw_chat_new" t-on-click="() => props.onCreate()">+ New</button>
            </div>
            <div class="o_openclaw_chat_session_list">
                <t t-foreach="props.sessions" t-as="session" t-key="session.id">
                    <button
                        type="button"
                        class="o_openclaw_chat_session_item"
                        t-att-class="props.activeSessionId === session.id ? 'is-active' : ''"
                        t-on-click="() => props.onSelect(session.id)"
                    >
                        <div class="o_openclaw_chat_session_name"><t t-esc="session.name"/></div>
                        <div class="o_openclaw_chat_session_preview">
                            <t t-esc="session.last_message_preview or 'Start a new conversation'"/>
                        </div>
                    </button>
                </t>
            </div>
        </aside>
    </t>

    <t t-name="openclaw.ChatHeader">
        <header class="o_openclaw_chat_main_header">
            <div>
                <div class="o_openclaw_chat_kicker">Conversation</div>
                <h2><t t-esc="props.session and props.session.name or 'Untitled session'"/></h2>
            </div>
            <div class="o_openclaw_chat_status">
                <span class="o_openclaw_chat_dot"/>
                <span>Connected</span>
            </div>
        </header>
    </t>

    <t t-name="openclaw.ChatMessages">
        <div class="o_openclaw_chat_messages">
            <t t-if="props.loading">
                <div class="o_openclaw_chat_empty_state">Loading chat history…</div>
            </t>
            <t t-elif="!props.messages.length and !props.sending">
                <div class="o_openclaw_chat_empty_state">
                    Start the conversation and OpenClaw will keep the session history here.
                </div>
            </t>
            <t t-else="">
                <t t-foreach="props.messages" t-as="message" t-key="message.id">
                    <article t-att-class="'o_openclaw_chat_message is-' + message.role">
                        <div class="o_openclaw_chat_message_meta"><t t-esc="message.author_name"/></div>
                        <div class="o_openclaw_chat_bubble">
                            <div class="o_openclaw_chat_message_content"><t t-esc="message.content"/></div>
                        </div>
                        <t t-if="message.requests and message.requests.length">
                            <div class="o_openclaw_chat_cards">
                                <t t-foreach="message.requests" t-as="request" t-key="request.id">
                                    <ActionCard
                                        request="request"
                                        disableApprove="props.sessionHasApproving and props.approvingRequestId !== request.id"
                                        isApproving="props.approvingRequestId === request.id"
                                        onApprove.bind="props.onApprove"
                                        onReject.bind="props.onReject"
                                        onViewDetail.bind="props.onViewDetail"
                                    />
                                </t>
                            </div>
                        </t>
                    </article>
                </t>
                <t t-if="props.sending">
                    <article class="o_openclaw_chat_message is-assistant">
                        <div class="o_openclaw_chat_message_meta">OpenClaw</div>
                        <div class="o_openclaw_chat_bubble">
                            <div class="o_openclaw_chat_message_content">OpenClaw está pensando…</div>
                        </div>
                    </article>
                </t>
            </t>
        </div>
    </t>

    <t t-name="openclaw.ActionCard">
        <div
            class="o_openclaw_action_card"
            role="group"
            t-att-aria-label="'Acción propuesta: ' + props.request.policy_key"
        >
            <div class="o_openclaw_action_card_head">
                <span class="o_openclaw_action_card_icon">
                    <t t-if="props.isApproving">⟳</t>
                    <t t-elif="props.request.state === 'executed'">✓</t>
                    <t t-elif="props.request.state === 'failed'">✕</t>
                    <t t-elif="props.request.state === 'rejected'">–</t>
                    <t t-elif="props.request.blocked">⚠</t>
                    <t t-else="">○</t>
                </span>
                <span class="o_openclaw_action_card_title">
                    <t t-esc="props.request.action_type"/>
                    <t t-if="props.request.target_model"> · <t t-esc="props.request.target_model"/></t>
                    <t t-if="props.request.target_ref">/<t t-esc="props.request.target_ref"/></t>
                </span>
                <span t-att-class="'o_openclaw_action_card_chip is-' + (props.request.blocked ? 'blocked' : props.request.state)">
                    <t t-if="props.request.blocked">Bloqueada</t>
                    <t t-elif="props.isApproving">Ejecutando…</t>
                    <t t-elif="props.request.state === 'draft'">Propuesta</t>
                    <t t-elif="props.request.state === 'pending'">Pendiente</t>
                    <t t-elif="props.request.state === 'approved'">Ejecutando…</t>
                    <t t-elif="props.request.state === 'executed'">Ejecutada</t>
                    <t t-elif="props.request.state === 'failed'">Fallida</t>
                    <t t-elif="props.request.state === 'rejected'">Rechazada</t>
                </span>
            </div>
            <div class="o_openclaw_action_card_meta" t-if="props.request.policy_name">
                Policy <code><t t-esc="props.request.policy_name"/></code>
            </div>
            <div class="o_openclaw_action_card_rationale" t-if="props.request.rationale">
                <t t-esc="props.request.rationale"/>
            </div>
            <div class="o_openclaw_action_card_rationale" t-if="props.request.blocked and props.request.decision_note">
                <t t-esc="props.request.decision_note"/>
            </div>
            <div class="o_openclaw_action_card_actions">
                <t t-if="!props.request.blocked and ['draft','pending'].includes(props.request.state) and !props.isApproving">
                    <button type="button" class="is-approve"
                            t-att-disabled="props.disableApprove"
                            t-on-click="() => props.onApprove(props.request.id)">Approve</button>
                    <button type="button" class="is-reject"
                            t-on-click="() => props.onReject(props.request.id)">Reject</button>
                </t>
                <t t-if="props.isApproving">
                    <span class="o_openclaw_action_card_spinner"/>
                </t>
                <button type="button" class="is-detail"
                        t-on-click="() => props.onViewDetail(props.request.id)">Details</button>
            </div>
        </div>
    </t>

    <t t-name="openclaw.ChatComposer">
        <div class="o_openclaw_chat_composer">
            <textarea
                class="o_openclaw_chat_input"
                placeholder="Type a message and press Enter to send"
                t-att-value="props.draft"
                t-on-input="(ev) => props.onDraftChange(ev.target.value)"
                t-on-keydown="(ev) => { if (ev.key === 'Enter' &amp;&amp; !ev.shiftKey) { ev.preventDefault(); props.onSend(); } }"
                rows="1"
            />
            <button type="button" class="o_openclaw_chat_send"
                    t-att-disabled="props.sending or !props.draft.trim()"
                    t-on-click="() => props.onSend()">↑</button>
        </div>
    </t>

    <t t-name="openclaw.RequestDrawer">
        <div class="o_openclaw_drawer_backdrop is-open" t-on-click="() => props.onClose()"/>
        <aside class="o_openclaw_drawer is-open" role="dialog" aria-label="Request details">
            <div class="o_openclaw_drawer_header">
                <h3>Request details</h3>
                <button type="button" class="o_openclaw_drawer_close" t-on-click="() => props.onClose()">×</button>
            </div>
            <div class="o_openclaw_drawer_body">
                <t t-if="props.loading">
                    <div>Loading…</div>
                </t>
                <t t-elif="props.request">
                    <div class="o_openclaw_drawer_section">
                        <h4>State</h4>
                        <div><t t-esc="props.request.state"/></div>
                    </div>
                    <div class="o_openclaw_drawer_section" t-if="props.request.rationale">
                        <h4>Rationale</h4>
                        <div><t t-esc="props.request.rationale"/></div>
                    </div>
                    <div class="o_openclaw_drawer_section" t-if="props.request.payload_json">
                        <h4>Payload</h4>
                        <pre><t t-esc="props.request.payload_json"/></pre>
                    </div>
                    <div class="o_openclaw_drawer_section" t-if="props.request.policy_snapshot_json">
                        <h4>Policy snapshot</h4>
                        <pre><t t-esc="props.request.policy_snapshot_json"/></pre>
                    </div>
                    <div class="o_openclaw_drawer_section" t-if="props.request.gateway_response_json">
                        <h4>Gateway response</h4>
                        <pre><t t-esc="props.request.gateway_response_json"/></pre>
                    </div>
                    <div class="o_openclaw_drawer_section" t-if="props.request.error_message">
                        <h4>Error</h4>
                        <div><t t-esc="props.request.error_message"/></div>
                    </div>
                </t>
            </div>
        </aside>
    </t>

</templates>
```

- [ ] **Step 2: Commit**

```bash
git add addons_custom/openclaw/static/src/xml/openclaw_chat.xml
git commit -m "feat(openclaw): split chat templates into sub-components with action cards"
```

Visual verification in Task 13.

---

### Task 12: JS — sub-components, new RPCs, drawer state, approve/reject logic

**Files:**
- Rewrite: `addons_custom/openclaw/static/src/js/openclaw_chat.js`

- [ ] **Step 1: Replace the file contents**

```javascript
/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

class ChatSidebar extends Component {}
ChatSidebar.template = "openclaw.ChatSidebar";
ChatSidebar.props = {
    sessions: Array,
    activeSessionId: { type: [Number, Boolean], optional: true },
    onSelect: Function,
    onCreate: Function,
};

class ChatHeader extends Component {}
ChatHeader.template = "openclaw.ChatHeader";
ChatHeader.props = {
    session: { type: Object, optional: true },
};

class ActionCard extends Component {}
ActionCard.template = "openclaw.ActionCard";
ActionCard.props = {
    request: Object,
    disableApprove: { type: Boolean, optional: true },
    isApproving: { type: Boolean, optional: true },
    onApprove: Function,
    onReject: Function,
    onViewDetail: Function,
};

class ChatMessages extends Component {}
ChatMessages.template = "openclaw.ChatMessages";
ChatMessages.components = { ActionCard };
ChatMessages.props = {
    messages: Array,
    loading: Boolean,
    sending: Boolean,
    approvingRequestId: { type: [Number, null], optional: true },
    sessionHasApproving: Boolean,
    onApprove: Function,
    onReject: Function,
    onViewDetail: Function,
};

class ChatComposer extends Component {}
ChatComposer.template = "openclaw.ChatComposer";
ChatComposer.props = {
    draft: String,
    sending: Boolean,
    onDraftChange: Function,
    onSend: Function,
};

class RequestDrawer extends Component {}
RequestDrawer.template = "openclaw.RequestDrawer";
RequestDrawer.props = {
    request: { type: Object, optional: true },
    loading: Boolean,
    onClose: Function,
};

export class OpenClawChatAction extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            sessions: [],
            activeSession: null,
            messages: [],
            draft: "",
            loading: true,
            sending: false,
            sidebarOpen: false,
            approvingRequestId: null,
            drawerRequestId: null,
            drawerRequest: null,
            drawerLoading: false,
        });

        this.refreshSessions = async () => {
            this.state.sessions = await this.orm.call(
                "openclaw.chat.session", "rpc_list_sessions", [],
            );
        };

        this.selectSession = async (sessionId) => {
            this.state.loading = true;
            try {
                const session = await this.orm.call(
                    "openclaw.chat.session", "rpc_get_session", [sessionId],
                );
                this.state.activeSession = session;
                this.state.messages = session.messages || [];
                await this.refreshSessions();
            } finally {
                this.state.loading = false;
            }
        };

        this.createSession = async () => {
            this.state.loading = true;
            try {
                const session = await this.orm.call(
                    "openclaw.chat.session", "rpc_create_session", [],
                );
                await this.refreshSessions();
                await this.selectSession(session.id);
            } catch (error) {
                this.notification.add(_t("Unable to create a new chat session."), { type: "danger" });
                throw error;
            } finally {
                this.state.loading = false;
            }
        };

        this.setDraft = (value) => {
            this.state.draft = value;
        };

        this.sendMessage = async () => {
            const content = this.state.draft.trim();
            if (!content || this.state.sending) return;
            if (!this.state.activeSession) {
                await this.createSession();
            }
            const sessionId = this.state.activeSession.id;
            this.state.sending = true;
            this.state.draft = "";
            try {
                const result = await this.orm.call(
                    "openclaw.chat.session", "rpc_send_message",
                    [sessionId, content],
                );
                this.state.activeSession = result.session;
                this.state.messages = result.session.messages || [];
                await this.refreshSessions();
            } catch (error) {
                this.notification.add(_t("OpenClaw could not send the message."), { type: "danger" });
                this.state.draft = content;
            } finally {
                this.state.sending = false;
            }
        };

        this.approveRequest = async (requestId) => {
            if (this.state.approvingRequestId !== null) return;
            this.state.approvingRequestId = requestId;
            try {
                const updated = await this.orm.call(
                    "openclaw.chat.session", "rpc_approve_request",
                    [requestId],
                );
                this._replaceRequestInMessages(updated);
                if (updated.state === "failed") {
                    this.notification.add(_t("OpenClaw could not execute the action."), { type: "danger" });
                }
            } catch (error) {
                this.notification.add(_t("Approval failed."), { type: "danger" });
            } finally {
                this.state.approvingRequestId = null;
            }
        };

        this.rejectRequest = async (requestId) => {
            try {
                const updated = await this.orm.call(
                    "openclaw.chat.session", "rpc_reject_request",
                    [requestId],
                );
                this._replaceRequestInMessages(updated);
            } catch (error) {
                this.notification.add(_t("Rejection failed."), { type: "danger" });
            }
        };

        this.openRequestDetail = async (requestId) => {
            this.state.drawerRequestId = requestId;
            this.state.drawerRequest = null;
            this.state.drawerLoading = true;
            try {
                const detail = await this.orm.call(
                    "openclaw.chat.session", "rpc_get_request_detail",
                    [requestId],
                );
                this.state.drawerRequest = detail;
            } catch (error) {
                this.notification.add(_t("Could not load request details."), { type: "danger" });
                this.state.drawerRequestId = null;
            } finally {
                this.state.drawerLoading = false;
            }
        };

        this.closeDrawer = () => {
            this.state.drawerRequestId = null;
            this.state.drawerRequest = null;
        };

        this._replaceRequestInMessages = (updated) => {
            for (const message of this.state.messages) {
                if (!message.requests) continue;
                const idx = message.requests.findIndex((r) => r.id === updated.id);
                if (idx >= 0) {
                    message.requests[idx] = { ...message.requests[idx], ...updated };
                    return;
                }
            }
        };

        onWillStart(async () => {
            await this.refreshSessions();
            if (this.state.sessions.length) {
                await this.selectSession(this.state.sessions[0].id);
            } else {
                await this.createSession();
            }
        });
    }
}

OpenClawChatAction.template = "openclaw.OpenClawChatAction";
OpenClawChatAction.components = {
    ChatSidebar,
    ChatHeader,
    ChatMessages,
    ChatComposer,
    RequestDrawer,
};

registry.category("actions").add("openclaw_chat_action", OpenClawChatAction);
```

- [ ] **Step 2: Commit**

```bash
git add addons_custom/openclaw/static/src/js/openclaw_chat.js
git commit -m "feat(openclaw): chat action with sub-components and approve/reject flows"
```

Smoke test in Task 13.

---

### Task 13: End-to-end smoke test and docker reload

**Files:** none modified. This is a verification task.

- [ ] **Step 1: Restart services**

Run:
```bash
docker compose restart control-plane odoo
```

Wait ~10 seconds, then:
```bash
docker compose logs --tail=60 control-plane odoo | grep -iE "error|exception" | head -20
```

Expected: no uncaught exceptions from openclaw or mcp_gateway.

- [ ] **Step 2: Upgrade the addon**

Run:
```bash
docker compose exec odoo odoo -u openclaw -d odoo --stop-after-init
```

Expected: exits with code 0; log shows the 4 new fields loaded on `openclaw.request`.

- [ ] **Step 3: Run the full test suite one more time**

```bash
docker compose exec odoo odoo --test-tags openclaw -d odoo -u openclaw --stop-after-init
cd control-plane && python -m unittest discover app/tests -v && cd ..
```

Expected: all tests PASS.

- [ ] **Step 4: Manual browser smoke test**

Open the Odoo instance, log in as a user in `openclaw.group_openclaw_user`, open the OpenClaw menu. Verify:

1. Chat shell renders in the new light theme (blue `#2563eb` accent, Inter font, no amber glow).
2. Sidebar shows sessions, "+ New" button creates a session.
3. Typing a message and pressing Enter sends it; an assistant reply appears.
4. If the gateway is configured and the LLM cooperates, at least one `ActionCard` appears below the assistant bubble with Approve/Reject/Details.
5. Click Approve on a low-risk action (e.g. `db_read` on a small query) → spinner → card transitions to "Ejecutada" with green chip.
6. Click Details on a card → drawer slides in from the right with payload JSON and policy snapshot.
7. Resize to 700px → sidebar collapses (current behavior: hidden; acceptable for this iteration). Drawer still readable.
8. Click Reject on a fresh card → chip turns "Rechazada", buttons disappear.
9. Reload page → state survives on the server; session and request states intact.

If any of the above fails, debug before committing. Do **not** commit this task unless all items check out.

- [ ] **Step 5: Commit the checklist record**

The smoke test does not change files, so there is no commit to make. Document the result in the PR description when raising it.

---

## Self-Review — spec coverage check

Cross-check of every spec section vs. tasks:

- §3 Architecture — implemented across Tasks 4, 6, 7, 8, 9 (Odoo layer) and Tasks 3, 4 (gateway layer).
- §4.1 Request fields — Task 1.
- §4.2/4.3 One2many on session/message — Task 2.
- §4.4 `_chat_card_payload` + message payload extension — Tasks 1 and 2.
- §4.5 Access rights fallback (drop + log for non-openclaw users) — Task 7 (inside `_materialize_suggestions`).
- §4.6 Migration — no explicit task; the schema is additive and `odoo -u openclaw` in Task 13 exercises it.
- §5.1/5.2 Gateway contract — Task 4.
- §5.3 System prompt extension — Task 4 (`_inject_policy_system_prompt`).
- §5.4 Envelope parser — Task 3.
- §5.5 Fallback mode — Task 4 (fallback branch returns `[]`).
- §6.1 Layout — Tasks 10, 11.
- §6.2 Component tree — Tasks 11, 12.
- §6.3 ActionCard state → visual mapping — Task 11 (XML) + Task 10 (chip classes).
- §6.4 Interactions (Approve/Reject/Details) — Task 12.
- §7 Visual style tokens — Task 10.
- §8.1 UI states — Tasks 11, 12 (sending ghost bubble, approving spinner, drawer loading).
- §8.2 Error paths — Tasks 6 (gateway error), 9 (approve failure), 12 (UI notifications).
- §8.3 Degraded mode — Task 4 (fallback branch).
- §8.4 Anti-abuse rules — Task 7 (truncation, forced approval, no parallel approves via `disableApprove`).
- §8.5 Logging — Task 7 (`_logger.info`/`_logger.warning`) and Task 9 (approval failure warning).
- §9 Testing — Tasks 1, 2, 3, 4, 5, 6, 7, 8, 9; smoke checklist in Task 13.
- §10 Rollout — Task 13 steps 1–4.
- §11 Rollback — no task (design note; verified manually if needed).
- §12 File-level summary — matches the File Structure section at the top of this plan.

**Gaps or notes:**

- The spec mentioned `__manifest__.py` in §12 "may register tests/". Odoo auto-discovers `tests/` subpackage; no manifest change required, and Task 1 adds `__init__.py` already.
- The spec noted a potential future `message.response_json` — explicitly out of scope, no task.
- The `policy_id` moving from `required=True` to optional-with-constraint is a spec extension the implementation requires; documented in Task 1.
