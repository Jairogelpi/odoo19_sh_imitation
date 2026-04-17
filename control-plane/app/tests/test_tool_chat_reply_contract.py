import asyncio
import unittest

from app.mcp_gateway import OpenClawMCPGateway, _parse_llm_envelope


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


class TestToolChatReplyOutput(unittest.TestCase):
    def _run(self, coro):
        return asyncio.new_event_loop().run_until_complete(coro)

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
