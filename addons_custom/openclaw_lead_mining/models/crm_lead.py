from odoo import models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    def action_generate_leads(self):
        """Redirect the native IAP (paid) entry point to the free OpenClaw wizard."""
        return {
            "type": "ir.actions.act_window",
            "name": "OpenClaw Lead Mining",
            "res_model": "openclaw.lead.mining.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {},
        }
