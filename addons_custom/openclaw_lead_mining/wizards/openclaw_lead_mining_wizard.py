from __future__ import annotations

import json
import logging
import os
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_EMAIL_REJECT_PREFIXES = ("no-reply", "noreply", "postmaster@", "webmaster@", "abuse@")
_EMAIL_REJECT_SUFFIXES = (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif")

LEAD_MINING_URL_DEFAULT = "http://lead-mining-mcp:8094/mcp"


def _mcp_rpc(url: str, method: str, params: dict | None, token: str, timeout: float) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        payload["params"] = params
    req = Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw) if raw else {}


def _extract_tool_result(rpc: dict) -> dict:
    if not isinstance(rpc, dict) or rpc.get("error"):
        return {"error": True, "mensaje": (rpc.get("error") or {}).get("message", "RPC error")}
    result = rpc.get("result") or {}
    for item in result.get("content") or []:
        if isinstance(item, dict) and item.get("type") == "text":
            try:
                return json.loads(item.get("text") or "{}")
            except json.JSONDecodeError:
                return {}
    return {}


def _scrape_email(website: str, timeout: float = 6.0) -> str:
    if not website:
        return ""
    url = website if "://" in website else f"https://{website}"
    try:
        req = Request(url, method="GET")
        req.add_header("User-Agent", "Mozilla/5.0 OpenClawLeadMining")
        req.add_header("Accept", "text/html,application/xhtml+xml")
        with urlopen(req, timeout=timeout) as resp:
            html = resp.read(512 * 1024).decode("utf-8", errors="replace")
    except (URLError, HTTPError, TimeoutError, ValueError, OSError):
        return ""
    m = re.search(r'mailto:([^"\'>\s?#]+)', html, re.IGNORECASE)
    if m:
        cand = m.group(1).strip().lower()
        if _EMAIL_RE.fullmatch(cand) and not cand.startswith(_EMAIL_REJECT_PREFIXES):
            return cand
    for match in _EMAIL_RE.finditer(html):
        cand = match.group(0).lower()
        if cand.startswith(_EMAIL_REJECT_PREFIXES):
            continue
        if any(cand.endswith(ext) for ext in _EMAIL_REJECT_SUFFIXES):
            continue
        return cand
    return ""


class OpenClawLeadMiningWizard(models.TransientModel):
    _name = "openclaw.lead.mining.wizard"
    _description = "Buscar leads en OpenStreetMap y crearlos como crm.lead"

    category = fields.Selection(
        selection="_category_selection",
        string="Sector",
        required=True,
        default="restaurant",
    )
    country_id = fields.Many2one(
        "res.country",
        string="País",
        default=lambda self: self.env.ref("base.es", raise_if_not_found=False),
    )
    state_id = fields.Many2one(
        "res.country.state",
        string="Provincia",
        domain="[('country_id', '=?', country_id)]",
        help="Provincia (igual que state_id en res.partner).",
    )
    city = fields.Char(
        string="Ciudad",
        help="Ciudad/municipio (igual que city en res.partner). Si se rellena, se usa como zona.",
    )
    area_name = fields.Char(
        string="Zona (nombre administrativo)",
        compute="_compute_area_name",
        store=True,
        readonly=False,
        help="Se calcula desde ciudad o provincia. Editable si quieres otro nombre OSM.",
    )

    @api.depends("state_id", "city")
    def _compute_area_name(self):
        for rec in self:
            if rec.city:
                rec.area_name = rec.city
            elif rec.state_id:
                rec.area_name = rec.state_id.name
            elif not rec.area_name:
                rec.area_name = "Madrid"
    require_website = fields.Boolean(string="Sólo con web", default=True)
    require_phone = fields.Boolean(string="Sólo con teléfono", default=True)
    limit = fields.Integer(string="Máximo de leads", default=30)
    enrich_email = fields.Boolean(
        string="Scrapear email del home si falta",
        default=True,
        help="Si el resultado no trae email, openclaw descarga la home y busca mailto:/regex.",
    )
    create_partner = fields.Boolean(
        string="Crear también contacto empresa",
        default=False,
        help=(
            "Por cada lead creará un res.partner (is_company=True) y lo enlazará vía partner_id. "
            "Reaprovecha el enricher de openclaw para capturar logo desde el home. "
            "El botón 'Buscar CIF' queda listo en el partner para cuando tengas el CIF."
        ),
    )

    sales_team_id = fields.Many2one("crm.team", string="Equipo de ventas")
    user_id = fields.Many2one("res.users", string="Vendedor", default=lambda self: self.env.user)
    tag_ids = fields.Many2many("crm.tag", string="Etiquetas")

    state = fields.Selection(
        [("filters", "Filtros"), ("preview", "Resultados"), ("done", "Creados")],
        default="filters",
    )
    result_line_ids = fields.One2many(
        "openclaw.lead.mining.result", "wizard_id", string="Resultados",
    )
    created_count = fields.Integer(readonly=True)

    @api.model
    def _category_selection(self):
        # Curated subset; the MCP supports more via lead.categories.
        return [
            ("restaurant", "Restaurante"),
            ("cafe", "Cafetería"),
            ("bar", "Bar"),
            ("hotel", "Hotel"),
            ("office", "Oficina (genérica)"),
            ("lawyer", "Despacho de abogados"),
            ("accountant", "Asesoría / contable"),
            ("company", "Empresa (office=company)"),
            ("retail", "Comercio (shop=*)"),
            ("supermarket", "Supermercado"),
            ("clothes", "Ropa"),
            ("car", "Concesionario"),
            ("healthcare", "Clínica"),
            ("dentist", "Dentista"),
            ("gym", "Gimnasio"),
            ("real_estate", "Inmobiliaria"),
        ]

    def _mcp_url(self) -> str:
        ICP = self.env["ir.config_parameter"].sudo()
        return ICP.get_param("openclaw.lead_mining_url", LEAD_MINING_URL_DEFAULT)

    def _mcp_token(self) -> str:
        ICP = self.env["ir.config_parameter"].sudo()
        token = ICP.get_param("openclaw.lead_mining_token", "") or ""
        if not token:
            token = os.environ.get("OPENCLAW_LEAD_MINING_MCP_TOKEN", "") or ""
        return token

    def action_search(self):
        self.ensure_one()
        if not self.area_name:
            raise UserError(_("Indica un nombre de zona (ej.: Madrid)."))
        url = self._mcp_url()
        token = self._mcp_token()
        try:
            rpc = _mcp_rpc(
                url, "tools/call",
                {
                    "name": "lead.search",
                    "arguments": {
                        "category": self.category,
                        "area_name": self.area_name,
                        "require_website": self.require_website,
                        "require_phone": self.require_phone,
                        "limit": self.limit,
                    },
                },
                token=token,
                timeout=120.0,
            )
        except (URLError, HTTPError, TimeoutError, OSError) as exc:
            raise UserError(_("No se pudo contactar con lead-mining-mcp: %s") % exc) from exc

        data = _extract_tool_result(rpc)
        if data.get("error"):
            raise UserError(data.get("mensaje") or _("Error en la búsqueda."))

        self.result_line_ids.unlink()
        lines = []
        for lead in data.get("leads", []):
            lines.append((0, 0, {
                "selected": True,
                "osm_id": lead.get("osm_id") or "",
                "name": lead.get("name") or "",
                "phone": lead.get("phone") or "",
                "website": lead.get("website") or "",
                "email": lead.get("email") or "",
                "street": lead.get("street") or "",
                "zip": lead.get("zip") or "",
                "city": lead.get("city") or "",
                "country_code": lead.get("country_code") or "",
                "category_hint": lead.get("category_hint") or "",
            }))
        self.result_line_ids = lines
        self.state = "preview"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_create_leads(self):
        self.ensure_one()
        Lead = self.env["crm.lead"]
        Partner = self.env["res.partner"]
        Country = self.env["res.country"]
        created = 0
        country_cache: dict[str, int] = {}
        # The openclaw enricher lives on res.partner; we borrow it via an empty recordset.
        partner_template = Partner.browse()
        has_enricher = hasattr(partner_template, "_openclaw_enrich_website_email_logo")

        for line in self.result_line_ids.filtered(lambda r: r.selected):
            email = line.email
            logo_bytes: bytes | None = None
            if self.enrich_email and not email and line.website:
                try:
                    email = _scrape_email(line.website)
                except Exception:
                    _logger.exception("[lead-mining] email scrape failed for %s", line.website)

            country_id = False
            code = (line.country_code or "").upper()
            if code:
                if code in country_cache:
                    country_id = country_cache[code]
                else:
                    country = Country.search([("code", "=", code)], limit=1)
                    country_id = country.id if country else False
                    country_cache[code] = country_id

            partner_id = False
            if self.create_partner and line.name:
                if has_enricher and line.website:
                    try:
                        enriched = partner_template._openclaw_enrich_website_email_logo(line.website, email or "")
                        if not email and enriched.get("email"):
                            email = enriched["email"]
                        logo_bytes = enriched.get("logo_bytes") or None
                    except Exception:
                        _logger.exception("[lead-mining] openclaw enrich failed for %s", line.website)
                partner_vals = {
                    "name": line.name,
                    "is_company": True,
                    "company_type": "company",
                    "phone": line.phone or False,
                    "website": line.website or False,
                    "email": email or False,
                    "street": line.street or False,
                    "zip": line.zip or False,
                    "city": line.city or False,
                    "country_id": country_id or False,
                    "comment": (
                        f"Creado por OpenClaw Lead Mining desde OSM.\n"
                        f"OSM id: {line.osm_id}"
                    ),
                }
                if logo_bytes:
                    import base64
                    partner_vals["image_1920"] = base64.b64encode(logo_bytes)
                partner = Partner.create(partner_vals)
                partner_id = partner.id

            vals = {
                "name": f"[{self.category}] {line.name}" if line.name else _("Lead sin nombre"),
                "partner_id": partner_id or False,
                "partner_name": False if partner_id else (line.name or False),
                "contact_name": False,
                "phone": line.phone or False,
                "website": line.website or False,
                "email_from": email or False,
                "street": line.street or False,
                "zip": line.zip or False,
                "city": line.city or False,
                "country_id": country_id or False,
                "description": (
                    f"Generado por OpenClaw Lead Mining desde OSM.\n"
                    f"OSM id: {line.osm_id}\nCategoría OSM: {line.category_hint or '-'}"
                ),
                "type": "lead",
            }
            if self.sales_team_id:
                vals["team_id"] = self.sales_team_id.id
            if self.user_id:
                vals["user_id"] = self.user_id.id
            if self.tag_ids:
                vals["tag_ids"] = [(6, 0, self.tag_ids.ids)]
            Lead.create(vals)
            created += 1

        self.created_count = created
        self.state = "done"
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_open_leads(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Leads creados"),
            "res_model": "crm.lead",
            "view_mode": "list,form,kanban",
            "domain": [("description", "like", "OpenClaw Lead Mining")],
        }


class OpenClawLeadMiningResult(models.TransientModel):
    _name = "openclaw.lead.mining.result"
    _description = "Resultado de lead mining (previsualización)"

    wizard_id = fields.Many2one("openclaw.lead.mining.wizard", ondelete="cascade", required=True)
    selected = fields.Boolean(default=True)
    osm_id = fields.Char(readonly=True)
    name = fields.Char()
    phone = fields.Char()
    website = fields.Char()
    email = fields.Char()
    street = fields.Char()
    zip = fields.Char()
    city = fields.Char()
    country_code = fields.Char()
    category_hint = fields.Char()
