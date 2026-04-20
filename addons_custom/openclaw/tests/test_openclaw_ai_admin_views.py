from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "openclaw_ai_admin")
class TestOpenClawAiAdminViews(TransactionCase):
    def test_admin_views_and_actions_are_registered(self):
        for xmlid in (
            "openclaw.action_openclaw_ai_agent",
            "openclaw.action_openclaw_ai_topic",
            "openclaw.action_openclaw_ai_default_prompt",
            "openclaw.menu_openclaw_ai",
        ):
            self.env.ref(xmlid)
