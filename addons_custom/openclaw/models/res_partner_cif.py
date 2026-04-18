"""Autorelleno de res.partner al informar un VAT/CIF/NIF válido.

Flujo:
  - `@api.onchange('vat')` valida formato y consulta `cif-lookup-mcp` para
    traer razón social, dirección, CP, municipio, provincia, teléfono y web.
    Rellena sólo los campos vacíos del partner.
  - El logo NO se descarga en onchange (demasiado lento). Se descarga al
    guardar (`create` / `write`) si el partner está marcado como enriquecido
    y no tiene imagen.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_LOGO_MIN_BYTES = 400
_EMAIL_REJECT_PREFIXES = ("no-reply", "noreply", "postmaster@", "webmaster@", "abuse@")
_EMAIL_REJECT_SUFFIXES = (".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif")

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CIF_LOOKUP_URL_DEFAULT = "http://cif-lookup-mcp:8093/mcp"
_CIF_RE = re.compile(r"^[ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J]$")
_NIF_RE = re.compile(r"^\d{8}[A-Z]$")
_NIE_RE = re.compile(r"^[XYZ]\d{7}[A-Z]$")
_NIF_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"

# Prefijo código postal -> provincia española (nombres alineados a res.country.state de l10n_es)
_CP_PROVINCIA = {
    "01": "Álava", "02": "Albacete", "03": "Alicante", "04": "Almería",
    "05": "Ávila", "06": "Badajoz", "07": "Islas Baleares", "08": "Barcelona",
    "09": "Burgos", "10": "Cáceres", "11": "Cádiz", "12": "Castellón",
    "13": "Ciudad Real", "14": "Córdoba", "15": "La Coruña", "16": "Cuenca",
    "17": "Gerona", "18": "Granada", "19": "Guadalajara", "20": "Guipúzcoa",
    "21": "Huelva", "22": "Huesca", "23": "Jaén", "24": "León",
    "25": "Lérida", "26": "La Rioja", "27": "Lugo", "28": "Madrid",
    "29": "Málaga", "30": "Murcia", "31": "Navarra", "32": "Orense",
    "33": "Asturias", "34": "Palencia", "35": "Las Palmas", "36": "Pontevedra",
    "37": "Salamanca", "38": "Santa Cruz de Tenerife", "39": "Cantabria",
    "40": "Segovia", "41": "Sevilla", "42": "Soria", "43": "Tarragona",
    "44": "Teruel", "45": "Toledo", "46": "Valencia", "47": "Valladolid",
    "48": "Vizcaya", "49": "Zamora", "50": "Zaragoza", "51": "Ceuta",
    "52": "Melilla",
}

_PROVINCIA_ALIASES = {
    "Álava": ["Araba", "Álava"],
    "Guipúzcoa": ["Gipuzkoa", "Guipúzcoa"],
    "Vizcaya": ["Bizkaia", "Vizcaya"],
    "La Coruña": ["A Coruña", "La Coruña", "Coruña"],
    "Orense": ["Ourense", "Orense"],
    "Gerona": ["Girona", "Gerona"],
    "Lérida": ["Lleida", "Lérida"],
    "Islas Baleares": ["Illes Balears", "Baleares", "Islas Baleares"],
    "Castellón": ["Castelló", "Castellón"],
    "Valencia": ["València", "Valencia"],
    "Alicante": ["Alacant", "Alicante"],
}


def _normalize_vat(raw: str) -> str:
    if not raw:
        return ""
    cleaned = re.sub(r"[\s\-.]", "", raw).upper()
    if len(cleaned) > 2 and cleaned[:2] == "ES" and cleaned[:2].isalpha():
        cleaned = cleaned[2:]
    return cleaned


def _is_spanish_doc(doc: str) -> bool:
    if not doc:
        return False
    if _CIF_RE.match(doc):
        return True
    if _NIF_RE.match(doc):
        idx = int(doc[:8]) % 23
        return doc[8] == _NIF_LETTERS[idx]
    if _NIE_RE.match(doc):
        prefix_map = {"X": "0", "Y": "1", "Z": "2"}
        num = prefix_map[doc[0]] + doc[1:8]
        idx = int(num) % 23
        return doc[8] == _NIF_LETTERS[idx]
    return False


def _http_post_json(url: str, payload: dict, timeout: float, auth_token: str = "") -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    if auth_token:
        req.add_header("Authorization", f"Bearer {auth_token}")
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _http_get_bytes(url: str, timeout: float = 6.0, max_bytes: int = 2 * 1024 * 1024) -> bytes | None:
    try:
        req = Request(url, method="GET")
        req.add_header("User-Agent", "Mozilla/5.0 OpenClaw-Odoo")
        with urlopen(req, timeout=timeout) as resp:
            content = resp.read(max_bytes + 1)
            if len(content) > max_bytes:
                return None
            return content
    except (URLError, HTTPError, TimeoutError, ValueError, OSError):
        return None


def _extract_tool_content(rpc_result: dict) -> dict:
    if not isinstance(rpc_result, dict):
        return {}
    if rpc_result.get("error"):
        return {"error": True, "mensaje": str(rpc_result["error"].get("message", "error"))}
    inner = rpc_result.get("result") or {}
    content_items = inner.get("content") or []
    for item in content_items:
        if isinstance(item, dict) and item.get("type") == "text":
            try:
                return json.loads(item.get("text") or "{}")
            except json.JSONDecodeError:
                return {}
    return {}


class ResPartnerCifAutofill(models.Model):
    _inherit = "res.partner"

    openclaw_cif_enriched = fields.Boolean(
        string="Datos enriquecidos por OpenClaw",
        readonly=True,
        copy=False,
    )

    def _openclaw_lookup_url(self) -> str:
        ICP = self.env["ir.config_parameter"].sudo()
        return ICP.get_param("openclaw.cif_lookup_url", CIF_LOOKUP_URL_DEFAULT)

    def _openclaw_lookup_token(self) -> str:
        ICP = self.env["ir.config_parameter"].sudo()
        token = ICP.get_param("openclaw.cif_lookup_token", "") or ""
        if not token:
            token = (
                os.environ.get("OPENCLAW_CIF_LOOKUP_MCP_TOKEN")
                or os.environ.get("CIF_LOOKUP_MCP_TOKEN")
                or ""
            )
        return token

    def _openclaw_cache_read(self, doc: str) -> dict | None:
        ICP = self.env["ir.config_parameter"].sudo()
        raw = ICP.get_param(f"openclaw.cif_cache.{doc}", "") or ""
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _openclaw_cache_write(self, doc: str, data: dict) -> None:
        if not data or data.get("error"):
            return
        try:
            payload = json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError):
            return
        if len(payload) > 32 * 1024:
            return
        self.env["ir.config_parameter"].sudo().set_param(
            f"openclaw.cif_cache.{doc}", payload,
        )

    def _openclaw_fetch_cif_data(self, doc: str) -> dict:
        cached = self._openclaw_cache_read(doc)
        if cached:
            return cached
        url = self._openclaw_lookup_url()
        token = self._openclaw_lookup_token()
        try:
            rpc = _http_post_json(
                url,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "cif.lookup",
                        "arguments": {"cif": doc, "include_partner_mapping": True},
                    },
                },
                timeout=20.0,
                auth_token=token,
            )
        except (URLError, HTTPError, TimeoutError, OSError) as exc:
            _logger.warning("[openclaw-cif] lookup failed for %s: %s", doc, exc)
            return {}
        data = _extract_tool_content(rpc)
        if data.get("error"):
            _logger.info("[openclaw-cif] lookup error for %s: %s", doc, data.get("mensaje"))
        else:
            self._openclaw_cache_write(doc, data)
        return data

    def _openclaw_resolve_country_state(self, data: dict) -> dict[str, Any]:
        res: dict[str, Any] = {}
        country = self.env["res.country"].search([("code", "=", "ES")], limit=1)
        if country:
            res["country_id"] = country.id
        state = False
        cp = (data.get("codigo_postal") or "").strip()
        if cp and len(cp) >= 2 and country:
            provincia = _CP_PROVINCIA.get(cp[:2])
            if provincia:
                candidates = _PROVINCIA_ALIASES.get(provincia, [provincia])
                for candidate in candidates:
                    state = self.env["res.country.state"].search(
                        [("country_id", "=", country.id), ("name", "=ilike", candidate)],
                        limit=1,
                    )
                    if state:
                        break
                if not state:
                    for candidate in candidates:
                        state = self.env["res.country.state"].search(
                            [("country_id", "=", country.id), ("name", "ilike", candidate)],
                            limit=1,
                        )
                        if state:
                            break
        if not state:
            ccaa = (data.get("comunidad_autonoma") or "").strip()
            if ccaa and country:
                state = self.env["res.country.state"].search(
                    [("country_id", "=", country.id), ("name", "ilike", ccaa)], limit=1,
                )
        if state:
            res["state_id"] = state.id
        return res

    def _openclaw_guess_domains(self, name: str) -> list[str]:
        if not name:
            return []
        base = re.sub(r"[^a-z0-9]+", "", name.lower())
        if not base:
            return []
        short = base[:20]
        return [f"{short}.es", f"{short}.com", f"{short}.net"]

    def _openclaw_fetch_logo_for_domain(self, domain: str) -> bytes | None:
        if not domain:
            return None
        for candidate in (
            f"https://{domain}/favicon.ico",
            f"https://icons.duckduckgo.com/ip3/{domain}.ico",
            f"https://www.google.com/s2/favicons?sz=128&domain={domain}",
        ):
            blob = _http_get_bytes(candidate, timeout=5.0)
            if blob and len(blob) > _LOGO_MIN_BYTES:
                return blob
        return None

    def _openclaw_try_fetch_logo(self, website: str) -> tuple[bytes | None, str]:
        """Devuelve (logo_bytes, dominio_usado)."""
        if not website:
            return None, ""
        parsed = urlparse(website if "://" in website else f"https://{website}")
        domain = parsed.netloc or parsed.path
        domain = domain.split("/")[0].strip()
        if not domain:
            return None, ""
        blob = self._openclaw_fetch_logo_for_domain(domain)
        return (blob, domain) if blob else (None, "")

    def _openclaw_fetch_homepage(self, website: str) -> tuple[str, str]:
        """Descarga la home; devuelve (html, url_final). Cadenas vacías si falla."""
        if not website:
            return "", ""
        url = website if "://" in website else f"https://{website}"
        try:
            req = Request(url, method="GET")
            req.add_header("User-Agent", "Mozilla/5.0 OpenClaw-Odoo")
            req.add_header("Accept", "text/html,application/xhtml+xml")
            with urlopen(req, timeout=6) as resp:
                raw = resp.read(512 * 1024)
                final_url = resp.geturl()
            return raw.decode("utf-8", errors="replace"), final_url
        except (URLError, HTTPError, TimeoutError, ValueError, OSError) as exc:
            _logger.info("[openclaw-cif] homepage fetch failed for %s: %s", website, exc)
            return "", ""

    def _openclaw_find_email_in_html(self, html: str) -> str:
        if not html:
            return ""
        m = re.search(r'mailto:([^"\'>\s?#]+)', html, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().lower()
            if _EMAIL_RE.fullmatch(candidate) and not candidate.startswith(_EMAIL_REJECT_PREFIXES):
                return candidate
        for match in _EMAIL_RE.finditer(html):
            candidate = match.group(0).lower()
            if candidate.startswith(_EMAIL_REJECT_PREFIXES):
                continue
            if any(candidate.endswith(ext) for ext in _EMAIL_REJECT_SUFFIXES):
                continue
            return candidate
        return ""

    def _openclaw_find_logo_url_in_html(self, html: str, base_url: str) -> str:
        if not html:
            return ""
        patterns = (
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<link[^>]+rel=["\'][^"\']*apple-touch-icon[^"\']*["\'][^>]+href=["\']([^"\']+)["\']',
            r'<link[^>]+rel=["\'](?:shortcut icon|icon)["\'][^>]+href=["\']([^"\']+)["\']',
        )
        for pattern in patterns:
            m = re.search(pattern, html, re.IGNORECASE)
            if m:
                return urljoin(base_url or "", m.group(1).strip())
        return ""

    def _openclaw_apply_cif_onchange(self, partner, data: dict) -> list[str]:
        """Aplica los datos del CIF a un partner in-memory (onchange). No logo."""
        if not data or data.get("error"):
            return []

        partner_mapping = data.get("_res_partner") or {}
        mapped_values = partner_mapping.get("values") or {}

        applied: list[str] = []

        def _is_empty(value: Any) -> bool:
            return value in (False, None, "", 0)

        def _set(field_name: str, value: Any) -> None:
            if not value:
                return
            if field_name not in partner._fields:
                return
            if not _is_empty(partner[field_name]):
                return
            setattr(partner, field_name, value)
            applied.append(field_name)

        _set("name", mapped_values.get("name") or data.get("razon_social"))
        _set("street", mapped_values.get("street") or data.get("direccion"))
        _set("zip", mapped_values.get("zip") or data.get("codigo_postal"))
        _set("city", mapped_values.get("city") or data.get("municipio"))
        _set("phone", mapped_values.get("phone") or data.get("telefono"))
        _set("website", mapped_values.get("website") or data.get("website"))
        _set("email", mapped_values.get("email") or data.get("email"))

        if _is_empty(partner.is_company):
            partner.is_company = True
            applied.append("is_company")
        if not partner.company_type or partner.company_type == "person":
            partner.company_type = "company"
            applied.append("company_type")

        country_state = self._openclaw_resolve_country_state(data)
        if country_state.get("country_id") and not partner.country_id:
            partner.country_id = country_state["country_id"]
            applied.append("country_id")
        if country_state.get("state_id") and not partner.state_id:
            partner.state_id = country_state["state_id"]
            applied.append("state_id")

        if applied:
            partner.openclaw_cif_enriched = True

        return applied

    def action_openclaw_cif_lookup(self):
        self.ensure_one()
        raw_vat = (self.vat or "").strip()
        if not raw_vat:
            raise UserError(_("Introduce un CIF/NIF/NIE en el campo NIF antes de buscar."))
        doc = _normalize_vat(raw_vat)
        if not _is_spanish_doc(doc):
            raise UserError(_("El documento no tiene formato válido de CIF/NIF/NIE español."))
        data = self._openclaw_fetch_cif_data(doc)
        if not data:
            raise UserError(_("No se pudo contactar con el servicio de búsqueda. Verifica conectividad."))
        if data.get("error"):
            raise UserError(data.get("mensaje") or _("No se encontraron datos para el documento."))

        mapping = (data.get("_res_partner") or {}).get("values") or {}
        vals: dict[str, Any] = {}
        applied: list[str] = []

        def _maybe(field_name: str, value: Any) -> None:
            if not value or field_name not in self._fields:
                return
            if self[field_name] not in (False, None, "", 0):
                return
            vals[field_name] = value
            applied.append(field_name)

        _maybe("name", mapping.get("name") or data.get("razon_social"))
        _maybe("street", mapping.get("street") or data.get("direccion"))
        _maybe("zip", mapping.get("zip") or data.get("codigo_postal"))
        _maybe("city", mapping.get("city") or data.get("municipio"))
        _maybe("phone", mapping.get("phone") or data.get("telefono"))
        _maybe("website", mapping.get("website") or data.get("website"))
        _maybe("email", mapping.get("email") or data.get("email"))

        if not self.is_company:
            vals["is_company"] = True
            applied.append("is_company")
        if not self.company_type or self.company_type == "person":
            vals["company_type"] = "company"
            applied.append("company_type")

        country_state = self._openclaw_resolve_country_state(data)
        if country_state.get("country_id") and not self.country_id:
            vals["country_id"] = country_state["country_id"]
            applied.append("country_id")
        if country_state.get("state_id") and not self.state_id:
            vals["state_id"] = country_state["state_id"]
            applied.append("state_id")

        if vals:
            vals["openclaw_cif_enriched"] = True
            self.write(vals)

        try:
            self._openclaw_maybe_fetch_logo()
        except Exception:
            _logger.exception("[openclaw-cif] logo/email fetch failed for %s", doc)

        _logger.info("[openclaw-cif] button lookup for %s applied: %s", doc, applied)

        message = (
            _("Datos actualizados desde %s: %s") % (data.get("fuente") or "-", ", ".join(applied))
            if applied
            else _("No había campos vacíos por rellenar.")
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OpenClaw"),
                "message": message,
                "type": "success" if applied else "info",
                "sticky": False,
            },
        }

    def _openclaw_maybe_fetch_logo(self) -> None:
        for partner in self:
            if not partner.openclaw_cif_enriched:
                continue
            need_logo = not partner.image_1920
            need_email = not partner.email
            if not need_logo and not need_email:
                continue

            website = partner.website or ""
            resolved_domain = ""
            if not website and partner.name:
                for guessed in self._openclaw_guess_domains(partner.name):
                    if _http_get_bytes(f"https://{guessed}/favicon.ico", timeout=4.0):
                        website = f"https://{guessed}"
                        resolved_domain = guessed
                        break

            html, final_url = self._openclaw_fetch_homepage(website)
            base_url = final_url or website

            if need_email and html:
                email = self._openclaw_find_email_in_html(html)
                if email:
                    partner.email = email
                    _logger.info("[openclaw-cif] email found on %s: %s", base_url, email)

            if need_logo:
                logo_bytes: bytes | None = None
                if html:
                    logo_url = self._openclaw_find_logo_url_in_html(html, base_url)
                    if logo_url:
                        logo_bytes = _http_get_bytes(logo_url, timeout=6.0)
                if not logo_bytes and website:
                    logo_bytes, dom = self._openclaw_try_fetch_logo(website)
                    resolved_domain = resolved_domain or dom
                if logo_bytes and len(logo_bytes) > _LOGO_MIN_BYTES:
                    partner.image_1920 = base64.b64encode(logo_bytes)
                    _logger.info("[openclaw-cif] logo set for %s (%d bytes)", base_url, len(logo_bytes))
                    if resolved_domain and not partner.website:
                        partner.website = f"https://{resolved_domain}"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        try:
            records._openclaw_maybe_fetch_logo()
        except Exception:
            _logger.exception("[openclaw-cif] logo fetch (create) failed")
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ("website", "openclaw_cif_enriched", "name", "vat")):
            try:
                self._openclaw_maybe_fetch_logo()
            except Exception:
                _logger.exception("[openclaw-cif] logo fetch (write) failed")
        return res
