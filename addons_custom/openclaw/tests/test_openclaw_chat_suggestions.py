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
