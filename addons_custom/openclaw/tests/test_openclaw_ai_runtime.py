import json

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "openclaw_ai_runtime")
class TestOpenClawAiRuntime(TransactionCase):
    def setUp(self):
        super().setUp()
        self.base_user_group = self.env.ref("base.group_user")
        self.openclaw_user_group = self.env.ref("openclaw.group_openclaw_user")
        self.admin_company = self.env.company
        self.other_company = self.env["res.company"].create({"name": "Other Company"})
        self.env["openclaw.policy"].search([
            ("active", "=", True),
            ("group_ids", "in", self.openclaw_user_group.id),
        ]).write({"active": False})
        self.env["openclaw.ai.default_prompt"].search([
            ("active", "=", True),
        ]).write({"active": False})
        self.user = self.env["res.users"].create({
            "name": "Runtime User",
            "login": "runtime.user@example.com",
            "group_ids": [(6, 0, [self.base_user_group.id, self.openclaw_user_group.id])],
        })
        self.session = self.env["openclaw.chat.session"].with_user(self.user).create({
            "name": "Runtime Session",
            "user_id": self.user.id,
        })
        self.profile = self.env["openclaw.ai.llm_profile"].create({
            "name": "OpenRouter Main",
            "model_name": "z-ai/glm-4.5-air:free",
        })
        self.read_tool = self.env["openclaw.ai.tool"].create({
            "name": "Read Contacts",
            "key": "odoo.search_read",
            "gateway_name": "odoo.search_read",
            "required_policy_action": "odoo_read",
        })
        self.write_tool = self.env["openclaw.ai.tool"].create({
            "name": "Create Requests",
            "key": "odoo.create_request",
            "gateway_name": "odoo.create_request",
            "execution_kind": "write",
            "required_policy_action": "odoo_write",
            "risk_level": "medium",
        })
        self.topic = self.env["openclaw.ai.topic"].create({
            "name": "CRM Contacts",
            "key": "crm_contacts",
            "mode": "actionable",
        })
        self.env["openclaw.ai.topic.tool"].create({
            "topic_id": self.topic.id,
            "tool_id": self.read_tool.id,
            "required": True,
        })
        self.env["openclaw.ai.topic.tool"].create({
            "topic_id": self.topic.id,
            "tool_id": self.write_tool.id,
        })
        self.agent_global = self.env["openclaw.ai.agent"].create({
            "name": "Global Agent",
            "key": "global_agent",
            "llm_profile_id": self.profile.id,
            "topic_ids": [(6, 0, [self.topic.id])],
        })
        self.agent_partner = self.env["openclaw.ai.agent"].create({
            "name": "Partner Agent",
            "key": "partner_agent",
            "llm_profile_id": self.profile.id,
            "topic_ids": [(6, 0, [self.topic.id])],
        })
        self.global_prompt = self.env["openclaw.ai.default_prompt"].create({
            "name": "Global Prompt",
            "sequence": 20,
            "applies_to_all_models": True,
            "agent_id": self.agent_global.id,
            "instructions": "Global instructions",
        })
        self.partner_prompt = self.env["openclaw.ai.default_prompt"].create({
            "name": "Partner Prompt",
            "sequence": 10,
            "agent_id": self.agent_partner.id,
            "model_ids": [(6, 0, [self.env.ref("base.model_res_partner").id])],
            "instructions": "Partner instructions",
        })
        self.env["openclaw.policy"].create({
            "name": "Read Odoo",
            "key": "read_odoo",
            "sequence": 10,
            "allow_read_odoo": True,
            "group_ids": [(6, 0, [self.openclaw_user_group.id])],
        })

    def test_model_specific_default_prompt_beats_global(self):
        bundle = self.session._resolve_chat_runtime(origin_kind="model", origin_model="res.partner")
        self.assertEqual(bundle["default_prompt"]["id"], self.partner_prompt.id)
        self.assertEqual(bundle["agent"]["id"], self.agent_partner.id)
        self.assertEqual(bundle["agent"]["key"], "partner_agent")

    def test_prompt_eligibility_filters_by_group_and_company(self):
        admin_group = self.env.ref("openclaw.group_openclaw_admin")
        blocked_prompt = self.env["openclaw.ai.default_prompt"].create({
            "name": "Blocked Prompt",
            "sequence": 1,
            "agent_id": self.agent_global.id,
            "applies_to_all_models": True,
            "group_ids": [(6, 0, [admin_group.id])],
            "company_id": self.other_company.id,
        })
        bundle = self.session._resolve_chat_runtime(origin_kind="global")
        self.assertEqual(bundle["default_prompt"]["id"], self.global_prompt.id)
        self.assertNotEqual(bundle["default_prompt"]["id"], blocked_prompt.id)

    def test_allowed_tools_intersect_topic_tools_and_policy(self):
        bundle = self.session._resolve_chat_runtime(origin_kind="model", origin_model="res.partner")
        tool_keys = [tool["key"] for tool in bundle["allowed_tools"]]
        self.assertIn("odoo.search_read", tool_keys)
        self.assertNotIn("odoo.create_request", tool_keys)

    def test_runtime_bundle_persists_on_session(self):
        bundle = self.session._resolve_chat_runtime(
            origin_kind="model",
            origin_model="res.partner",
            persist=True,
        )
        self.session.invalidate_recordset()
        self.assertEqual(self.session.resolved_agent_id, self.agent_partner)
        self.assertEqual(self.session.resolved_default_prompt_id, self.partner_prompt)
        self.assertEqual(self.session.resolved_llm_profile_id, self.profile)
        stored = json.loads(self.session.runtime_bundle_json)
        self.assertEqual(stored["agent"]["id"], bundle["agent"]["id"])
        self.assertEqual(self.session.runtime_bundle_version, bundle["bundle_version"])
