from odoo import fields, models


class OpenClawPolicy(models.Model):
    _name = 'openclaw.policy'
    _description = 'OpenClaw Policy'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    key = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text()
    group_ids = fields.Many2many('res.groups', string='Odoo Groups')
    tool_allowlist = fields.Text(string='Allowed MCP Tools')
    allow_read_db = fields.Boolean(default=False)
    allow_write_db = fields.Boolean(default=False)
    allow_read_odoo = fields.Boolean(default=True)
    allow_write_odoo = fields.Boolean(default=False)
    allow_read_docs = fields.Boolean(default=True)
    allow_write_docs = fields.Boolean(default=False)
    allow_workspace_read = fields.Boolean(default=True)
    allow_workspace_write = fields.Boolean(default=False)
    allow_web_search = fields.Boolean(default=True)
    allow_code_generation = fields.Boolean(default=False)
    allow_shell_actions = fields.Boolean(default=False)
    require_human_approval = fields.Boolean(default=True)
    notes = fields.Text()

    _sql_constraints = [
        ('openclaw_policy_key_uniq', 'unique(key)', 'The policy key must be unique.'),
    ]

    def name_get(self):
        return [(record.id, f'{record.name} [{record.key}]') for record in self]
