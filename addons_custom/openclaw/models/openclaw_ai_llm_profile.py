from odoo import fields, models


class OpenClawAiLlmProfile(models.Model):
    _name = "openclaw.ai.llm_profile"
    _description = "OpenClaw AI LLM Profile"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    backend = fields.Selection(
        [
            ("openrouter", "OpenRouter"),
        ],
        default="openrouter",
        required=True,
    )
    model_name = fields.Char(required=True)
    fallback_model_name = fields.Char()
    temperature = fields.Float(default=0.5)
    max_tokens = fields.Integer(default=800)
    reasoning_enabled = fields.Boolean(default=True)
    supports_tools = fields.Boolean(default=False)
    supports_structured_output = fields.Boolean(default=True)
