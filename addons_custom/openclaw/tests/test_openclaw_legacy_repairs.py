import json

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestLegacyDashboardAliasRepairs(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user_group = self.env.ref("openclaw.group_openclaw_user")
        self.base_user_group = self.env.ref("base.group_user")
        self.user = self.env["res.users"].create({
            "name": "Legacy Repair User",
            "login": "legacyrepair@example.com",
            "group_ids": [(6, 0, [self.user_group.id, self.base_user_group.id])],
        })
        self.read_only_policy = self.env["openclaw.policy"].create({
            "name": "Read Only",
            "key": "legacy_read_only",
            "sequence": 10,
            "allow_read_odoo": True,
            "group_ids": [(6, 0, [self.user_group.id])],
        })
        self.write_policy = self.env["openclaw.policy"].create({
            "name": "Write Policy",
            "key": "legacy_write",
            "sequence": 20,
            "allow_write_odoo": True,
            "require_human_approval": True,
            "group_ids": [(6, 0, [self.user_group.id])],
        })
        self.session = self.env["openclaw.chat.session"].with_user(self.user).create({
            "name": "Legacy session",
            "user_id": self.user.id,
        })
        self.message = self.env["openclaw.chat.message"].with_user(self.user).create({
            "session_id": self.session.id,
            "role": "assistant",
            "content": "legacy blocked card",
        })

    def test_repair_legacy_dashboard_alias_rehydrates_request(self):
        request = self.env["openclaw.request"].with_user(self.user).create({
            "name": "Legacy dashboard",
            "instruction": (
                "El usuario quiere un dashboard llamado 'jairo' con un gráfico "
                "de barras mostrando el número de registros en el módulo de ventas."
            ),
            "session_id": self.session.id,
            "message_id": self.message.id,
            "origin": "chat_suggestion",
            "action_type": "custom",
            "decision_note": "Invalid action_type: 'create_dashboard'",
            "approval_required": True,
        })

        repaired = request.repair_legacy_dashboard_alias_blocks()

        self.assertEqual(repaired, request)
        self.assertEqual(request.state, "draft")
        self.assertEqual(request.action_type, "odoo_write")
        self.assertEqual(request.policy_id, self.write_policy)
        self.assertEqual(request.target_model, "dashboard.dashboard")
        self.assertFalse(request.decision_note)
        self.assertTrue(request.approval_required)

        payload = json.loads(request.payload_json)
        self.assertEqual(payload["model"], "dashboard.dashboard")
        self.assertEqual(payload["operation"], "create")
        self.assertEqual(payload["values"]["name"], "jairo")
        self.assertEqual(payload["blueprint"]["chart_type"], "bar_chart")
        self.assertEqual(payload["blueprint"]["model"], "sale.order")
        self.assertEqual(payload["blueprint"]["fields"], ["state"])
        self.assertIn("Supuestos", request.rationale)
        self.assertIn("sale.order", request.rationale)

    def test_message_payload_auto_repairs_legacy_dashboard_alias(self):
        request = self.env["openclaw.request"].with_user(self.user).create({
            "name": "Legacy dashboard",
            "instruction": (
                "El usuario quiere un dashboard con un gráfico de barras que "
                "muestre el número de registros del módulo de ventas"
            ),
            "session_id": self.session.id,
            "message_id": self.message.id,
            "origin": "chat_suggestion",
            "action_type": "custom",
            "decision_note": "Invalid action_type: 'create_dashboard'",
            "approval_required": True,
        })

        payload = self.session.with_user(self.user)._message_payload(self.message)

        self.assertEqual(payload["requests"][0]["id"], request.id)
        self.assertEqual(payload["requests"][0]["action_type"], "odoo_write")
        self.assertFalse(payload["requests"][0]["blocked"])
        self.assertEqual(request.policy_id, self.write_policy)
        self.assertEqual(request.target_model, "dashboard.dashboard")

    def test_repair_skips_non_repairable_blocked_requests(self):
        request = self.env["openclaw.request"].with_user(self.user).create({
            "name": "Other blocked request",
            "instruction": "El usuario quiere un dashboard",
            "session_id": self.session.id,
            "message_id": self.message.id,
            "origin": "chat_suggestion",
            "action_type": "custom",
            "decision_note": "Invalid action_type: 'create_dashboard'",
            "approval_required": True,
        })

        repaired = request.repair_legacy_dashboard_alias_blocks()

        self.assertFalse(repaired)
        self.assertFalse(request.policy_id)
        self.assertEqual(request.action_type, "custom")
        self.assertIn("create_dashboard", request.decision_note)
