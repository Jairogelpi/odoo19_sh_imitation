from odoo import fields, models


class OpenClawAiTopic(models.Model):
    _name = "openclaw.ai.topic"
    _description = "OpenClaw AI Topic"
    _order = "sequence, id"

    name = fields.Char(required=True)
    key = fields.Char(required=True)
    active = fields.Boolean(default=True)
    instructions = fields.Text()
    sequence = fields.Integer(default=10)
    mode = fields.Selection(
        [
            ("info_only", "Info Only"),
            ("actionable", "Actionable"),
        ],
        default="info_only",
        required=True,
    )
    tool_binding_ids = fields.One2many(
        "openclaw.ai.topic.tool",
        "topic_id",
        string="Tool Bindings",
    )


class OpenClawAiTool(models.Model):
    _name = "openclaw.ai.tool"
    _description = "OpenClaw AI Tool"

    name = fields.Char(required=True)
    key = fields.Char(required=True)
    active = fields.Boolean(default=True)
    execution_kind = fields.Selection(
        [
            ("read", "Read"),
            ("write", "Write"),
            ("custom", "Custom"),
        ],
        default="read",
        required=True,
    )
    gateway_name = fields.Char()
    required_policy_action = fields.Selection(
        [
            ("db_read", "DB Read"),
            ("db_write", "DB Write"),
            ("odoo_read", "Odoo Read"),
            ("odoo_write", "Odoo Write"),
            ("docs_read", "Docs Read"),
            ("docs_write", "Docs Write"),
            ("web_search", "Web Search"),
            ("code_generation", "Code Generation"),
            ("shell_action", "Shell Action"),
        ],
        required=True,
        default="odoo_read",
    )
    risk_level = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        default="low",
        required=True,
    )
    schema_key = fields.Char()
    schema_version = fields.Integer(default=1, required=True)


class OpenClawAiTopicTool(models.Model):
    _name = "openclaw.ai.topic.tool"
    _description = "OpenClaw AI Topic Tool Binding"
    _order = "sequence, id"

    topic_id = fields.Many2one(
        "openclaw.ai.topic",
        required=True,
        ondelete="cascade",
    )
    tool_id = fields.Many2one(
        "openclaw.ai.tool",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    required = fields.Boolean(default=False)
    tool_instructions = fields.Text()
    parameter_hints_json = fields.Text()
