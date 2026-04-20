from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "openclaw_ai_registry")
class TestOpenClawAiRegistry(TransactionCase):
    def setUp(self):
        super().setUp()
        self.base_user_group = self.env.ref("base.group_user")
        self.openclaw_admin_group = self.env.ref("openclaw.group_openclaw_admin")

    def _has_access(self, model_name, user, operation):
        try:
            self.env[model_name].with_user(user).check_access(operation)
        except AccessError:
            return False
        return True

    def test_ai_models_are_registered(self):
        for model_name in (
            "openclaw.ai.agent",
            "openclaw.ai.topic",
            "openclaw.ai.tool",
            "openclaw.ai.source",
            "openclaw.ai.default_prompt",
            "openclaw.ai.default_prompt.button",
            "openclaw.ai.llm_profile",
        ):
            self.assertIn(model_name, self.env)

    def test_chat_session_exposes_runtime_fields(self):
        session_fields = self.env["openclaw.chat.session"]._fields
        for field_name in (
            "origin_kind",
            "origin_model",
            "origin_res_id",
            "resolved_agent_id",
            "resolved_default_prompt_id",
            "resolved_llm_profile_id",
            "runtime_bundle_version",
            "runtime_bundle_json",
        ):
            self.assertIn(field_name, session_fields)

    def test_ai_relationship_fields_exist(self):
        agent_fields = self.env["openclaw.ai.agent"]._fields
        topic_fields = self.env["openclaw.ai.topic"]._fields
        tool_fields = self.env["openclaw.ai.tool"]._fields
        prompt_fields = self.env["openclaw.ai.default_prompt"]._fields

        for field_name in ("topic_ids", "source_ids", "llm_profile_id"):
            self.assertIn(field_name, agent_fields)
        self.assertIn("tool_binding_ids", topic_fields)
        self.assertIn("required_policy_action", tool_fields)
        for field_name in ("agent_id", "button_ids", "group_ids", "company_id"):
            self.assertIn(field_name, prompt_fields)

    def test_openclaw_admin_has_create_access_to_ai_models(self):
        admin_user = self.env["res.users"].create({
            "name": "OpenClaw AI Admin",
            "login": "openclaw.ai.admin@example.com",
            "group_ids": [(6, 0, [self.base_user_group.id, self.openclaw_admin_group.id])],
        })
        self.assertTrue(self._has_access("openclaw.ai.agent", admin_user, "create"))
        self.assertTrue(self._has_access("openclaw.ai.default_prompt", admin_user, "write"))

    def test_base_internal_user_has_no_ai_admin_access(self):
        internal_user = self.env["res.users"].create({
            "name": "Internal Only",
            "login": "internal.only@example.com",
            "group_ids": [(6, 0, [self.base_user_group.id])],
        })
        self.assertFalse(self._has_access("openclaw.ai.agent", internal_user, "create"))
        self.assertFalse(self._has_access("openclaw.ai.default_prompt", internal_user, "write"))
