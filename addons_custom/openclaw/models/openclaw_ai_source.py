from odoo import fields, models


class OpenClawAiSource(models.Model):
    _name = "openclaw.ai.source"
    _description = "OpenClaw AI Source"

    name = fields.Char(required=True)
    key = fields.Char(required=True)
    active = fields.Boolean(default=True)
    source_type = fields.Selection(
        [
            ("url", "URL"),
            ("document", "Document"),
            ("knowledge", "Knowledge"),
            ("vault_note", "Vault Note"),
        ],
        default="knowledge",
        required=True,
    )
    uri = fields.Char()
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("ready", "Ready"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
    )
    last_indexed_at = fields.Datetime()
    index_ref = fields.Char()
    metadata_json = fields.Text()
