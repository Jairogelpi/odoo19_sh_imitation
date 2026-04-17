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
