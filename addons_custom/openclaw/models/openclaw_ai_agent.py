from odoo import fields, models


class OpenClawAiAgent(models.Model):
    _name = "openclaw.ai.agent"
    _description = "OpenClaw AI Agent"

    name = fields.Char(required=True)
    key = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text()
    system_prompt = fields.Text()
    response_style = fields.Selection(
        [
            ("concise", "Concise"),
            ("balanced", "Balanced"),
            ("detailed", "Detailed"),
        ],
        default="balanced",
        required=True,
    )
    restrict_to_sources = fields.Boolean(default=False)
    llm_profile_id = fields.Many2one("openclaw.ai.llm_profile", string="LLM Profile")
    topic_ids = fields.Many2many(
        "openclaw.ai.topic",
        "openclaw_ai_agent_topic_rel",
        "agent_id",
        "topic_id",
        string="Topics",
    )
    source_ids = fields.Many2many(
        "openclaw.ai.source",
        "openclaw_ai_agent_source_rel",
        "agent_id",
        "source_id",
        string="Sources",
    )
