from odoo import fields, models


class OpenClawAiDefaultPrompt(models.Model):
    _name = "openclaw.ai.default_prompt"
    _description = "OpenClaw AI Default Prompt"
    _order = "sequence, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    applies_to_all_models = fields.Boolean(default=False)
    model_ids = fields.Many2many("ir.model", string="Models")
    agent_id = fields.Many2one("openclaw.ai.agent", string="Agent")
    instructions = fields.Text()
    button_ids = fields.One2many(
        "openclaw.ai.default_prompt.button",
        "default_prompt_id",
        string="Buttons",
    )
    group_ids = fields.Many2many("res.groups", string="Groups")
    company_id = fields.Many2one("res.company", string="Company")


class OpenClawAiDefaultPromptButton(models.Model):
    _name = "openclaw.ai.default_prompt.button"
    _description = "OpenClaw AI Default Prompt Button"
    _order = "sequence, id"

    default_prompt_id = fields.Many2one(
        "openclaw.ai.default_prompt",
        string="Default Prompt",
        required=True,
        ondelete="cascade",
    )
    label = fields.Char(required=True)
    prompt_text = fields.Text(required=True)
    sequence = fields.Integer(default=10)
    icon = fields.Char()
