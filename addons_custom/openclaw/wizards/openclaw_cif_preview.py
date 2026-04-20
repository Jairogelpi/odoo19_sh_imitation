from __future__ import annotations

import base64
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class OpenClawCifPreview(models.TransientModel):
    _name = "openclaw.cif.preview"
    _description = "Previsualización de datos de CIF antes de aplicar al partner"

    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    source = fields.Char(string="Fuente", readonly=True)
    vat_display = fields.Char(string="CIF/NIF", readonly=True)

    name = fields.Char(string="Razón social")
    street = fields.Char(string="Dirección")
    zip = fields.Char(string="Código postal")
    city = fields.Char(string="Municipio")
    state_id = fields.Many2one("res.country.state", string="Provincia")
    country_id = fields.Many2one("res.country", string="País")
    phone = fields.Char(string="Teléfono")
    website = fields.Char(string="Sitio web")
    email = fields.Char(string="Email")

    logo_preview = fields.Binary(string="Logo", attachment=False)
    logo_source_url = fields.Char(string="Origen del logo", readonly=True)

    def action_apply(self):
        self.ensure_one()
        partner = self.partner_id
        if not partner:
            return {"type": "ir.actions.act_window_close"}

        vals = {}

        def _set(field_name, value):
            if not value:
                return
            if field_name not in partner._fields:
                return
            vals[field_name] = value

        _set("name", self.name)
        _set("street", self.street)
        _set("zip", self.zip)
        _set("city", self.city)
        _set("phone", self.phone)
        _set("website", self.website)
        _set("email", self.email)
        if self.country_id:
            vals["country_id"] = self.country_id.id
        if self.state_id:
            vals["state_id"] = self.state_id.id
        vals["is_company"] = True
        vals["company_type"] = "company"

        if self.logo_preview:
            vals["image_1920"] = self.logo_preview

        if vals:
            vals["openclaw_cif_enriched"] = True
            partner.write(vals)

        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }
