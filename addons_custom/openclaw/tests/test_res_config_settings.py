from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOpenClawResConfigSettings(TransactionCase):
    def test_default_get_returns_allowed_tools(self):
        defaults = self.env["res.config.settings"].default_get(["openclaw_allowed_tools"])

        self.assertIn("openclaw_allowed_tools", defaults)
        self.assertIn("db.read", defaults["openclaw_allowed_tools"])

    def test_settings_view_uses_text_widget_for_allowed_tools(self):
        view = self.env.ref("openclaw.view_res_config_settings_openclaw")

        self.assertIn('name="openclaw_allowed_tools"', view.arch_db)
        self.assertIn('widget="text"', view.arch_db)
