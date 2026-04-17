from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    openclaw_enabled = fields.Boolean(
        string='Enable OpenClaw',
        config_parameter='openclaw.enabled',
    )
    openclaw_gateway_url = fields.Char(
        string='MCP Gateway URL',
        default='http://control-plane:8082',
        config_parameter='openclaw.gateway_url',
    )
    openclaw_docs_root = fields.Char(
        string='Docs Root',
        default='/app/docs',
        config_parameter='openclaw.docs_root',
    )
    openclaw_require_human_approval = fields.Boolean(
        string='Require Human Approval For Dangerous Actions',
        default=True,
        config_parameter='openclaw.require_human_approval',
    )
    openclaw_allowed_tools = fields.Text(
        string='Allowed Tools',
        default='db.read\ndb.write\nodoo.read\nodoo.write\ncrm.write\ncalendar.write\ndocs.read\ndocs.write\ndocs.read_markdown\ndocs.write_markdown\nworkspace.read_file\nworkspace.write_file\nworkspace.list_tree\nworkspace.search\nweb.search\ncode.generate\nshell.execute',
        config_parameter='openclaw.allowed_tools',
    )
