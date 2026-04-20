from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "openclaw_ai_pilot_crm_contacts")
class TestOpenClawAiCrmContactsPilot(TransactionCase):
    def setUp(self):
        super().setUp()
        self.base_user_group = self.env.ref("base.group_user")
        self.openclaw_user_group = self.env.ref("openclaw.group_openclaw_user")
        self.user = self.env["res.users"].create({
            "name": "CRM Contacts Pilot User",
            "login": "crm.contacts.pilot@example.com",
            "group_ids": [(6, 0, [self.base_user_group.id, self.openclaw_user_group.id])],
        })
        self.session = self.env["openclaw.chat.session"].with_user(self.user).create({
            "name": "CRM Contacts Pilot",
            "user_id": self.user.id,
        })

    def test_res_partner_context_resolves_crm_contacts_agent(self):
        default_prompt = self.env.ref("openclaw.openclaw_ai_default_prompt_crm_contacts")
        llm_profile = self.env.ref("openclaw.openclaw_ai_llm_profile_crm_contacts")

        bundle = self.session._resolve_chat_runtime(origin_kind="model", origin_model="res.partner")

        self.assertEqual(bundle["default_prompt"]["id"], default_prompt.id)
        self.assertEqual(bundle["agent"]["key"], "crm_contacts_agent")
        self.assertEqual(bundle["llm_profile"]["id"], llm_profile.id)
        tool_keys = [tool["key"] for tool in bundle["allowed_tools"]]
        self.assertIn("odoo.search_read", tool_keys)
        self.assertIn("odoo.create_request", tool_keys)
