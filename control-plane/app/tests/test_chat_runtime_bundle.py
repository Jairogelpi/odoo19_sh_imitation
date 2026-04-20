import asyncio
import unittest

from app.mcp_gateway import OpenClawMCPGateway
from app.schema_validation import load_schema


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


class TestChatRuntimeBundle(unittest.TestCase):
    def _run(self, coro):
        return asyncio.new_event_loop().run_until_complete(coro)

    def test_runtime_bundle_schema_file_exists(self):
        schema = load_schema("runtime_bundle.v1.json")
        self.assertEqual(schema["type"], "object")

    def test_invalid_runtime_bundle_is_rejected_before_provider_call(self):
        gateway = OpenClawMCPGateway.__new__(OpenClawMCPGateway)
        gateway.openrouter = type("O", (), {"configured": True})()

        async def fail_chat_reply(*args, **kwargs):
            raise AssertionError("invalid runtime bundles must be rejected before provider calls")

        gateway.openrouter.chat_reply = fail_chat_reply

        result = self._run(gateway.tool_chat_reply({
            "messages": [{"role": "user", "content": "hola"}],
            "runtime_bundle": {"bundle_version": "broken"},
        }))

        self.assertEqual(result["kind"], "rejected")
        self.assertIn("runtime_bundle", result["summary"])

    def test_valid_runtime_bundle_short_circuits_legacy_router(self):
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
