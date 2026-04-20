from unittest.mock import patch

from odoo.addons.openclaw.models.gateway_client import OpenClawGatewayClient
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "openclaw_ai_gateway_bundle")
class TestOpenClawAiGatewayBundle(TransactionCase):
    def setUp(self):
        super().setUp()
        self.base_user_group = self.env.ref("base.group_user")
        self.openclaw_user_group = self.env.ref("openclaw.group_openclaw_user")
        self.user = self.env["res.users"].create({
            "name": "Bundle User",
            "login": "bundle.user@example.com",
            "group_ids": [(6, 0, [self.base_user_group.id, self.openclaw_user_group.id])],
        })
        self.env["ir.config_parameter"].sudo().set_param("openclaw.gateway_url", "http://fake")
        self.session = self.env["openclaw.chat.session"].with_user(self.user).create({
            "name": "Bundle Session",
            "user_id": self.user.id,
        })
        self.profile = self.env["openclaw.ai.llm_profile"].create({
            "name": "OpenRouter Bundle",
            "model_name": "z-ai/glm-4.5-air:free",
            "temperature": 0.3,
            "max_tokens": 256,
        })
        self.agent = self.env["openclaw.ai.agent"].create({
            "name": "Bundle Agent",
            "key": "bundle_agent",
            "llm_profile_id": self.profile.id,
        })
        self.prompt = self.env["openclaw.ai.default_prompt"].create({
            "name": "Bundle Prompt",
            "sequence": 10,
            "applies_to_all_models": True,
            "agent_id": self.agent.id,
            "instructions": "Bundle instructions",
        })

    def test_rpc_send_message_passes_runtime_bundle_and_persists_runtime(self):
        Session = self.env["openclaw.chat.session"].with_user(self.user)
        with patch.object(
            OpenClawGatewayClient,
            "chat_reply",
            return_value={"reply": "ok", "suggested_actions": []},
        ) as chat_mock:
            Session.rpc_send_message(self.session.id, "hola")

        _, kwargs = chat_mock.call_args
        self.assertIn("runtime_bundle", kwargs)
        bundle = kwargs["runtime_bundle"]
        self.assertEqual(bundle["agent"]["id"], self.agent.id)
        self.assertEqual(bundle["default_prompt"]["id"], self.prompt.id)
        self.assertEqual(bundle["llm_profile"]["id"], self.profile.id)

        self.session.invalidate_recordset()
        self.assertEqual(self.session.resolved_agent_id, self.agent)
        self.assertEqual(self.session.resolved_default_prompt_id, self.prompt)
        self.assertEqual(self.session.resolved_llm_profile_id, self.profile)
        self.assertEqual(self.session.runtime_bundle_version, bundle["bundle_version"])
        self.assertTrue(self.session.runtime_bundle_json)

    def test_gateway_client_keeps_legacy_calls_working_without_runtime_bundle(self):
        client = OpenClawGatewayClient(base_url="http://fake")
        fake_result = {
            "content": [{
                "type": "text",
                "text": '{"kind": "completed", "reply": "hola"}',
            }],
        }
        with patch.object(client, "_rpc", return_value=fake_result) as rpc_mock:
            out = client.chat_reply(
                [{"role": "user", "content": "hi"}],
                policy_context={"available_policies": []},
            )

        self.assertEqual(out["reply"], "hola")
        self.assertNotIn("runtime_bundle", rpc_mock.call_args.args[1]["arguments"])
