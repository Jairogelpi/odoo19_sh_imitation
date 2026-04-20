import asyncio
import unittest

from app.mcp_gateway import OpenClawMCPGateway, _parse_llm_envelope


def _valid_runtime_bundle() -> dict:
    allowed_tool = {
        "id": 11,
        "key": "odoo.search_read",
        "name": "Read Contacts",
        "gateway_name": "odoo.search_read",
        "required_policy_action": "odoo_read",
        "execution_kind": "read",
        "risk_level": "low",
        "required": True,
        "tool_instructions": "Search contacts before proposing changes.",
    }
    return {
        "bundle_version": 1,
        "session_origin": {"kind": "model", "model": "res.partner", "res_id": False},
        "agent": {"id": 7, "key": "crm_contacts_agent", "name": "CRM Contacts"},
        "default_prompt": {"id": 8, "name": "CRM Contacts", "instructions": "Focus on CRM contacts."},
        "llm_profile": {
            "id": 9,
            "name": "OpenRouter Main",
            "backend": "openrouter",
            "model_name": "bundle/model",
            "fallback_model_name": "bundle/fallback",
        },
        "topics": [{
            "id": 10,
            "key": "crm_contacts",
            "name": "CRM Contacts",
            "mode": "actionable",
            "instructions": "Use approved contact tools only.",
            "tools": [allowed_tool],
        }],
        "sources": [],
        "allowed_tools": [allowed_tool],
        "prompt_sections": {
            "system_contract": "Return structured OpenClaw replies.",
            "agent_prompt": "You are the CRM contacts agent.",
            "default_prompt_instructions": "Prefer CRM contact workflows.",
            "topic_instructions": "Use read tools first.",
        },
        "record_context": {"model": "res.partner", "id": False},
        "ui_buttons": [],
        "policy_projection": {"allowed_actions": ["odoo_read"]},
        "schema_versions": {"runtime_bundle": "v1"},
    }


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

    def test_create_dashboard_alias_is_normalized_to_odoo_write(self):
        raw = (
            '{"reply": "ok", "suggested_actions": ['
            '{"title": "Crear dashboard", "action_type": "create_dashboard", '
            '"policy_key": "odoo-write-policy", "payload": {"values": {"name": "jairo"}}}'
            "]}"
        )
        reply, actions = _parse_llm_envelope(raw)
        self.assertEqual(reply, "ok")
        self.assertEqual(actions[0]["action_type"], "odoo_write")
        self.assertEqual(actions[0]["target_model"], "dashboard.dashboard")
        self.assertEqual(actions[0]["payload"]["model"], "dashboard.dashboard")
        self.assertEqual(actions[0]["payload"]["operation"], "create")


class TestToolChatReplyOutput(unittest.TestCase):
    def _run(self, coro):
        return asyncio.new_event_loop().run_until_complete(coro)

    def test_router_routes_contact_creation_without_llm(self):
        gateway = OpenClawMCPGateway.__new__(OpenClawMCPGateway)
        gateway.openrouter = type("O", (), {"configured": True})()

        async def fail_chat_reply(*args, **kwargs):
            raise AssertionError("router should short-circuit before OpenRouter")

        gateway.openrouter.chat_reply = fail_chat_reply

        result = self._run(gateway.tool_chat_reply({
            "messages": [{"role": "user", "content": "Crear contacto Juan García con email juan@example.com"}],
            "policy_context": {
                "available_policies": [
                    {"key": "odoo-write-policy", "allowed_actions": ["odoo_write", "odoo_read"]},
                ],
            },
        }))

        self.assertEqual(result["kind"], "completed")
        self.assertEqual(result["provider"], "local")
        self.assertEqual(result["model"], "router")
        self.assertIn("openclaw-crm-contacts", result["reply"])
        self.assertEqual(len(result["suggested_actions"]), 1)
        self.assertEqual(result["suggested_actions"][0]["target_model"], "res.partner")
        self.assertEqual(result["suggested_actions"][0]["payload"]["operation"], "create")

    def test_runtime_bundle_bypasses_contact_router(self):
        gateway = OpenClawMCPGateway.__new__(OpenClawMCPGateway)
        gateway.openrouter = type("O", (), {"configured": True})()

        async def fake_chat_reply(messages, model, temperature, max_tokens):
            return '{"reply": "bundle path", "suggested_actions": []}'

        gateway.openrouter.chat_reply = fake_chat_reply

        result = self._run(gateway.tool_chat_reply({
            "messages": [{"role": "user", "content": "Crear contacto Juan García con email juan@example.com"}],
            "runtime_bundle": _valid_runtime_bundle(),
            "policy_context": {
                "available_policies": [
                    {"key": "odoo-read-policy", "allowed_actions": ["odoo_read"]},
                ],
            },
        }))

        self.assertEqual(result["kind"], "completed")
        self.assertEqual(result["provider"], "openrouter")
        self.assertEqual(result["model"], "bundle/model")
        self.assertEqual(result["reply"], "bundle path")

    def test_router_routes_invoicing_handoff_without_llm(self):
        gateway = OpenClawMCPGateway.__new__(OpenClawMCPGateway)
        gateway.openrouter = type("O", (), {"configured": True})()

        async def fail_chat_reply(*args, **kwargs):
            raise AssertionError("router should short-circuit before OpenRouter")

        gateway.openrouter.chat_reply = fail_chat_reply

        result = self._run(gateway.tool_chat_reply({
            "messages": [{"role": "user", "content": "Necesito crear una factura para Acme"}],
            "policy_context": {
                "available_policies": [
                    {"key": "odoo-write-policy", "allowed_actions": ["odoo_write", "odoo_read"]},
                ],
            },
        }))

        self.assertEqual(result["kind"], "completed")
        self.assertEqual(result["provider"], "local")
        self.assertEqual(result["model"], "router")
        self.assertIn("openclaw-invoicing", result["reply"])
        self.assertEqual(result["suggested_actions"], [])

    def test_router_dashboard_creation_requires_full_spec_without_llm(self):
        gateway = OpenClawMCPGateway.__new__(OpenClawMCPGateway)
        gateway.openrouter = type("O", (), {"configured": True})()

        async def fail_chat_reply(*args, **kwargs):
            raise AssertionError("router should short-circuit before OpenRouter")

        gateway.openrouter.chat_reply = fail_chat_reply

        result = self._run(gateway.tool_chat_reply({
            "messages": [{"role": "user", "content": "crear dashboard Ventas Semanal"}],
            "policy_context": {
                "available_policies": [
                    {"key": "odoo-write-policy", "allowed_actions": ["odoo_write", "odoo_read"]},
                ],
            },
        }))

        self.assertEqual(result["kind"], "completed")
        self.assertEqual(result["provider"], "local")
        self.assertEqual(result["model"], "router")
        self.assertIn("openclaw-dashboard-chat", result["reply"])
        self.assertIn("tipo de gráfico", result["reply"])
        self.assertIn("modelo Odoo", result["reply"])
        self.assertEqual(result["suggested_actions"], [])

    def test_router_dashboard_creation_with_full_spec_generates_action(self):
        gateway = OpenClawMCPGateway.__new__(OpenClawMCPGateway)
        gateway.openrouter = type("O", (), {"configured": True})()

        async def fail_chat_reply(*args, **kwargs):
            raise AssertionError("router should short-circuit before OpenRouter")

        gateway.openrouter.chat_reply = fail_chat_reply

        result = self._run(gateway.tool_chat_reply({
            "messages": [{
                "role": "user",
                "content": (
                    "crear dashboard Ventas Semanal tipo bar_chart modelo sale.order "
                    "datos amount_total, user_id y representa ventas por comercial"
                ),
            }],
            "policy_context": {
                "available_policies": [
                    {"key": "odoo-write-policy", "allowed_actions": ["odoo_write", "odoo_read"]},
                ],
            },
        }))

        self.assertEqual(result["kind"], "completed")
        self.assertEqual(result["provider"], "local")
        self.assertEqual(result["model"], "router")
        self.assertIn("openclaw-dashboard-chat", result["reply"])
        self.assertEqual(len(result["suggested_actions"]), 1)
        self.assertEqual(result["suggested_actions"][0]["target_model"], "dashboard.dashboard")
        self.assertEqual(result["suggested_actions"][0]["payload"]["operation"], "create")
        self.assertEqual(result["suggested_actions"][0]["payload"]["values"]["name"], "Ventas Semanal")

    def test_router_dashboard_delegation_proposes_safe_sales_defaults(self):
        gateway = OpenClawMCPGateway.__new__(OpenClawMCPGateway)
        gateway.openrouter = type("O", (), {"configured": True})()

        async def fail_chat_reply(*args, **kwargs):
            raise AssertionError("router should short-circuit before OpenRouter")

        gateway.openrouter.chat_reply = fail_chat_reply

        result = self._run(gateway.tool_chat_reply({
            "messages": [{
                "role": "user",
                "content": "crear dashboard de ventas, hazlo tú",
            }],
            "policy_context": {
                "available_policies": [
                    {"key": "odoo-write-policy", "allowed_actions": ["odoo_write", "odoo_read"]},
                ],
            },
        }))

        self.assertEqual(result["kind"], "completed")
        self.assertEqual(result["provider"], "local")
        self.assertEqual(result["model"], "router")
        self.assertIn("configuración base", result["reply"])
        self.assertIn("sale.order", result["reply"])
        self.assertIn("bar_chart", result["reply"])
        self.assertEqual(result["suggested_actions"], [])

    def test_router_dashboard_confirmation_after_delegation_generates_action(self):
        gateway = OpenClawMCPGateway.__new__(OpenClawMCPGateway)
        gateway.openrouter = type("O", (), {"configured": True})()

        async def fail_chat_reply(*args, **kwargs):
            raise AssertionError("router should short-circuit before OpenRouter")

        gateway.openrouter.chat_reply = fail_chat_reply

        result = self._run(gateway.tool_chat_reply({
            "messages": [
                {"role": "user", "content": "crear dashboard"},
                {
                    "role": "assistant",
                    "content": "Necesito nombre, tipo, modelo, campos y objetivo.",
                },
                {
                    "role": "user",
                    "content": "lo que tú quieras de módulo de ventas",
                },
                {
                    "role": "assistant",
                    "content": (
                        "Te propongo una configuración base con sale.order, bar_chart "
                        "y conteo por state. Responde sí si te vale."
                    ),
                },
                {"role": "user", "content": "sí, hazlo"},
            ],
            "policy_context": {
                "available_policies": [
                    {"key": "odoo-write-policy", "allowed_actions": ["odoo_write", "odoo_read"]},
                ],
            },
        }))

        self.assertEqual(result["kind"], "completed")
        self.assertEqual(result["provider"], "local")
        self.assertEqual(result["model"], "router")
        self.assertEqual(len(result["suggested_actions"]), 1)
        self.assertIn("supuestos", result["reply"].lower())
        self.assertEqual(result["suggested_actions"][0]["target_model"], "dashboard.dashboard")
        self.assertEqual(result["suggested_actions"][0]["payload"]["operation"], "create")
        self.assertEqual(result["suggested_actions"][0]["payload"]["values"]["name"], "Ventas - Registros")
        self.assertEqual(result["suggested_actions"][0]["payload"]["blueprint"]["chart_type"], "bar_chart")
        self.assertEqual(result["suggested_actions"][0]["payload"]["blueprint"]["model"], "sale.order")
        self.assertEqual(result["suggested_actions"][0]["payload"]["blueprint"]["fields"], ["state"])

    def test_openrouter_reply_parsed_into_envelope(self):
        gateway = OpenClawMCPGateway.__new__(OpenClawMCPGateway)
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

    def test_openrouter_dashboard_alias_is_normalized(self):
        gateway = OpenClawMCPGateway.__new__(OpenClawMCPGateway)
        gateway.openrouter = type("O", (), {"configured": True})()

        async def fake_chat_reply(messages, model, temperature, max_tokens):
            return (
                '{"reply": "Creando dashboard", "suggested_actions": ['
                '{"title": "Crear dashboard BI", "action_type": "create_dashboard", '
                '"policy_key": "odoo-write-policy", "payload": {"values": {"name": "jairo"}}}'
                "]}"
            )

        gateway.openrouter.chat_reply = fake_chat_reply

        result = self._run(gateway.tool_chat_reply({
            "messages": [{"role": "user", "content": "hola"}],
        }))

        self.assertEqual(result["reply"], "Creando dashboard")
        self.assertEqual(len(result["suggested_actions"]), 1)
        self.assertEqual(result["suggested_actions"][0]["action_type"], "odoo_write")
        self.assertEqual(result["suggested_actions"][0]["target_model"], "dashboard.dashboard")
        self.assertEqual(result["suggested_actions"][0]["payload"]["operation"], "create")

    def test_openrouter_plain_text_reply_emits_empty_actions(self):
        gateway = OpenClawMCPGateway.__new__(OpenClawMCPGateway)
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
        gateway = OpenClawMCPGateway.__new__(OpenClawMCPGateway)
        gateway.openrouter = type("O", (), {"configured": False})()

        result = self._run(gateway.tool_chat_reply({
            "messages": [{"role": "user", "content": "hello"}],
        }))

        self.assertEqual(result["suggested_actions"], [])
        self.assertIn("hello", result["reply"])
