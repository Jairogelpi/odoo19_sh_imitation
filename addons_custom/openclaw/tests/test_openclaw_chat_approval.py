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
        self.base_user_group = self.env.ref("base.group_user")
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
            "group_ids": [(6, 0, [self.user_group.id, self.base_user_group.id])],
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
