from unittest.mock import patch

from odoo.addons.openclaw.models.gateway_client import OpenClawGatewayClient
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


@tagged("post_install", "-at_install")
class TestBuildPolicyContext(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user_group = self.env.ref("openclaw.group_openclaw_user")
        self.admin_group = self.env.ref("openclaw.group_openclaw_admin")
        self.base_user_group = self.env.ref("base.group_user")
        self.user = self.env["res.users"].create({
            "name": "Chat User",
            "login": "chatuser@example.com",
            "group_ids": [(6, 0, [self.user_group.id, self.base_user_group.id])],
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
