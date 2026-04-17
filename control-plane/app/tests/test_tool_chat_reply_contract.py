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
