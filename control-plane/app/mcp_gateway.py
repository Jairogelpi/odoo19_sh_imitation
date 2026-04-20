from __future__ import annotations

import asyncio
import html
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from . import backups, db_manager, docs_browser
from .chat_runtime import (
    RuntimeBundleValidationError,
    build_runtime_chat_request,
    has_runtime_bundle,
)
from .config import settings
from .openrouter_client import OpenRouterClient, OpenRouterError
from .github_api import GitHubClient

log = logging.getLogger("control-plane.mcp")


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _json_text(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, indent=2)


def _tool_result(value: Any) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": _json_text(value)}],
        "isError": False,
    }


def _tool_error(message: str, data: Any | None = None) -> dict[str, Any]:
    payload = {"kind": "error", "message": message}
    if data is not None:
        payload["data"] = _json_safe(data)
    return {
        "content": [{"type": "text", "text": _json_text(payload)}],
        "isError": True,
    }


def _jsonrpc_error(request_id: Any, code: int, message: str, data: Any | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = _json_safe(data)
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


def _normalize_suggested_action(item: Any) -> Any:
    if not isinstance(item, dict):
        return item

    normalized = dict(item)
    raw_action_type = normalized.get("action_type")
    action_type = "" if raw_action_type is None else str(raw_action_type).strip()
    if action_type != "create_dashboard":
        return normalized

    payload = normalized.get("payload")
    payload_dict = dict(payload) if isinstance(payload, dict) else {}
    target_model = str(
        normalized.get("target_model")
        or payload_dict.get("model")
        or ""
    ).strip()
    if target_model and target_model != "dashboard.dashboard":
        return normalized

    payload_dict.setdefault("model", "dashboard.dashboard")
    payload_dict.setdefault("operation", "create")
    normalized["action_type"] = "odoo_write"
    normalized["target_model"] = "dashboard.dashboard"
    normalized["payload"] = payload_dict
    return normalized


def _parse_llm_envelope(raw_text: str) -> tuple[str, list[dict[str, Any]]]:
    """Parse an LLM response expected to be a JSON object with keys
    `reply` (string) and `suggested_actions` (list).

    Falls back to using the raw text as `reply` when JSON parsing fails
    or when the payload does not match the expected shape.
    """
    stripped = (raw_text or "").strip()
    if not stripped:
        return "", []
    try:
        decoded = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return stripped, []
    if not isinstance(decoded, dict):
        return stripped, []
    reply = decoded.get("reply", "")
    reply_str = "" if reply is None else str(reply)
    raw_actions = decoded.get("suggested_actions")
    actions = [_normalize_suggested_action(item) for item in raw_actions] if isinstance(raw_actions, list) else []
    return reply_str, actions


def _clean_entity_value(value: str) -> str:
    cleaned = (value or "").strip().strip('"\'`“”')
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" ,.;:")


def _extract_crm_entities(text: str) -> tuple[str | None, str | None]:
    raw = text or ""
    lower = raw.lower()

    opportunity_name: str | None = None
    client_name: str | None = None

    pair_match = re.search(
        r"(?P<opp>[^,.;\n]+?)\s+y\s+el\s+cliente\s+(?P<client>[^,.;\n]+)",
        lower,
    )
    if pair_match:
        opp_span = pair_match.span("opp")
        client_span = pair_match.span("client")
        opportunity_name = _clean_entity_value(raw[opp_span[0]:opp_span[1]])
        client_name = _clean_entity_value(raw[client_span[0]:client_span[1]])

    if not opportunity_name:
        for pattern in [
            r"oportunidad\s*(?:es|:)?\s*[\"“']?([^\"”'\n]+?)[\"”']?(?:\s+para|\s+del\s+cliente|\s+con\s+cliente|[\.,;]|$)",
            r"nombre\s+de\s+la\s+oportunidad\s*(?:es|:)?\s*[\"“']?([^\"”'\n\.,;]+)",
        ]:
            match = re.search(pattern, lower)
            if match:
                span = match.span(1)
                opportunity_name = _clean_entity_value(raw[span[0]:span[1]])
                break

    if not client_name:
        for pattern in [
            r"cliente\s*(?:es|:)?\s*[\"“']?([^\"”'\n\.,;]+)",
            r"para\s+([\"“']?[^\"”'\n\.,;]+)",
        ]:
            match = re.search(pattern, lower)
            if match:
                span = match.span(1)
                client_name = _clean_entity_value(raw[span[0]:span[1]])
                if client_name and client_name.lower().startswith("el cliente"):
                    client_name = _clean_entity_value(client_name[10:])
                break

    return opportunity_name or None, client_name or None


def _build_crm_create_values(opportunity_name: str, client_name: str) -> dict[str, Any]:
    values: dict[str, Any] = {
        "name": opportunity_name,
        "type": "opportunity",
        "partner_name": client_name,
    }
    return values


def _extract_crm_update_values(text: str) -> dict[str, Any]:
    raw = text or ""
    lower = raw.lower()
    values: dict[str, Any] = {}

    amount_match = re.search(
        r"(?:monto|importe|revenue|ingreso\s+estimado|expected\s+revenue)\s*(?:es|:|=)?\s*([0-9]+(?:[\.,][0-9]+)?)",
        lower,
    )
    if amount_match:
        amount_text = amount_match.group(1).replace(",", ".")
        try:
            values["expected_revenue"] = float(amount_text)
        except ValueError:
            pass

    priority_map = {
        "alta": "3",
        "high": "3",
        "media": "2",
        "normal": "2",
        "baja": "1",
        "low": "1",
    }
    for token, priority in priority_map.items():
        if f"prioridad {token}" in lower or f"priority {token}" in lower:
            values["priority"] = priority
            break

    desc_match = re.search(r"(?:descripcion|description)\s*(?:es|:)?\s*[\"“']?([^\"”'\n]+)", raw, flags=re.IGNORECASE)
    if desc_match:
        values["description"] = _clean_entity_value(desc_match.group(1))

    new_name_match = re.search(
        r"(?:nuevo\s+nombre|renombra(?:r)?\s+a|new\s+name)\s*[\"“']([^\"”']+)[\"”']",
        raw,
        flags=re.IGNORECASE,
    )
    if new_name_match:
        values["name"] = _clean_entity_value(new_name_match.group(1))

    return {k: v for k, v in values.items() if v not in (None, "")}


def _text_contains_any(text: str, phrases: list[str]) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in phrases)


def _truncate_before_keywords(text: str, keywords: list[str]) -> str:
    lowered = text.lower()
    cut_index = len(text)
    for keyword in keywords:
        position = lowered.find(keyword)
        if position != -1 and position < cut_index:
            cut_index = position
    return text[:cut_index].strip(" ,.;:-")


def _extract_contact_reference(text: str) -> dict[str, Any]:
    raw = text or ""
    id_match = re.search(r"(?:contacto|contact)\s*(?:id\s*)?#?\s*(\d+)", raw, flags=re.IGNORECASE)
    if id_match:
        return {"ids": [int(id_match.group(1))]}

    name_match = re.search(
        r"(?:contacto|contact)\s*(?:llamado|named|de)?\s*[:\-]?\s*([^,;\n]+)",
        raw,
        flags=re.IGNORECASE,
    )
    if name_match:
        name = _clean_entity_value(name_match.group(1))
        if name:
            return {"name": name}

    return {}


def _extract_contact_create_values(text: str) -> dict[str, Any]:
    raw = text or ""
    trimmed = re.sub(
        r"^(crear|nuevo|agregar|add)\s+(?:un\s+|una\s+)?(?:contacto|contact)\s*(?:llamado|named)?\s*[:\-]?\s*",
        "",
        raw,
        flags=re.IGNORECASE,
    )
    name = _truncate_before_keywords(
        trimmed,
        [" con ", " email", " correo", " tel", " phone", " país", " pais", " country", " ciudad", " city", " empresa", " company"],
    )

    email_match = re.search(r"(?:email|correo(?:\s+electr[oó]nico)?)\s*(?:es|:|=)?\s*([^\s,;]+)", raw, flags=re.IGNORECASE)
    phone_match = re.search(r"(?:tel[eé]fono|telefono|phone)\s*(?:es|:|=)?\s*([^,;\n]+)", raw, flags=re.IGNORECASE)
    country_match = re.search(r"(?:pa[ií]s|pais|country)\s*(?:es|:|=)?\s*([^,;\n]+)", raw, flags=re.IGNORECASE)
    city_match = re.search(r"(?:ciudad|city)\s*(?:es|:|=)?\s*([^,;\n]+)", raw, flags=re.IGNORECASE)
    company_hint = _text_contains_any(raw, [" empresa", " company", " sociedad", " corp", " s.a.", " s.l."])

    values: dict[str, Any] = {}
    if name:
        values["name"] = name
    if email_match:
        values["email"] = _clean_entity_value(email_match.group(1)).lower()
    if phone_match:
        values["phone"] = _clean_entity_value(phone_match.group(1))
    if country_match:
        values["country_id"] = _clean_entity_value(country_match.group(1))
    if city_match:
        values["city"] = _clean_entity_value(city_match.group(1))
    if company_hint:
        values["is_company"] = True
    return values


def _extract_contact_update_values(text: str) -> dict[str, Any]:
    raw = text or ""
    values: dict[str, Any] = {}

    email_match = re.search(r"(?:email|correo(?:\s+electr[oó]nico)?)\s*(?:es|:|=)?\s*([^\s,;]+)", raw, flags=re.IGNORECASE)
    phone_match = re.search(r"(?:tel[eé]fono|telefono|phone)\s*(?:es|:|=)?\s*([^,;\n]+)", raw, flags=re.IGNORECASE)
    country_match = re.search(r"(?:pa[ií]s|pais|country)\s*(?:es|:|=)?\s*([^,;\n]+)", raw, flags=re.IGNORECASE)
    city_match = re.search(r"(?:ciudad|city)\s*(?:es|:|=)?\s*([^,;\n]+)", raw, flags=re.IGNORECASE)
    name_match = re.search(r"(?:nombre|name)\s*(?:es|a|=|:)?\s*([^,;\n]+)", raw, flags=re.IGNORECASE)

    if email_match:
        values["email"] = _clean_entity_value(email_match.group(1)).lower()
    if phone_match:
        values["phone"] = _clean_entity_value(phone_match.group(1))
    if country_match:
        values["country_id"] = _clean_entity_value(country_match.group(1))
    if city_match:
        values["city"] = _clean_entity_value(city_match.group(1))
    if name_match:
        values["name"] = _clean_entity_value(name_match.group(1))

    return {k: v for k, v in values.items() if v not in (None, "")}


def _extract_search_query(text: str, keywords: list[str]) -> str:
    raw = text or ""
    lowered = raw.lower()
    for keyword in keywords:
        position = lowered.find(keyword)
        if position != -1:
            remainder = raw[position + len(keyword):]
            query = _truncate_before_keywords(
                remainder,
                [" con ", " email", " correo", " tel", " phone", " por ", " id ", " id:", " id=", " nombre", " name"],
            )
            if query:
                return query
    quoted = re.search(r"[\"'“”](.+?)[\"'“”]", raw)
    if quoted:
        return _clean_entity_value(quoted.group(1))
    return _clean_entity_value(raw)


def _extract_dashboard_name(text: str) -> str | None:
    raw = text or ""
    patterns = [
        r"dashboard\s*(?:llamado|llamado\s+como|named|name|nombre)?\s*[:=]?\s*[\"'“”]?([^\"'“”\n]+)",
        r"(?:nombre\s+del\s+dashboard|nombre\s+dashboard|dashboard\s+name)\s*(?:es|:|=)?\s*[\"'“”]?([^\"'“”\n]+)",
        r"crear\s+(?:un\s+)?dashboard\s+[\"'“”]([^\"'“”]+)[\"'“”]",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, flags=re.IGNORECASE)
        if match:
            candidate = _truncate_before_keywords(
                _clean_entity_value(match.group(1)),
                [
                    " para ",
                    " con ",
                    " de ",
                    " por ",
                    " en ",
                    " tipo ",
                    " objetivo",
                    " kpi",
                    " filtro",
                    " visual",
                ],
            )
            if candidate:
                return candidate
    return None


_DASHBOARD_CHART_TYPES: list[tuple[str, str]] = [
    ("kpi", "KPI"),
    ("tile", "Tile View"),
    ("bar_chart", "Bar Chart"),
    ("column_chart", "Column Chart"),
    ("doughnut_chart", "Doughnut Chart"),
    ("area_chart", "Area Chart"),
    ("funnel_chart", "Funnel Chart"),
    ("pyramid_chart", "Pyramid Chart"),
    ("line_chart", "Line Chart"),
    ("pie_chart", "Pie Chart"),
    ("radar_chart", "Radar Chart"),
    ("stackedcolumn_chart", "StackedColumn"),
    ("radial_chart", "Radial Chart"),
    ("scatter_chart", "Scatter Chart"),
    ("map_chart", "Map Chart"),
    ("meter_chart", "Meter Chart"),
    ("to_do", "To Do"),
    ("list", "List View"),
]


def _extract_dashboard_chart_type(text: str) -> str | None:
    lowered = (text or "").lower()
    aliases: dict[str, str] = {
        "kpi": "kpi",
        "tile": "tile",
        "bar": "bar_chart",
        "bar chart": "bar_chart",
        "column": "column_chart",
        "doughnut": "doughnut_chart",
        "donut": "doughnut_chart",
        "area": "area_chart",
        "funnel": "funnel_chart",
        "embudo": "funnel_chart",
        "pyramid": "pyramid_chart",
        "piramide": "pyramid_chart",
        "line": "line_chart",
        "línea": "line_chart",
        "linea": "line_chart",
        "pie": "pie_chart",
        "radar": "radar_chart",
        "stacked": "stackedcolumn_chart",
        "stackedcolumn": "stackedcolumn_chart",
        "radial": "radial_chart",
        "scatter": "scatter_chart",
        "map": "map_chart",
        "mapa": "map_chart",
        "meter": "meter_chart",
        "gauge": "meter_chart",
        "to do": "to_do",
        "todo": "to_do",
        "list": "list",
        "tabla": "list",
    }
    for token, code in aliases.items():
        if token in lowered:
            return code
    for code, _label in _DASHBOARD_CHART_TYPES:
        if code in lowered:
            return code
    return None


def _extract_dashboard_model(text: str) -> str | None:
    raw = text or ""
    direct = re.search(r"\b([a-z_]+\.[a-z_]+)\b", raw)
    if direct:
        return direct.group(1)
    model_hint = re.search(
        r"(?:modelo|model)\s*(?:de\s+datos|datos|odoo)?\s*(?:es|:|=)?\s*([a-z_]+\.[a-z_]+)",
        raw,
        flags=re.IGNORECASE,
    )
    if model_hint:
        return model_hint.group(1)
    return None


def _extract_dashboard_fields(text: str) -> list[str]:
    raw = text or ""
    capture = re.search(
        r"(?:datos|campos|metricas|m[eé]tricas|kpis?)\s*(?:a\s+sacar|que\s+queremos\s+sacar|:|=|son)?\s*([^.;\n]+)",
        raw,
        flags=re.IGNORECASE,
    )
    if not capture:
        return []
    chunk = capture.group(1)
    parts = [p.strip(" .;") for p in re.split(r",|\sy\s", chunk) if p.strip()]
    return parts[:8]


def _extract_dashboard_representation(text: str) -> str | None:
    raw = text or ""
    match = re.search(
        r"(?:representar|representa|representaci[oó]n|objetivo)\s*(?:es|:|=)?\s*([^.;\n]+)",
        raw,
        flags=re.IGNORECASE,
    )
    if match:
        return _clean_entity_value(match.group(1))
    return None


def _recent_user_messages(messages: list[dict[str, str]], limit: int = 5) -> list[str]:
    user_messages: list[str] = []
    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = str(message.get("content") or "").strip()
        if content:
            user_messages.append(content)
    return user_messages[-limit:]


def _dashboard_delegation_requested(text: str) -> bool:
    lowered = (text or "").lower()
    phrases = [
        "hazlo tu",
        "hazlo tú",
        "lo que tu quieras",
        "lo que tú quieras",
        "como tu quieras",
        "como tú quieras",
        "tu decide",
        "tú decide",
        "elige tu",
        "elige tú",
        "you choose",
        "do what you think",
        "use your judgement",
    ]
    return any(phrase in lowered for phrase in phrases)


def _dashboard_confirmation_requested(text: str) -> bool:
    lowered = " ".join((text or "").lower().split())
    if not lowered or _dashboard_delegation_requested(lowered):
        return False
    if lowered in {"si", "sí", "hazlo", "adelante", "procede", "dale", "vale", "ok"}:
        return True
    phrases = [
        "si hazlo",
        "sí hazlo",
        "si, hazlo",
        "sí, hazlo",
        "si adelante",
        "sí adelante",
        "vale hazlo",
        "ok hazlo",
    ]
    return any(phrase in lowered for phrase in phrases)


def _dashboard_sales_context(text: str) -> bool:
    lowered = (text or "").lower()
    tokens = [
        "ventas",
        "sale.order",
        "sales module",
        "modulo de ventas",
        "módulo de ventas",
        "pedido de venta",
        "pedidos de venta",
    ]
    return any(token in lowered for token in tokens)


def _dashboard_record_count_requested(text: str) -> bool:
    lowered = (text or "").lower()
    tokens = [
        "numero de registros",
        "número de registros",
        "number of records",
        "count of records",
        "conteo de registros",
        "contar registros",
    ]
    return any(token in lowered for token in tokens)


def _apply_dashboard_safe_defaults(
    *,
    text: str,
    dashboard_name: str | None,
    chart_type: str | None,
    model_name: str | None,
    requested_fields: list[str],
    representation_goal: str | None,
    allow_defaults: bool,
) -> tuple[str | None, str | None, str | None, list[str], str | None, list[str]]:
    if not allow_defaults:
        return dashboard_name, chart_type, model_name, requested_fields, representation_goal, []

    defaults_used: list[str] = []
    normalized_name = (dashboard_name or "").strip().lower()
    if dashboard_name and (
        _dashboard_delegation_requested(dashboard_name)
        or normalized_name in {"ventas", "de ventas"}
    ):
        dashboard_name = None

    if _dashboard_sales_context(text):
        if not dashboard_name:
            dashboard_name = "Ventas - Registros"
            defaults_used.append("nombre=Ventas - Registros")
        if not chart_type:
            chart_type = "bar_chart"
            defaults_used.append("tipo=bar_chart")
        if not model_name:
            model_name = "sale.order"
            defaults_used.append("modelo=sale.order")
        if not requested_fields:
            requested_fields = ["state"]
            defaults_used.append("campos=state")
        if not representation_goal and (_dashboard_record_count_requested(text) or requested_fields == ["state"]):
            representation_goal = "Numero de registros de ventas por estado"
            defaults_used.append("representacion=Numero de registros de ventas por estado")
    return dashboard_name, chart_type, model_name, requested_fields, representation_goal, defaults_used


def _build_skill_taxonomy(policy_context: dict[str, Any] | None = None) -> dict[str, Any]:
    taxonomy = {
        "core": {
            "name": "openclaw-core",
            "scope": "policy, permissions, orchestration",
        },
        "router": {
            "name": "openclaw-router",
            "scope": "intent classification and skill dispatch",
        },
        "domains": [
            {
                "name": "openclaw-crm-contacts",
                "scope": "res.partner contact CRUD",
            },
            {
                "name": "openclaw-crm-opportunities",
                "scope": "crm.lead pipeline and opportunities",
            },
            {
                "name": "openclaw-sales",
                "scope": "sale.order quotations and orders",
            },
            {
                "name": "openclaw-inventory",
                "scope": "product and stock operations",
            },
            {
                "name": "openclaw-invoicing",
                "scope": "customer invoices, payments, and receivables",
            },
            {
                "name": "openclaw-purchase",
                "scope": "purchase orders, vendors, and procurement",
            },
            {
                "name": "openclaw-hr",
                "scope": "employees, leaves, payroll intents, and HR workflows",
            },
            {
                "name": "openclaw-reporting",
                "scope": "KPIs, analytics, dashboards, and business reports",
            },
            {
                "name": "openclaw-dashboard-chat",
                "scope": "chat-driven dashboard creation, edit, clone, and publish",
            },
            {
                "name": "openclaw-cif-lookup",
                "scope": "Spanish CIF enrichment and res.partner upsert via cif.validate/cif.lookup",
            },
            {
                "name": "openclaw-lead-mining",
                "scope": "OpenStreetMap-based free lead generation into crm.lead via lead.categories/lead.search",
            },
            {
                "name": "openclaw-odoo",
                "scope": "generic Odoo actions and approvals",
            },
        ],
    }
    if policy_context and isinstance(policy_context.get("skill_taxonomy"), dict):
        taxonomy.update(policy_context["skill_taxonomy"])
    return taxonomy


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


class WorkspaceStore:
    """Restricted read/write access to the workspace roots OpenClaw is allowed to touch."""

    def __init__(self) -> None:
        self.roots: dict[str, Path] = {
            "docs": Path(settings.docs_root).resolve(),
            "addons_custom": Path(settings.openclaw_addons_custom_root).resolve(),
        }

    def _root(self, root_name: str) -> Path:
        if root_name not in self.roots:
            raise ValueError(f"Unsupported root: {root_name}")
        return self.roots[root_name]

    def _resolve(self, root_name: str, relative_path: str = "") -> Path:
        root = self._root(root_name)
        target = (root / relative_path).resolve()
        if not str(target).startswith(str(root)):
            raise ValueError("Path escapes allowed root")
        return target

    @staticmethod
    def _is_hidden(path: Path) -> bool:
        return path.name.startswith(".") or path.name in {"__pycache__", "logs"}

    def list_tree(self, root_name: str, relative_path: str = "", max_depth: int = 3) -> dict[str, Any]:
        if root_name == "all":
            combined: list[dict[str, Any]] = []
            for current_root_name, root in self.roots.items():
                if not root.exists():
                    continue
                try:
                    combined.append(self.list_tree(current_root_name, relative_path, max_depth)["tree"])
                except FileNotFoundError:
                    continue
            return {
                "root": root_name,
                "path": relative_path,
                "tree": {
                    "name": "all",
                    "path": "",
                    "type": "dir",
                    "children": combined,
                },
            }

        target = self._resolve(root_name, relative_path)
        if not target.exists():
            raise FileNotFoundError(relative_path or root_name)

        def walk(path: Path, depth: int) -> dict[str, Any]:
            node = {
                "name": path.name or root_name,
                "path": str(path.relative_to(self._root(root_name))).replace("\\", "/") if path != self._root(root_name) else "",
                "type": "dir" if path.is_dir() else "file",
            }
            if path.is_file():
                try:
                    node["size"] = path.stat().st_size
                except OSError:
                    node["size"] = None
                return node
            if depth <= 0:
                node["children"] = []
                return node
            children: list[dict[str, Any]] = []
            for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if self._is_hidden(child):
                    continue
                if child.is_file() and child.suffix.lower() not in {".md", ".py", ".xml", ".json", ".yml", ".yaml", ".js", ".css", ".txt", ".sh", ".html"}:
                    continue
                children.append(walk(child, depth - 1))
            node["children"] = children
            return node

        defaults_summary = "; ".join(defaults_used)
        if recent_delegation and defaults_used and not last_confirmation:
            return {
                "reply": (
                    "Te enroutÃ© al skill openclaw-dashboard-chat. Como me delegaste la configuracion, "
                    "te propongo esta configuracion base antes de crear nada: "
                    f"{defaults_summary}. "
                    "Si te vale, responde 'si', 'hazlo' o 'adelante' y genero la accion aprobable."
                ),
                "suggested_actions": [],
            }

        rationale_suffix = f" Supuestos delegados usados: {defaults_summary}." if defaults_used else ""
        if recent_delegation and defaults_used and last_confirmation:
            reply_text = (
                "Perfecto. Prepare la accion de openclaw-dashboard-chat con estos supuestos revisables: "
                f"{defaults_summary}."
            )
        else:
            reply_text = (
                f"Perfecto. PreparÃ© la acciÃ³n de openclaw-dashboard-chat para crear el dashboard '{dashboard_name}' "
                "y dejarlo listo para confirmaciÃ³n en la UI."
            )

        return {
            "root": root_name,
            "path": relative_path,
            "tree": walk(target, max_depth),
        }

    def list_tree(self, root_name: str, relative_path: str = "", max_depth: int = 3) -> dict[str, Any]:
        if root_name == "all":
            combined: list[dict[str, Any]] = []
            for current_root_name, root in self.roots.items():
                if not root.exists():
                    continue
                try:
                    combined.append(self.list_tree(current_root_name, relative_path, max_depth)["tree"])
                except FileNotFoundError:
                    continue
            return {
                "root": root_name,
                "path": relative_path,
                "tree": {
                    "name": "all",
                    "path": "",
                    "type": "dir",
                    "children": combined,
                },
            }

        target = self._resolve(root_name, relative_path)
        if not target.exists():
            raise FileNotFoundError(relative_path or root_name)

        def walk(path: Path, depth: int) -> dict[str, Any]:
            node = {
                "name": path.name or root_name,
                "path": str(path.relative_to(self._root(root_name))).replace("\\", "/") if path != self._root(root_name) else "",
                "type": "dir" if path.is_dir() else "file",
            }
            if path.is_file():
                try:
                    node["size"] = path.stat().st_size
                except OSError:
                    node["size"] = None
                return node
            if depth <= 0:
                node["children"] = []
                return node
            children: list[dict[str, Any]] = []
            for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                if self._is_hidden(child):
                    continue
                if child.is_file() and child.suffix.lower() not in {".md", ".py", ".xml", ".json", ".yml", ".yaml", ".js", ".css", ".txt", ".sh", ".html"}:
                    continue
                children.append(walk(child, depth - 1))
            node["children"] = children
            return node

        return {
            "root": root_name,
            "path": relative_path,
            "tree": walk(target, max_depth),
        }

    def read_file(self, root_name: str, relative_path: str) -> dict[str, Any]:
        target = self._resolve(root_name, relative_path)
        if target.is_dir():
            candidate = target / "README.md"
            if candidate.exists():
                target = candidate
            else:
                return self.list_tree(root_name, relative_path)
        if not target.exists():
            raise FileNotFoundError(relative_path)
        content = target.read_text(encoding="utf-8")
        return {
            "root": root_name,
            "path": str(target.relative_to(self._root(root_name))).replace("\\", "/"),
            "content": content,
        }

    def write_file(self, root_name: str, relative_path: str, content: str, *, create_dirs: bool = True) -> dict[str, Any]:
        target = self._resolve(root_name, relative_path)
        if target.exists() and target.is_dir():
            raise ValueError("Cannot overwrite a directory with file content")
        if create_dirs:
            target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        return {
            "root": root_name,
            "path": str(target.relative_to(self._root(root_name))).replace("\\", "/"),
            "bytes_written": len(content.encode("utf-8")),
        }

    def search(self, root_name: str, query: str, max_results: int = 20) -> dict[str, Any]:
        roots = list(self.roots.items()) if root_name == "all" else [(root_name, self._root(root_name))]
        needle = query.lower().strip()
        if not needle:
            raise ValueError("Query cannot be empty")
        results: list[dict[str, Any]] = []
        for current_root_name, root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if len(results) >= max_results:
                    return {"root": root_name, "query": query, "results": results}
                if not path.is_file() or self._is_hidden(path):
                    continue
                if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz"}:
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for line_number, line in enumerate(text.splitlines(), start=1):
                    if needle in line.lower():
                        results.append(
                            {
                                "root": current_root_name,
                                "path": str(path.relative_to(root)).replace("\\", "/"),
                                "line": line_number,
                                "snippet": line.strip()[:240],
                            }
                        )
                        if len(results) >= max_results:
                            break
        return {"root": root_name, "query": query, "results": results}


class OpenClawMCPGateway:
    def __init__(self) -> None:
        self.workspace = WorkspaceStore()
        self.github = GitHubClient()
        self.openrouter = OpenRouterClient()
        self.protocol_version = "2024-11-05"
        self.server_info = {"name": "odoo19-control-plane", "version": "19.0.1.0.0"}
        self._tool_specs = self._build_tool_specs()

    def _build_tool_specs(self) -> list[ToolSpec]:
        object_schema = {"type": "object", "additionalProperties": True}
        return [
            ToolSpec(
                name="openclaw.execute_request",
                description="Validate and execute an OpenClaw request through the permission layer.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "request": object_schema,
                    },
                    "required": ["request"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="db.list_databases",
                description="List PostgreSQL databases managed by the local Odoo platform.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            ),
            ToolSpec(
                name="db.create_database",
                description="Create a new PostgreSQL database owned by the Odoo user.",
                input_schema={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="db.duplicate_database",
                description="Duplicate an existing PostgreSQL database using CREATE DATABASE ... WITH TEMPLATE.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "target": {"type": "string"},
                    },
                    "required": ["source", "target"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="db.drop_database",
                description="Drop a PostgreSQL database after confirming the exact name.",
                input_schema={
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "confirm": {"type": "string"}},
                    "required": ["name", "confirm"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="docs.read_markdown",
                description="Read a markdown file or docs folder from the Obsidian vault.",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="docs.write_markdown",
                description="Write or overwrite a markdown file in the Obsidian vault.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="docs.search",
                description="Search the docs vault by plain-text match.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 100},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="workspace.read_file",
                description="Read a file from the permitted workspace roots.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "root": {"type": "string", "enum": ["docs", "addons_custom"]},
                        "path": {"type": "string"},
                    },
                    "required": ["root", "path"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="workspace.write_file",
                description="Write a file under docs or addons_custom.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "root": {"type": "string", "enum": ["docs", "addons_custom"]},
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["root", "path", "content"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="workspace.list_tree",
                description="List a directory tree under docs or addons_custom.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "root": {"type": "string", "enum": ["docs", "addons_custom", "all"]},
                        "path": {"type": "string"},
                        "max_depth": {"type": "integer", "minimum": 0, "maximum": 8},
                    },
                    "required": ["root"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="workspace.search",
                description="Search docs or addons_custom by plain-text match.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "root": {"type": "string", "enum": ["docs", "addons_custom", "all"]},
                        "query": {"type": "string"},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 100},
                    },
                    "required": ["root", "query"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="web.search",
                description="Perform a simple web search using DuckDuckGo HTML results.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="github.list_workflows",
                description="List GitHub Actions workflows for the configured repository.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            ),
            ToolSpec(
                name="github.dispatch_workflow",
                description="Trigger a GitHub Actions workflow dispatch on a branch.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "integer"},
                        "ref": {"type": "string"},
                    },
                    "required": ["workflow_id", "ref"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="code.generate",
                description="Draft an agent plan or code changes using the configured OpenRouter model.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "instruction": {"type": "string"},
                        "context": {"type": "string"},
                        "target": {"type": "string"},
                    },
                    "required": ["instruction"],
                    "additionalProperties": True,
                },
            ),
            ToolSpec(
                name="obsidian.mcp_tools_list",
                description="List tools exposed by the configured external Obsidian MCP server.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            ),
            ToolSpec(
                name="obsidian.mcp_call",
                description="Call a specific tool on the configured external Obsidian MCP server.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string"},
                        "arguments": {"type": "object", "additionalProperties": True},
                    },
                    "required": ["tool_name"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="memory.mcp_tools_list",
                description="List tools exposed by the configured external Memory MCP server.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            ),
            ToolSpec(
                name="memory.mcp_call",
                description="Call a specific tool on the configured external Memory MCP server.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string"},
                        "arguments": {"type": "object", "additionalProperties": True},
                    },
                    "required": ["tool_name"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="context7.resolve_library_id",
                description="Resolve a Context7 library identifier for a framework or package name.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "library_name": {"type": "string"},
                        "query": {"type": "string"},
                    },
                    "required": ["library_name"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="context7.query_docs",
                description="Query Context7 docs using a resolved library identifier and a natural-language question.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "library_id": {"type": "string"},
                        "query": {"type": "string"},
                    },
                    "required": ["library_id", "query"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="context7.mcp_tools_list",
                description="List tools exposed by the configured external Context7 MCP server.",
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            ),
            ToolSpec(
                name="context7.mcp_call",
                description="Call a specific tool on the configured external Context7 MCP server.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "tool_name": {"type": "string"},
                        "arguments": {"type": "object", "additionalProperties": True},
                    },
                    "required": ["tool_name"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="cif.validate",
                description="Validate the format of a Spanish CIF (no network call).",
                input_schema={
                    "type": "object",
                    "properties": {"cif": {"type": "string"}},
                    "required": ["cif"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="cif.lookup",
                description=(
                    "Look up a Spanish company by CIF across public sources (infocif, infoempresa, axesor) "
                    "and optionally enrich phone/website with Google Maps. Set include_partner_mapping=true "
                    "to also receive a values dict ready for Odoo res.partner (to be submitted through the "
                    "OpenClaw permission pipeline)."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "cif": {"type": "string"},
                        "include_partner_mapping": {"type": "boolean"},
                    },
                    "required": ["cif"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="lead.categories",
                description="List supported OpenStreetMap business categories for free lead mining (use one as `category` in lead.search).",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="lead.search",
                description=(
                    "Search real businesses in OpenStreetMap by administrative area or bounding box and category. "
                    "Returns normalised leads (name, phone, website, email, address, lat/lon, OSM id) suitable for "
                    "bulk crm.lead creation. Pass area_name OR bbox; use require_website/require_phone to filter. "
                    "Downstream (OpenClaw wizard or skill) decides which ones to persist — the tool itself never writes to Odoo."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "One of lead.categories output (e.g. restaurant, hotel, lawyer)."},
                        "area_name": {"type": "string", "description": "Administrative area, e.g. 'Madrid', 'Valencia'."},
                        "bbox": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 4,
                            "maxItems": 4,
                            "description": "[south, west, north, east] in WGS84 degrees.",
                        },
                        "require_website": {"type": "boolean", "default": True},
                        "require_phone": {"type": "boolean", "default": True},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 50},
                    },
                    "required": ["category"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="chat.reply",
                description="Generate a conversational reply for the OpenClaw chat UI using the configured OpenRouter model.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "messages": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "role": {"type": "string", "enum": ["system", "user", "assistant"]},
                                    "content": {"type": "string"},
                                },
                                "required": ["role", "content"],
                                "additionalProperties": True,
                            },
                        },
                        "model": {"type": "string"},
                        "temperature": {"type": "number", "minimum": 0, "maximum": 2},
                        "max_tokens": {"type": "integer", "minimum": 1, "maximum": 4000},
                    },
                    "required": ["messages"],
                    "additionalProperties": False,
                },
            ),
            ToolSpec(
                name="shell.execute",
                description="Execute a shell command only when explicitly enabled by environment policy.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "cwd": {"type": "string"},
                    },
                    "required": ["command"],
                    "additionalProperties": True,
                },
            ),
        ]

    def _tool_index(self) -> dict[str, ToolSpec]:
        return {tool.name: tool for tool in self._tool_specs}

    def initialize(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "protocolVersion": self.protocol_version,
            "serverInfo": self.server_info,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"listChanged": False},
            },
            "instructions": "Call tools/list to discover tools, then tools/call to execute them.",
            "clientInfo": _json_safe((params or {}).get("clientInfo", {})),
        }

    def list_tools(self) -> dict[str, Any]:
        return {"tools": [{"name": tool.name, "description": tool.description, "inputSchema": tool.input_schema} for tool in self._tool_specs]}

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        arguments = arguments or {}
        handlers = {
            "openclaw.execute_request": self.tool_openclaw_execute_request,
            "db.list_databases": self.tool_db_list_databases,
            "db.create_database": self.tool_db_create_database,
            "db.duplicate_database": self.tool_db_duplicate_database,
            "db.drop_database": self.tool_db_drop_database,
            "docs.read_markdown": self.tool_docs_read_markdown,
            "docs.write_markdown": self.tool_docs_write_markdown,
            "docs.search": self.tool_docs_search,
            "workspace.read_file": self.tool_workspace_read_file,
            "workspace.write_file": self.tool_workspace_write_file,
            "workspace.list_tree": self.tool_workspace_list_tree,
            "workspace.search": self.tool_workspace_search,
            "web.search": self.tool_web_search,
            "github.list_workflows": self.tool_github_list_workflows,
            "github.dispatch_workflow": self.tool_github_dispatch_workflow,
            "code.generate": self.tool_code_generate,
            "obsidian.mcp_tools_list": self.tool_obsidian_mcp_tools_list,
            "obsidian.mcp_call": self.tool_obsidian_mcp_call,
            "memory.mcp_tools_list": self.tool_memory_mcp_tools_list,
            "memory.mcp_call": self.tool_memory_mcp_call,
            "context7.resolve_library_id": self.tool_context7_resolve_library_id,
            "context7.query_docs": self.tool_context7_query_docs,
            "context7.mcp_tools_list": self.tool_context7_mcp_tools_list,
            "context7.mcp_call": self.tool_context7_mcp_call,
            "cif.validate": self.tool_cif_validate,
            "cif.lookup": self.tool_cif_lookup,
            "lead.categories": self.tool_lead_categories,
            "lead.search": self.tool_lead_search,
            "chat.reply": self.tool_chat_reply,
            "shell.execute": self.tool_shell_execute,
        }
        if name not in handlers:
            raise ValueError(f"Unknown tool: {name}")
        result = handlers[name](arguments)
        if asyncio.iscoroutine(result):
            result = await result
        return _tool_result(result)

    async def handle_jsonrpc(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        method = payload.get("method")
        request_id = payload.get("id")
        params = payload.get("params") or {}

        if method is None:
            return _jsonrpc_error(request_id, -32600, "Invalid Request")

        if method == "initialize":
            if request_id is None:
                return None
            return {"jsonrpc": "2.0", "id": request_id, "result": self.initialize(params)}

        if method == "notifications/initialized":
            return None

        if method == "tools/list":
            if request_id is None:
                return None
            return {"jsonrpc": "2.0", "id": request_id, "result": self.list_tools()}

        if method == "tools/call":
            if request_id is None:
                return None
            tool_name = params.get("name")
            if not tool_name:
                return _jsonrpc_error(request_id, -32602, "Missing tool name")
            try:
                result = await self.call_tool(tool_name, params.get("arguments") or {})
            except ValueError as exc:
                return _jsonrpc_error(request_id, -32602, str(exc))
            except Exception as exc:  # pragma: no cover - defensive server side guard
                log.exception("Tool %s failed", tool_name)
                return _jsonrpc_error(request_id, -32000, "Tool execution failed", {"tool": tool_name, "error": str(exc)})
            return {"jsonrpc": "2.0", "id": request_id, "result": result}

        if request_id is None:
            return None
        return _jsonrpc_error(request_id, -32601, f"Unknown method: {method}")

    @staticmethod
    def _get_policy_allowlist(request: dict[str, Any]) -> set[str]:
        allowlist: set[str] = set()
        raw = request.get("tool_allowlist")
        if isinstance(raw, str):
            for line in raw.splitlines():
                cleaned = line.strip()
                if cleaned:
                    allowlist.add(cleaned)
        policy = request.get("policy") or {}
        if isinstance(policy, dict):
            raw_policy = policy.get("tool_allowlist")
            if isinstance(raw_policy, str):
                for line in raw_policy.splitlines():
                    cleaned = line.strip()
                    if cleaned:
                        allowlist.add(cleaned)
        return allowlist

    @staticmethod
    def _matches_allowlist(action: str, allowlist: set[str]) -> bool:
        if not allowlist:
            return False
        if action in allowlist:
            return True
        family = action.split(".", 1)[0]
        return f"{family}.read" in allowlist or f"{family}.write" in allowlist or f"{family}.*" in allowlist

    @staticmethod
    def _normalize_action_name(action: str) -> str:
        mapping = {
            "db_read": "db.read",
            "db_write": "db.write",
            "odoo_read": "odoo.read",
            "odoo_write": "odoo.write",
            "docs_read": "docs.read",
            "docs_write": "docs.write",
            "web_search": "web.search",
            "code_generation": "code.generate",
            "shell_action": "shell.execute",
        }
        return mapping.get(action, action)

    def _request_allowed(self, request: dict[str, Any], action: str) -> bool:
        action = self._normalize_action_name(action)
        allowlist = self._get_policy_allowlist(request)
        if self._matches_allowlist(action, allowlist):
            return True
        policy = request.get("policy") or {}
        if not isinstance(policy, dict):
            return False
        if action.startswith("db."):
            return bool(policy.get("allow_read_db") or policy.get("allow_write_db"))
        if action.startswith("docs."):
            if action.endswith("write_markdown"):
                return bool(policy.get("allow_write_docs") or policy.get("allow_workspace_write"))
            return bool(policy.get("allow_read_docs") or policy.get("allow_workspace_read"))
        if action.startswith("workspace."):
            if action.endswith("write_file"):
                return bool(policy.get("allow_workspace_write") or policy.get("allow_write_docs"))
            return bool(policy.get("allow_workspace_read") or policy.get("allow_read_docs"))
        if action == "web.search":
            return bool(policy.get("allow_web_search"))
        if action == "code.generate":
            return bool(policy.get("allow_code_generation"))
        if action == "shell.execute":
            return bool(policy.get("allow_shell_actions"))
        if action.startswith("github."):
            return True
        return False

    @staticmethod
    def _mcp_endpoint(base_url: str) -> str:
        url = (base_url or "").strip().rstrip("/")
        if not url:
            return ""
        if url.endswith("/mcp"):
            return url
        return f"{url}/mcp"

    async def _remote_mcp_request(
        self,
        *,
        base_url: str,
        token: str,
        timeout_seconds: int,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        endpoint = self._mcp_endpoint(base_url)
        if not endpoint:
            return {"kind": "rejected", "summary": "Remote MCP URL is not configured."}

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {},
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            return {
                "kind": "failed",
                "summary": f"Remote MCP request failed: {exc}",
                "endpoint": endpoint,
            }

        try:
            body = response.json()
        except ValueError:
            return {
                "kind": "failed",
                "summary": "Remote MCP response is not valid JSON.",
                "endpoint": endpoint,
            }

        if not isinstance(body, dict):
            return {
                "kind": "failed",
                "summary": "Remote MCP response has invalid shape.",
                "endpoint": endpoint,
                "response": _json_safe(body),
            }

        if isinstance(body.get("error"), dict):
            error = body["error"]
            return {
                "kind": "failed",
                "summary": f"Remote MCP error: {error.get('message') or 'unknown error'}",
                "endpoint": endpoint,
                "error": _json_safe(error),
            }

        result = body.get("result")
        if method == "tools/call":
            decoded = self._decode_mcp_result(result)
            if isinstance(decoded, dict):
                decoded.setdefault("kind", "completed")
                decoded.setdefault("endpoint", endpoint)
                return decoded
            return {
                "kind": "completed",
                "summary": "Remote MCP tool executed.",
                "endpoint": endpoint,
                "result": _json_safe(decoded),
            }

        if isinstance(result, dict):
            return {
                "kind": "completed",
                "summary": "Remote MCP request completed.",
                "endpoint": endpoint,
                **_json_safe(result),
            }

        return {
            "kind": "completed",
            "summary": "Remote MCP request completed.",
            "endpoint": endpoint,
            "result": _json_safe(result),
        }

    @staticmethod
    def _normalise_local_odoo_action(request: dict[str, Any]) -> dict[str, Any]:
        payload = request.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        operation = payload.get("operation")
        if not operation:
            operation = "search_read" if request.get("action_type") == "odoo_read" else "create"
        return {
            "model": payload.get("model") or request.get("target_model"),
            "operation": operation,
            "domain": payload.get("domain") or [],
            "fields": payload.get("fields"),
            "limit": payload.get("limit"),
            "ids": payload.get("ids") or payload.get("record_ids") or [],
            "values": payload.get("values") or {},
            "method": payload.get("method"),
            "args": payload.get("args") or [],
            "kwargs": payload.get("kwargs") or {},
            "target_ref": request.get("target_ref"),
        }

    async def tool_openclaw_execute_request(self, arguments: dict[str, Any]) -> dict[str, Any]:
        request = arguments.get("request") or {}
        if not isinstance(request, dict):
            raise ValueError("request must be an object")

        action_type = request.get("action_type")
        if not action_type:
            raise ValueError("request.action_type is required")

        action_name = action_type if action_type != "custom" else request.get("custom_tool_name") or ""
        if not self._request_allowed(request, action_name):
            return {
                "kind": "rejected",
                "summary": "Action blocked by the current policy allowlist.",
                "action_type": action_type,
            }

        if action_type in {"odoo_read", "odoo_write"}:
            return {
                "kind": "requires_local_execution",
                "summary": "This action must run inside Odoo with ORM access.",
                "tool_name": "openclaw.execute_request",
                "local_action": self._normalise_local_odoo_action(request),
            }

        payload = request.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}

        if action_type == "db_read":
            return await self.tool_db_list_databases({})
        if action_type == "db_write":
            operation = payload.get("operation")
            if operation == "create":
                return await self.tool_db_create_database({"name": payload.get("name") or payload.get("target")})
            if operation == "duplicate":
                return await self.tool_db_duplicate_database({"source": payload.get("source"), "target": payload.get("target")})
            if operation == "drop":
                return await self.tool_db_drop_database({"name": payload.get("name") or payload.get("target"), "confirm": payload.get("confirm") or payload.get("name") or payload.get("target")})
            return {
                "kind": "rejected",
                "summary": "Unsupported database write operation.",
                "supported_operations": ["create", "duplicate", "drop"],
            }
        if action_type == "docs_read":
            path = payload.get("path") or request.get("target_ref") or ""
            return await self.tool_docs_read_markdown({"path": path})
        if action_type == "docs_write":
            path = payload.get("path") or request.get("target_ref")
            content = payload.get("content")
            if not path or content is None:
                return {
                    "kind": "rejected",
                    "summary": "docs.write requires path and content.",
                }
            return await self.tool_docs_write_markdown({"path": path, "content": content})
        if action_type == "web_search":
            return await self.tool_web_search({"query": payload.get("query") or request.get("instruction", ""), "max_results": payload.get("max_results") or 5})
        if action_type == "code_generation":
            return await self.tool_code_generate({"instruction": request.get("instruction", ""), "context": payload.get("context", ""), "target": payload.get("target", "")})
        if action_type == "shell_action":
            return await self.tool_shell_execute({"command": payload.get("command") or "", "cwd": payload.get("cwd") or settings.openclaw_workspace_root})
        if action_type == "custom":
            tool_name = request.get("custom_tool_name") or payload.get("tool_name")
            if not tool_name:
                return {"kind": "rejected", "summary": "Custom requests require custom_tool_name or payload.tool_name."}
            tool_arguments = payload.get("arguments") if isinstance(payload.get("arguments"), dict) else payload
            if not self._request_allowed(request, tool_name):
                return {"kind": "rejected", "summary": f"Custom tool not allowed: {tool_name}"}
            result = await self.call_tool(tool_name, tool_arguments)
            decoded = self._decode_mcp_result(result)
            decoded.setdefault("tool_name", tool_name)
            return decoded

        return {
            "kind": "rejected",
            "summary": f"Unsupported action type: {action_type}",
            "action_type": action_type,
        }

    async def tool_db_list_databases(self, arguments: dict[str, Any]) -> dict[str, Any]:
        databases = await db_manager.list_databases()
        return {
            "kind": "completed",
            "summary": f"Listed {len(databases)} database(s).",
            "databases": [dat.__dict__ for dat in databases],
        }

    async def tool_db_create_database(self, arguments: dict[str, Any]) -> dict[str, Any]:
        name = (arguments.get("name") or "").strip()
        if not name:
            return {"kind": "rejected", "summary": "Database name is required."}
        ok, output = await db_manager.create_database(name)
        return {"kind": "completed" if ok else "failed", "summary": output or (f"Database '{name}' created" if ok else f"Failed to create '{name}'"), "name": name, "ok": ok, "output": output}

    async def tool_db_duplicate_database(self, arguments: dict[str, Any]) -> dict[str, Any]:
        source = (arguments.get("source") or "").strip()
        target = (arguments.get("target") or "").strip()
        if not source or not target:
            return {"kind": "rejected", "summary": "Both source and target database names are required."}
        ok, output = await db_manager.duplicate_database(source, target)
        return {"kind": "completed" if ok else "failed", "summary": output or (f"Database '{source}' duplicated as '{target}'" if ok else f"Failed to duplicate '{source}'"), "source": source, "target": target, "ok": ok, "output": output}

    async def tool_db_drop_database(self, arguments: dict[str, Any]) -> dict[str, Any]:
        name = (arguments.get("name") or "").strip()
        confirm = (arguments.get("confirm") or "").strip()
        if not name or not confirm:
            return {"kind": "rejected", "summary": "Database name and confirmation are required."}
        if name != confirm:
            return {"kind": "rejected", "summary": "Confirmation must match the database name exactly.", "name": name}
        ok, output = await db_manager.drop_database(name)
        return {"kind": "completed" if ok else "failed", "summary": output or (f"Database '{name}' dropped" if ok else f"Failed to drop '{name}'"), "name": name, "ok": ok, "output": output}

    async def tool_docs_read_markdown(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = (arguments.get("path") or "").strip()
        if not path:
            return {"kind": "rejected", "summary": "docs.read_markdown requires a path."}
        rendered_title, rendered_html = docs_browser.read_markdown(path)
        file_data = self.workspace.read_file("docs", path)
        return {
            "kind": "completed",
            "summary": f"Read docs path '{path}'.",
            "path": file_data.get("path", path),
            "title": rendered_title,
            "content": file_data.get("content"),
            "rendered_html": rendered_html,
        }

    async def tool_docs_write_markdown(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = (arguments.get("path") or "").strip()
        content = arguments.get("content")
        if not path or content is None:
            return {"kind": "rejected", "summary": "docs.write_markdown requires path and content."}
        result = self.workspace.write_file("docs", path, str(content))
        return {"kind": "completed", "summary": f"Wrote docs file '{result['path']}'.", **result}

    async def tool_docs_search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = (arguments.get("query") or "").strip()
        max_results = int(arguments.get("max_results") or 20)
        if not query:
            return {"kind": "rejected", "summary": "docs.search requires a query."}
        result = self.workspace.search("docs", query, max_results=max_results)
        result["kind"] = "completed"
        result["summary"] = f"Found {len(result['results'])} docs hit(s)."
        return result

    async def tool_workspace_read_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        root = (arguments.get("root") or "").strip()
        path = (arguments.get("path") or "").strip()
        if root not in {"docs", "addons_custom"}:
            return {"kind": "rejected", "summary": "root must be docs or addons_custom."}
        if not path:
            return {"kind": "rejected", "summary": "path is required."}
        result = self.workspace.read_file(root, path)
        result["kind"] = "completed"
        result["summary"] = f"Read {root}:{result['path']}"
        return result

    async def tool_workspace_write_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        root = (arguments.get("root") or "").strip()
        path = (arguments.get("path") or "").strip()
        content = arguments.get("content")
        if root not in {"docs", "addons_custom"}:
            return {"kind": "rejected", "summary": "root must be docs or addons_custom."}
        if not path or content is None:
            return {"kind": "rejected", "summary": "path and content are required."}
        result = self.workspace.write_file(root, path, str(content))
        return {"kind": "completed", "summary": f"Wrote {root}:{result['path']}.", **result}

    async def tool_workspace_list_tree(self, arguments: dict[str, Any]) -> dict[str, Any]:
        root = (arguments.get("root") or "").strip()
        path = (arguments.get("path") or "").strip()
        max_depth = int(arguments.get("max_depth") or 3)
        if root not in {"docs", "addons_custom", "all"}:
            return {"kind": "rejected", "summary": "root must be docs, addons_custom, or all."}
        tree = self.workspace.list_tree(root, path, max_depth=max_depth)
        tree["kind"] = "completed"
        tree["summary"] = f"Listed tree for {root}:{path or '.'}."
        return tree

    async def tool_workspace_search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        root = (arguments.get("root") or "").strip()
        query = (arguments.get("query") or "").strip()
        max_results = int(arguments.get("max_results") or 20)
        if root not in {"docs", "addons_custom", "all"}:
            return {"kind": "rejected", "summary": "root must be docs, addons_custom, or all."}
        if not query:
            return {"kind": "rejected", "summary": "query is required."}
        result = self.workspace.search(root, query, max_results=max_results)
        result["kind"] = "completed"
        result["summary"] = f"Found {len(result['results'])} hit(s) under {root}."
        return result

    async def tool_web_search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        query = (arguments.get("query") or "").strip()
        max_results = int(arguments.get("max_results") or 5)
        if not query:
            return {"kind": "rejected", "summary": "web.search requires a query."}
        url = "https://html.duckduckgo.com/html/"
        headers = {"User-Agent": "Mozilla/5.0 (OpenClaw)"}
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url, params={"q": query}, headers=headers)
            response.raise_for_status()
        matches = []
        pattern = re.compile(r'<a[^>]+class="result__a"[^>]+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>', re.S)
        for match in pattern.finditer(response.text):
            raw_url = html.unescape(match.group("url"))
            title = re.sub(r"<.*?>", "", html.unescape(match.group("title"))).strip()
            parsed = urlparse(raw_url)
            if parsed.netloc.endswith("duckduckgo.com") and parsed.path == "/l/":
                params = parse_qs(parsed.query)
                if "uddg" in params:
                    raw_url = html.unescape(params["uddg"][0])
            matches.append({"title": title, "url": raw_url})
            if len(matches) >= max_results:
                break
        return {"kind": "completed", "summary": f"Found {len(matches)} web result(s).", "query": query, "results": matches}

    async def tool_github_list_workflows(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.github.configured:
            return {"kind": "rejected", "summary": "GITHUB_TOKEN is not configured."}
        workflows = await self.github.list_workflows()
        return {"kind": "completed", "summary": f"Found {len(workflows)} workflow(s).", "workflows": workflows}

    async def tool_github_dispatch_workflow(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.github.configured:
            return {"kind": "rejected", "summary": "GITHUB_TOKEN is not configured."}
        workflow_id = int(arguments.get("workflow_id") or 0)
        ref = (arguments.get("ref") or "").strip()
        if not workflow_id or not ref:
            return {"kind": "rejected", "summary": "workflow_id and ref are required."}
        ok = await self.github.dispatch_workflow(workflow_id, ref)
        return {"kind": "completed" if ok else "failed", "summary": f"Workflow dispatch {'succeeded' if ok else 'failed'} for {workflow_id}@{ref}.", "workflow_id": workflow_id, "ref": ref, "ok": ok}

    async def tool_obsidian_mcp_tools_list(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not settings.openclaw_obsidian_mcp_url:
            return {"kind": "rejected", "summary": "OPENCLAW_OBSIDIAN_MCP_URL is not configured."}
        return await self._remote_mcp_request(
            base_url=settings.openclaw_obsidian_mcp_url,
            token=settings.openclaw_obsidian_mcp_token,
            timeout_seconds=settings.openclaw_obsidian_mcp_timeout_seconds,
            method="tools/list",
            params={},
        )

    async def tool_obsidian_mcp_call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not settings.openclaw_obsidian_mcp_url:
            return {"kind": "rejected", "summary": "OPENCLAW_OBSIDIAN_MCP_URL is not configured."}
        tool_name = (arguments.get("tool_name") or "").strip()
        if not tool_name:
            return {"kind": "rejected", "summary": "tool_name is required."}
        raw_args = arguments.get("arguments")
        tool_arguments = raw_args if isinstance(raw_args, dict) else {}
        return await self._remote_mcp_request(
            base_url=settings.openclaw_obsidian_mcp_url,
            token=settings.openclaw_obsidian_mcp_token,
            timeout_seconds=settings.openclaw_obsidian_mcp_timeout_seconds,
            method="tools/call",
            params={"name": tool_name, "arguments": tool_arguments},
        )

    async def tool_memory_mcp_tools_list(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not settings.openclaw_memory_mcp_url:
            return {"kind": "rejected", "summary": "OPENCLAW_MEMORY_MCP_URL is not configured."}
        return await self._remote_mcp_request(
            base_url=settings.openclaw_memory_mcp_url,
            token=settings.openclaw_memory_mcp_token,
            timeout_seconds=settings.openclaw_memory_mcp_timeout_seconds,
            method="tools/list",
            params={},
        )

    async def tool_memory_mcp_call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not settings.openclaw_memory_mcp_url:
            return {"kind": "rejected", "summary": "OPENCLAW_MEMORY_MCP_URL is not configured."}
        tool_name = (arguments.get("tool_name") or "").strip()
        if not tool_name:
            return {"kind": "rejected", "summary": "tool_name is required."}
        raw_args = arguments.get("arguments")
        tool_arguments = raw_args if isinstance(raw_args, dict) else {}
        return await self._remote_mcp_request(
            base_url=settings.openclaw_memory_mcp_url,
            token=settings.openclaw_memory_mcp_token,
            timeout_seconds=settings.openclaw_memory_mcp_timeout_seconds,
            method="tools/call",
            params={"name": tool_name, "arguments": tool_arguments},
        )

    async def tool_cif_validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not settings.openclaw_cif_lookup_mcp_url:
            return {"kind": "rejected", "summary": "OPENCLAW_CIF_LOOKUP_MCP_URL is not configured."}
        cif = (arguments.get("cif") or "").strip()
        if not cif:
            return {"kind": "rejected", "summary": "cif is required."}
        return await self._remote_mcp_request(
            base_url=settings.openclaw_cif_lookup_mcp_url,
            token=settings.openclaw_cif_lookup_mcp_token,
            timeout_seconds=settings.openclaw_cif_lookup_mcp_timeout_seconds,
            method="tools/call",
            params={"name": "cif.validate", "arguments": {"cif": cif}},
        )

    async def tool_cif_lookup(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not settings.openclaw_cif_lookup_mcp_url:
            return {"kind": "rejected", "summary": "OPENCLAW_CIF_LOOKUP_MCP_URL is not configured."}
        cif = (arguments.get("cif") or "").strip()
        if not cif:
            return {"kind": "rejected", "summary": "cif is required."}
        payload: dict[str, Any] = {"cif": cif}
        if arguments.get("include_partner_mapping"):
            payload["include_partner_mapping"] = True
        return await self._remote_mcp_request(
            base_url=settings.openclaw_cif_lookup_mcp_url,
            token=settings.openclaw_cif_lookup_mcp_token,
            timeout_seconds=settings.openclaw_cif_lookup_mcp_timeout_seconds,
            method="tools/call",
            params={"name": "cif.lookup", "arguments": payload},
        )

    async def tool_lead_categories(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not settings.openclaw_lead_mining_mcp_url:
            return {"kind": "rejected", "summary": "OPENCLAW_LEAD_MINING_MCP_URL is not configured."}
        return await self._remote_mcp_request(
            base_url=settings.openclaw_lead_mining_mcp_url,
            token=settings.openclaw_lead_mining_mcp_token,
            timeout_seconds=settings.openclaw_lead_mining_mcp_timeout_seconds,
            method="tools/call",
            params={"name": "lead.categories", "arguments": {}},
        )

    async def tool_lead_search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not settings.openclaw_lead_mining_mcp_url:
            return {"kind": "rejected", "summary": "OPENCLAW_LEAD_MINING_MCP_URL is not configured."}
        category = (arguments.get("category") or "").strip()
        if not category:
            return {"kind": "rejected", "summary": "category is required (call lead.categories first)."}
        payload: dict[str, Any] = {"category": category}
        for key in ("area_name", "bbox", "require_website", "require_phone", "limit"):
            if key in arguments and arguments[key] is not None:
                payload[key] = arguments[key]
        return await self._remote_mcp_request(
            base_url=settings.openclaw_lead_mining_mcp_url,
            token=settings.openclaw_lead_mining_mcp_token,
            timeout_seconds=settings.openclaw_lead_mining_mcp_timeout_seconds,
            method="tools/call",
            params={"name": "lead.search", "arguments": payload},
        )

    async def tool_context7_resolve_library_id(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not settings.openclaw_context7_mcp_url:
            return {"kind": "rejected", "summary": "OPENCLAW_CONTEXT7_MCP_URL is not configured."}
        library_name = (arguments.get("library_name") or "").strip()
        query = (arguments.get("query") or "").strip()
        if not library_name:
            return {"kind": "rejected", "summary": "library_name is required."}
        payload = {"libraryName": library_name}
        if query:
            payload["query"] = query
        return await self._remote_mcp_request(
            base_url=settings.openclaw_context7_mcp_url,
            token=settings.openclaw_context7_mcp_token,
            timeout_seconds=settings.openclaw_context7_mcp_timeout_seconds,
            method="tools/call",
            params={"name": settings.openclaw_context7_resolve_tool_name, "arguments": payload},
        )

    async def tool_context7_query_docs(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not settings.openclaw_context7_mcp_url:
            return {"kind": "rejected", "summary": "OPENCLAW_CONTEXT7_MCP_URL is not configured."}
        library_id = (arguments.get("library_id") or "").strip()
        query = (arguments.get("query") or "").strip()
        if not library_id or not query:
            return {"kind": "rejected", "summary": "library_id and query are required."}
        return await self._remote_mcp_request(
            base_url=settings.openclaw_context7_mcp_url,
            token=settings.openclaw_context7_mcp_token,
            timeout_seconds=settings.openclaw_context7_mcp_timeout_seconds,
            method="tools/call",
            params={
                "name": settings.openclaw_context7_query_tool_name,
                "arguments": {"libraryId": library_id, "query": query},
            },
        )

    async def tool_context7_mcp_tools_list(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not settings.openclaw_context7_mcp_url:
            return {"kind": "rejected", "summary": "OPENCLAW_CONTEXT7_MCP_URL is not configured."}
        return await self._remote_mcp_request(
            base_url=settings.openclaw_context7_mcp_url,
            token=settings.openclaw_context7_mcp_token,
            timeout_seconds=settings.openclaw_context7_mcp_timeout_seconds,
            method="tools/list",
            params={},
        )

    async def tool_context7_mcp_call(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not settings.openclaw_context7_mcp_url:
            return {"kind": "rejected", "summary": "OPENCLAW_CONTEXT7_MCP_URL is not configured."}
        tool_name = (arguments.get("tool_name") or "").strip()
        if not tool_name:
            return {"kind": "rejected", "summary": "tool_name is required."}
        raw_args = arguments.get("arguments")
        tool_arguments = raw_args if isinstance(raw_args, dict) else {}
        return await self._remote_mcp_request(
            base_url=settings.openclaw_context7_mcp_url,
            token=settings.openclaw_context7_mcp_token,
            timeout_seconds=settings.openclaw_context7_mcp_timeout_seconds,
            method="tools/call",
            params={"name": tool_name, "arguments": tool_arguments},
        )

    async def tool_code_generate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        instruction = (arguments.get("instruction") or "").strip()
        context = (arguments.get("context") or "").strip()
        target = (arguments.get("target") or "").strip()
        if not instruction:
            return {"kind": "rejected", "summary": "code.generate requires an instruction."}
        if self.openrouter.configured:
            models_to_try = [settings.openrouter_model]
            if settings.openrouter_fallback_model and settings.openrouter_fallback_model not in models_to_try:
                models_to_try.append(settings.openrouter_fallback_model)

            last_error: str | None = None
            for model_name in models_to_try:
                try:
                    draft = await self.openrouter.draft_plan(
                        instruction,
                        context=context,
                        target=target,
                        model=model_name,
                    )
                    return {
                        "kind": "completed",
                        "summary": draft.get("summary") or "Generated a code draft plan.",
                        "draft": draft,
                        "model": draft.get("model", model_name),
                        "provider": draft.get("provider", "openrouter"),
                    }
                except (OpenRouterError, httpx.HTTPError, ValueError) as exc:
                    last_error = str(exc)
                    log.warning("OpenRouter draft generation failed for %s: %s", model_name, exc)

            if last_error:
                log.warning("OpenRouter draft generation fell back to local output: %s", last_error)

        draft = {
            "target": target or None,
            "instruction": instruction,
            "context": context or None,
            "notes": [
                "Use workspace.write_file for actual file writes.",
                "Keep writes scoped to addons_custom or docs.",
                f"Preferred OpenRouter model: {settings.openrouter_model}",
                f"Fallback OpenRouter model: {settings.openrouter_fallback_model}",
            ],
        }
        return {
            "kind": "completed",
            "summary": "Generated a local fallback draft plan.",
            "draft": draft,
            "provider": "local-fallback",
            "model": settings.openrouter_model,
        }

    def _inject_policy_system_prompt(
        self,
        messages: list[dict[str, str]],
        policy_context: dict[str, Any],
    ) -> list[dict[str, str]]:
        available = policy_context.get("available_policies") or []
        taxonomy_json = json.dumps(_build_skill_taxonomy(policy_context), ensure_ascii=False)
        instruction = (
            "Respond as a single JSON object with keys `reply` (string) and "
            "`suggested_actions` (array). `reply` is the user-facing text. "
            "Each suggested action must have `title`, `rationale`, `action_type`, "
            "`policy_key`, and `payload` (object). Only use `policy_key` values "
            f"from this list: {json.dumps(available, ensure_ascii=False)}. "
            "Never invent new action_type aliases. For dashboard creation, use "
            "`action_type=\"odoo_write\"` with `payload.operation=\"create\"` "
            "and `payload.model=\"dashboard.dashboard\"`. "
            "Follow the official OpenClaw skill taxonomy with `openclaw-core`, "
            "`openclaw-router`, and domain skills. Taxonomy: "
            f"{taxonomy_json}. When unsure, return an empty "
            "`suggested_actions` array. Never include text outside the JSON."
        )
        extended = list(messages)
        extended.insert(0, {"role": "system", "content": instruction})
        return extended

    @staticmethod
    def _select_policy_key_for_action(policy_context: dict[str, Any], action_name: str) -> str | None:
        available = policy_context.get("available_policies") or []
        for policy in available:
            if not isinstance(policy, dict):
                continue
            allowed = policy.get("allowed_actions") or []
            if action_name in allowed:
                key = policy.get("key")
                if key:
                    return str(key)
        return None

    def _build_contact_chat_reply(
        self,
        messages: list[dict[str, str]],
        policy_context: dict[str, Any],
    ) -> dict[str, Any] | None:
        last_user_message = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        if not last_user_message:
            return None

        text = last_user_message.lower()
        contact_keywords = ["contacto", "contact", "partner", "persona", "empresa", "res.partner"]
        action_keywords = [
            "crear", "crea", "nuevo", "agregar", "añadir", "add", "create",
            "actualizar", "actualiza", "editar", "edita", "modificar", "modifica", "cambiar", "cambia", "update", "edit",
            "eliminar", "elimina", "borrar", "borra", "delete", "remove",
            "buscar", "busca", "listar", "lista", "mostrar", "muestra", "ver", "view", "search",
        ]
        if not _text_contains_any(text, contact_keywords) or not _text_contains_any(text, action_keywords):
            return None

        if _text_contains_any(text, ["crear", "crea", "nuevo", "agregar", "añadir", "add", "create"]):
            values = _extract_contact_create_values(last_user_message)
            name = str(values.get("name") or "").strip()
            if not name:
                return {
                    "reply": (
                        "He detectado que quieres crear un contacto con el skill openclaw-crm-contacts, "
                        "pero me falta el nombre. Dime el nombre y, si quieres, email y teléfono."
                    ),
                    "suggested_actions": [],
                }
            policy_key = self._select_policy_key_for_action(policy_context, "odoo_write")
            if not policy_key:
                return {
                    "reply": "Detecté la intención de crear un contacto, pero no hay una policy con escritura Odoo activa.",
                    "suggested_actions": [],
                }
            return {
                "reply": f"He enroutado tu mensaje al skill openclaw-crm-contacts para crear el contacto '{name}'.",
                "suggested_actions": [
                    {
                        "title": "Crear contacto CRM",
                        "rationale": "Crear un res.partner con los datos capturados por el router oficial de OpenClaw.",
                        "action_type": "odoo_write",
                        "policy_key": policy_key,
                        "target_model": "res.partner",
                        "payload": {
                            "model": "res.partner",
                            "operation": "create",
                            "values": values,
                        },
                    }
                ],
            }

        if _text_contains_any(text, ["actualizar", "actualiza", "editar", "edita", "modificar", "modifica", "cambiar", "cambia", "update", "edit"]):
            reference = _extract_contact_reference(last_user_message)
            values = _extract_contact_update_values(last_user_message)
            if not reference:
                return {
                    "reply": (
                        "He enroutado tu mensaje al skill openclaw-crm-contacts, pero necesito el ID o el nombre del contacto "
                        "para actualizarlo."
                    ),
                    "suggested_actions": [],
                }
            if not values:
                return {
                    "reply": (
                        "Tengo el contacto objetivo, pero me falta qué quieres cambiar. Indícame email, teléfono, país, ciudad o nombre."
                    ),
                    "suggested_actions": [],
                }
            policy_key = self._select_policy_key_for_action(policy_context, "odoo_write")
            if not policy_key:
                return {
                    "reply": "Detecté la intención de editar un contacto, pero no hay una policy con escritura Odoo activa.",
                    "suggested_actions": [],
                }
            if reference.get("ids"):
                payload: dict[str, Any] = {
                    "model": "res.partner",
                    "operation": "write",
                    "ids": reference["ids"],
                    "values": values,
                }
            else:
                contact_name = str(reference.get("name") or "").strip()
                payload = {
                    "model": "res.partner",
                    "operation": "write_by_domain",
                    "domain": [["name", "ilike", contact_name]],
                    "values": values,
                }
            return {
                "reply": "He enroutado tu mensaje al skill openclaw-crm-contacts para actualizar el contacto solicitado.",
                "suggested_actions": [
                    {
                        "title": "Actualizar contacto CRM",
                        "rationale": "Actualizar res.partner usando el router oficial de OpenClaw.",
                        "action_type": "odoo_write",
                        "policy_key": policy_key,
                        "target_model": "res.partner",
                        "payload": payload,
                    }
                ],
            }

        if _text_contains_any(text, ["eliminar", "elimina", "borrar", "borra", "delete", "remove"]):
            reference = _extract_contact_reference(last_user_message)
            if not reference:
                return {
                    "reply": "He enroutado tu mensaje al skill openclaw-crm-contacts, pero necesito el ID o el nombre del contacto para borrarlo.",
                    "suggested_actions": [],
                }
            policy_key = self._select_policy_key_for_action(policy_context, "odoo_write")
            if not policy_key:
                return {
                    "reply": "Detecté la intención de borrar un contacto, pero no hay una policy con escritura Odoo activa.",
                    "suggested_actions": [],
                }
            if reference.get("ids"):
                payload = {
                    "model": "res.partner",
                    "operation": "unlink",
                    "ids": reference["ids"],
                }
            else:
                contact_name = str(reference.get("name") or "").strip()
                payload = {
                    "model": "res.partner",
                    "operation": "unlink_by_domain",
                    "domain": [["name", "ilike", contact_name]],
                }
            return {
                "reply": "He enroutado tu mensaje al skill openclaw-crm-contacts para eliminar el contacto solicitado.",
                "suggested_actions": [
                    {
                        "title": "Eliminar contacto CRM",
                        "rationale": "Eliminar res.partner de forma controlada mediante OpenClaw.",
                        "action_type": "odoo_write",
                        "policy_key": policy_key,
                        "target_model": "res.partner",
                        "payload": payload,
                    }
                ],
            }

        if _text_contains_any(text, ["buscar", "busca", "listar", "lista", "mostrar", "muestra", "ver", "view", "search"]):
            query = _extract_search_query(last_user_message, ["buscar contactos", "buscar contacto", "listar contactos", "mostrar contactos", "ver contactos", "buscar cliente", "buscar clientes"])
            policy_key = self._select_policy_key_for_action(policy_context, "odoo_read")
            if not policy_key:
                return {
                    "reply": "Detecté una búsqueda de contactos, pero no hay una policy con lectura Odoo activa.",
                    "suggested_actions": [],
                }
            return {
                "reply": "He enroutado tu mensaje al skill openclaw-crm-contacts para buscar los contactos solicitados.",
                "suggested_actions": [
                    {
                        "title": "Buscar contactos CRM",
                        "rationale": "Leer res.partner para localizar contactos por nombre, email o teléfono.",
                        "action_type": "odoo_read",
                        "policy_key": policy_key,
                        "target_model": "res.partner",
                        "payload": {
                            "model": "res.partner",
                            "operation": "search_read",
                            "domain": ["|", "|", ["name", "ilike", query], ["email", "ilike", query], ["phone", "ilike", query]],
                            "fields": ["name", "email", "phone", "is_company", "country_id", "city"],
                            "limit": 20,
                        },
                    }
                ],
            }

        return None

    def _build_domain_handoff_reply(
        self,
        messages: list[dict[str, str]],
        domain_skill: str,
        focus_phrase: str,
    ) -> dict[str, Any] | None:
        last_user_message = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        if not last_user_message:
            return None

        return {
            "reply": (
                f"He enroutado tu mensaje al skill {domain_skill}. "
                f"Si me das más detalles sobre {focus_phrase}, te preparo la acción aprobable."
            ),
            "suggested_actions": [],
        }

    def _build_dashboard_chat_reply(
        self,
        messages: list[dict[str, str]],
        policy_context: dict[str, Any],
    ) -> dict[str, Any] | None:
        recent_user_messages = _recent_user_messages(messages)
        last_user_message = recent_user_messages[-1] if recent_user_messages else ""
        if not last_user_message:
            return None

        recent_context = "\n".join(recent_user_messages)
        text = last_user_message.lower()
        recent_text = recent_context.lower()
        dashboard_keywords = ["dashboard", "tablero", "cuadro de mando", "panel"]
        dashboard_actions = ["crear", "crea", "nuevo", "nueva", "build", "create", "generar", "arma"]
        publish_actions = ["publicar", "publica", "share", "compartir", "comparte"]
        if not _text_contains_any(recent_text, dashboard_keywords):
            return None

        policy_key = self._select_policy_key_for_action(policy_context, "odoo_write")
        if not policy_key:
            return {
                "reply": (
                    "Detecté intención de dashboard, pero no hay una policy activa con permiso "
                    "de escritura Odoo para ejecutar la operación."
                ),
                "suggested_actions": [],
            }

        if _text_contains_any(text, publish_actions):
            return {
                "reply": (
                    "Te enrouté al skill openclaw-dashboard-chat. Para publicar el dashboard, "
                    "indícame el nombre exacto y a qué grupo o usuarios quieres dar acceso."
                ),
                "suggested_actions": [],
            }

        recent_dashboard_action = any(_text_contains_any(message.lower(), dashboard_actions) for message in recent_user_messages)
        recent_delegation = any(_dashboard_delegation_requested(message) for message in recent_user_messages)
        last_confirmation = _dashboard_confirmation_requested(last_user_message)

        if not recent_dashboard_action and not recent_delegation and not last_confirmation:
            return {
                "reply": (
                    "Te enrouté al skill openclaw-dashboard-chat. Si quieres, te preparo la acción "
                    "aprobable para crearlo; dime el nombre del dashboard y objetivo principal."
                ),
                "suggested_actions": [],
            }

        dashboard_name = _extract_dashboard_name(recent_context)
        chart_type = _extract_dashboard_chart_type(recent_context)
        model_name = _extract_dashboard_model(recent_context)
        requested_fields = _extract_dashboard_fields(recent_context)
        representation_goal = _extract_dashboard_representation(recent_context)
        dashboard_name, chart_type, model_name, requested_fields, representation_goal, defaults_used = _apply_dashboard_safe_defaults(
            text=recent_context,
            dashboard_name=dashboard_name,
            chart_type=chart_type,
            model_name=model_name,
            requested_fields=requested_fields,
            representation_goal=representation_goal,
            allow_defaults=recent_delegation,
        )

        missing: list[str] = []
        if not dashboard_name:
            missing.append("nombre del dashboard")
        if not chart_type:
            missing.append("tipo de gráfico")
        if not model_name:
            missing.append("modelo Odoo origen (ej: sale.order)")
        if not requested_fields:
            missing.append("datos/campos a extraer")
        if not representation_goal:
            missing.append("qué quieres representar")

        if missing:
            chart_type_list = ", ".join([f"{code} ({label})" for code, label in _DASHBOARD_CHART_TYPES])
            return {
                "reply": (
                    "Te enrouté al skill openclaw-dashboard-chat y para crearlo necesito completar estos datos: "
                    f"{'; '.join(missing)}. "
                    "Lista completa de tipos de gráfico disponibles en este módulo: "
                    f"{chart_type_list}. "
                    "Formato recomendado: nombre, tipo, modelo, campos y representación objetivo."
                ),
                "suggested_actions": [],
            }

        return {
            "reply": (
                f"Perfecto. Preparé la acción de openclaw-dashboard-chat para crear el dashboard '{dashboard_name}' "
                "y dejarlo listo para confirmación en la UI."
            ),
            "suggested_actions": [
                {
                    "title": "Crear dashboard BI",
                    "rationale": (
                        "Crear dashboard.dashboard y dejar registrada la especificación pedida: "
                        f"tipo={chart_type}, modelo={model_name}, campos={requested_fields}, representa={representation_goal}."
                    ),
                    "action_type": "odoo_write",
                    "policy_key": policy_key,
                    "target_model": "dashboard.dashboard",
                    "payload": {
                        "model": "dashboard.dashboard",
                        "operation": "create",
                        "values": {
                            "name": dashboard_name,
                        },
                        "blueprint": {
                            "chart_type": chart_type,
                            "model": model_name,
                            "fields": requested_fields,
                            "representation": representation_goal,
                        },
                    },
                }
            ],
        }

    def _build_dashboard_chat_reply(
        self,
        messages: list[dict[str, str]],
        policy_context: dict[str, Any],
    ) -> dict[str, Any] | None:
        recent_user_messages = _recent_user_messages(messages)
        last_user_message = recent_user_messages[-1] if recent_user_messages else ""
        if not last_user_message:
            return None

        recent_context = "\n".join(recent_user_messages)
        text = last_user_message.lower()
        recent_text = recent_context.lower()
        dashboard_keywords = ["dashboard", "tablero", "cuadro de mando", "panel"]
        dashboard_actions = ["crear", "crea", "nuevo", "nueva", "build", "create", "generar", "arma"]
        publish_actions = ["publicar", "publica", "share", "compartir", "comparte"]
        if not _text_contains_any(recent_text, dashboard_keywords):
            return None

        policy_key = self._select_policy_key_for_action(policy_context, "odoo_write")
        if not policy_key:
            return {
                "reply": (
                    "Detecté intención de dashboard, pero no hay una policy activa con permiso "
                    "de escritura Odoo para ejecutar la operación."
                ),
                "suggested_actions": [],
            }

        if _text_contains_any(text, publish_actions):
            return {
                "reply": (
                    "Te enrouté al skill openclaw-dashboard-chat. Para publicar el dashboard, "
                    "indícame el nombre exacto y a qué grupo o usuarios quieres dar acceso."
                ),
                "suggested_actions": [],
            }

        recent_dashboard_action = any(_text_contains_any(message.lower(), dashboard_actions) for message in recent_user_messages)
        recent_delegation = any(_dashboard_delegation_requested(message) for message in recent_user_messages)
        last_confirmation = _dashboard_confirmation_requested(last_user_message)
        if not recent_dashboard_action and not recent_delegation and not last_confirmation:
            return {
                "reply": (
                    "Te enrouté al skill openclaw-dashboard-chat. Si quieres, te preparo la acción "
                    "aprobable para crearlo; dime el nombre del dashboard y objetivo principal."
                ),
                "suggested_actions": [],
            }

        dashboard_name = _extract_dashboard_name(recent_context)
        chart_type = _extract_dashboard_chart_type(recent_context)
        model_name = _extract_dashboard_model(recent_context)
        requested_fields = _extract_dashboard_fields(recent_context)
        representation_goal = _extract_dashboard_representation(recent_context)
        dashboard_name, chart_type, model_name, requested_fields, representation_goal, defaults_used = _apply_dashboard_safe_defaults(
            text=recent_context,
            dashboard_name=dashboard_name,
            chart_type=chart_type,
            model_name=model_name,
            requested_fields=requested_fields,
            representation_goal=representation_goal,
            allow_defaults=recent_delegation,
        )

        missing: list[str] = []
        if not dashboard_name:
            missing.append("nombre del dashboard")
        if not chart_type:
            missing.append("tipo de gráfico")
        if not model_name:
            missing.append("modelo Odoo origen (ej: sale.order)")
        if not requested_fields:
            missing.append("datos/campos a extraer")
        if not representation_goal:
            missing.append("qué quieres representar")

        if missing:
            chart_type_list = ", ".join([f"{code} ({label})" for code, label in _DASHBOARD_CHART_TYPES])
            return {
                "reply": (
                    "Te enrouté al skill openclaw-dashboard-chat y para crearlo necesito completar estos datos: "
                    f"{'; '.join(missing)}. "
                    "Lista completa de tipos de gráfico disponibles en este módulo: "
                    f"{chart_type_list}. "
                    "Formato recomendado: nombre, tipo, modelo, campos y representación objetivo."
                ),
                "suggested_actions": [],
            }

        defaults_summary = "; ".join(defaults_used)
        if recent_delegation and defaults_used and not last_confirmation:
            return {
                "reply": (
                    "Te enrouté al skill openclaw-dashboard-chat. Como me delegaste la configuración, "
                    "te propongo esta configuración base antes de crear nada: "
                    f"{defaults_summary}. "
                    "Si te vale, responde 'si', 'hazlo' o 'adelante' y genero la acción aprobable."
                ),
                "suggested_actions": [],
            }

        rationale_suffix = f" Supuestos delegados usados: {defaults_summary}." if defaults_used else ""
        if recent_delegation and defaults_used and last_confirmation:
            reply_text = (
                "Perfecto. Preparé la acción de openclaw-dashboard-chat con estos supuestos revisables: "
                f"{defaults_summary}."
            )
        else:
            reply_text = (
                f"Perfecto. Preparé la acción de openclaw-dashboard-chat para crear el dashboard '{dashboard_name}' "
                "y dejarlo listo para confirmación en la UI."
            )

        return {
            "reply": reply_text,
            "suggested_actions": [
                {
                    "title": "Crear dashboard BI",
                    "rationale": (
                        "Crear dashboard.dashboard y dejar registrada la especificación pedida: "
                        f"tipo={chart_type}, modelo={model_name}, campos={requested_fields}, representa={representation_goal}."
                        f"{rationale_suffix}"
                    ),
                    "action_type": "odoo_write",
                    "policy_key": policy_key,
                    "target_model": "dashboard.dashboard",
                    "payload": {
                        "model": "dashboard.dashboard",
                        "operation": "create",
                        "values": {
                            "name": dashboard_name,
                        },
                        "blueprint": {
                            "chart_type": chart_type,
                            "model": model_name,
                            "fields": requested_fields,
                            "representation": representation_goal,
                        },
                    },
                }
            ],
        }

    _CIF_REGEX = re.compile(r"\b([ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J])\b", re.IGNORECASE)

    async def _build_cif_chat_reply(
        self,
        messages: list[dict[str, str]],
        policy_context: dict[str, Any],
    ) -> dict[str, Any] | None:
        last_user_message = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        if not last_user_message:
            return None
        match = self._CIF_REGEX.search(last_user_message)
        if not match:
            return None
        cif = match.group(1).upper()

        text_lower = last_user_message.lower()
        user_confirmed = any(tok in text_lower for tok in [" si ", " sí ", "si,", "sí,", "si\n", "sí\n", "confirmo", "adelante", "procede", "guarda", "guárdala", "dala de alta"]) or text_lower.strip() in {"si", "sí", "yes"}

        try:
            lookup_result = await self.tool_cif_lookup({"cif": cif, "include_partner_mapping": True})
        except Exception as exc:
            return {
                "reply": f"No pude consultar el CIF {cif}: {exc}. Reintenta en unos segundos.",
                "suggested_actions": [],
            }

        if lookup_result.get("kind") != "completed":
            summary = lookup_result.get("summary") or "no se pudo completar el lookup"
            return {
                "reply": f"CIF {cif}: {summary}.",
                "suggested_actions": [],
            }

        data = lookup_result.get("result") or lookup_result
        if isinstance(data, dict) and isinstance(data.get("content"), list):
            for item in data["content"]:
                if item.get("type") == "text":
                    try:
                        data = json.loads(item.get("text") or "{}")
                    except (ValueError, TypeError):
                        data = {}
                    break

        if not isinstance(data, dict) or data.get("error"):
            msg = (data or {}).get("mensaje") if isinstance(data, dict) else "sin datos"
            return {
                "reply": f"No encontré datos para el CIF {cif}: {msg}. Revisa el CIF o reintenta.",
                "suggested_actions": [],
            }

        razon = data.get("razon_social") or data.get("nombre") or ""
        direccion = data.get("direccion") or ""
        cp = data.get("codigo_postal") or ""
        municipio = data.get("municipio") or ""
        ccaa = data.get("comunidad_autonoma") or ""
        telefono = data.get("telefono") or ""
        website = data.get("website") or ""
        fuente = data.get("_fuente") or data.get("fuente") or "scraper"
        missing = data.get("_campos_no_disponibles") or []

        partner_mapping = data.get("_res_partner") or {}
        values = partner_mapping.get("values") or {}
        state_name = partner_mapping.get("state_name") or ccaa
        country_code = partner_mapping.get("country_code") or "ES"

        if not user_confirmed:
            resumen_lines = [
                f"He encontrado esta empresa con CIF {cif} (fuente: {fuente}):",
                f"- Razón social: {razon or '(no disponible)'}",
                f"- Dirección: {direccion or '(no disponible)'}",
                f"- CP / Municipio: {cp or '-'} / {municipio or '-'}",
                f"- CCAA: {ccaa or '-'}",
                f"- Teléfono: {telefono or '(no disponible)'}",
                f"- Web: {website or '(no disponible)'}",
            ]
            if missing:
                resumen_lines.append(f"- Campos sin datos: {', '.join(missing)}")
            resumen_lines.append("")
            resumen_lines.append("¿Es esta la empresa que quieres dar de alta en Odoo? Responde **sí** para crearla o dime qué no cuadra.")
            return {
                "reply": "\n".join(resumen_lines),
                "suggested_actions": [],
            }

        policy_key = self._select_policy_key_for_action(policy_context, "odoo_write")
        if not policy_key:
            return {
                "reply": f"Tengo los datos de {razon or cif}, pero no hay una policy con escritura Odoo activa.",
                "suggested_actions": [],
            }

        return {
            "reply": f"Dando de alta {razon or cif} en res.partner vía OpenClaw (skill openclaw-cif-lookup).",
            "suggested_actions": [
                {
                    "title": f"Alta empresa {razon or cif}",
                    "rationale": f"Crear res.partner desde cif.lookup ({fuente}).",
                    "action_type": "odoo_write",
                    "policy_key": policy_key,
                    "target_model": "res.partner",
                    "payload": {
                        "model": "res.partner",
                        "operation": "create",
                        "values": values,
                        "state_name": state_name,
                        "country_code": country_code,
                    },
                }
            ],
        }

    def _route_chat_reply(
        self,
        messages: list[dict[str, str]],
        policy_context: dict[str, Any],
    ) -> dict[str, Any] | None:
        routed = self._build_contact_chat_reply(messages, policy_context)
        if routed is not None:
            return routed

        routed = self._build_crm_chat_reply(messages, policy_context)
        if routed is not None:
            return routed

        routed = self._build_dashboard_chat_reply(messages, policy_context)
        if routed is not None:
            return routed

        last_user_message = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        lowered = last_user_message.lower()

        if _text_contains_any(lowered, ["cotización", "cotizacion", "presupuesto", "pedido", "orden de venta", "sale order"]):
            return self._build_domain_handoff_reply(messages, "openclaw-sales", "la cotización o pedido")

        if _text_contains_any(lowered, ["stock", "inventario", "existencias", "producto", "almacén", "almacen", "warehouse"]):
            return self._build_domain_handoff_reply(messages, "openclaw-inventory", "el producto o stock")

        if _text_contains_any(
            lowered,
            [
                "factura",
                "facturas",
                "invoice",
                "invoicing",
                "pago",
                "pagos",
                "cobro",
                "cobranza",
                "cuentas por cobrar",
                "account.move",
            ],
        ):
            return self._build_domain_handoff_reply(messages, "openclaw-invoicing", "la factura, pago o cobranza")

        if _text_contains_any(
            lowered,
            [
                "compra",
                "compras",
                "purchase",
                "procurement",
                "proveedor",
                "proveedores",
                "orden de compra",
                "po ",
                "rfq",
            ],
        ):
            return self._build_domain_handoff_reply(messages, "openclaw-purchase", "la compra o proveedor")

        if _text_contains_any(
            lowered,
            [
                "empleado",
                "empleados",
                "rrhh",
                "hr",
                "recursos humanos",
                "vacaciones",
                "ausencia",
                "nomina",
                "payroll",
                "contrato",
            ],
        ):
            return self._build_domain_handoff_reply(messages, "openclaw-hr", "el proceso de RRHH o empleado")

        if _text_contains_any(
            lowered,
            [
                "reporte",
                "reportes",
                "informe",
                "informes",
                "dashboard",
                "kpi",
                "metricas",
                "métricas",
                "analitica",
                "analítica",
                "forecast",
            ],
        ):
            return self._build_domain_handoff_reply(messages, "openclaw-reporting", "el reporte o KPI que necesitas")

        return None

    def _build_crm_chat_reply(
        self,
        messages: list[dict[str, str]],
        policy_context: dict[str, Any],
    ) -> dict[str, Any] | None:
        last_user_message = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        if not last_user_message:
            return None

        text = last_user_message.lower()
        create_intent = any(
            token in text
            for token in [
                "crear oportunidad",
                "crear una oportunidad",
                "crea oportunidad",
                "crea una oportunidad",
                "create opportunity",
                "new opportunity",
                "nueva oportunidad",
            ]
        )
        delete_intent = any(
            token in text
            for token in [
                "borrar oportunidad",
                "borrar una oportunidad",
                "borrar la oportunidad",
                "borra oportunidad",
                "borra una oportunidad",
                "borra la oportunidad",
                "eliminar oportunidad",
                "eliminar una oportunidad",
                "elimina la oportunidad",
                "delete opportunity",
            ]
        )
        update_intent = (
            "oportunidad" in text
            and any(
                token in text
                for token in [
                    "modificar",
                    "modifica",
                    "actualizar",
                    "actualiza",
                    "editar",
                    "edita",
                    "cambiar",
                    "cambia",
                    "update",
                    "edit",
                    "change",
                ]
            )
        )
        if not create_intent and not delete_intent and not update_intent:
            return None

        opportunity_name, client_name = _extract_crm_entities(last_user_message)
        missing: list[str] = []
        if not opportunity_name:
            missing.append("nombre de la oportunidad")
        if not client_name:
            missing.append("cliente")

        if missing:
            missing_text = " y ".join(missing)
            action_label = "crear" if create_intent else ("borrar" if delete_intent else "modificar")
            return {
                "reply": (
                    f"Para {action_label} la oportunidad me falta {missing_text}. "
                    "Comparteme ambos datos y te genero la accion aprobable."
                ),
                "suggested_actions": [],
            }

        update_values = _extract_crm_update_values(last_user_message) if update_intent else {}
        if update_intent and not update_values:
            return {
                "reply": (
                    "Tengo la oportunidad y el cliente, pero me falta qué dato quieres modificar "
                    "(por ejemplo monto, prioridad, descripcion o nuevo nombre)."
                ),
                "suggested_actions": [],
            }

        policy_key = self._select_policy_key_for_action(policy_context, "odoo_write")
        if not policy_key:
            return {
                "reply": (
                    "Tengo el nombre de la oportunidad y el cliente, pero no hay una policy activa "
                    "con permiso de escritura Odoo para ejecutar esta accion."
                ),
                "suggested_actions": [],
            }

        if create_intent:
            return {
                "reply": (
                    f"Perfecto. Preparé la accion para crear la oportunidad '{opportunity_name}' "
                    f"para el cliente '{client_name}'."
                ),
                "suggested_actions": [
                    {
                        "title": "Crear oportunidad CRM",
                        "rationale": (
                            "Crear un crm.lead de tipo opportunity con los datos provistos por el usuario."
                        ),
                        "action_type": "odoo_write",
                        "policy_key": policy_key,
                        "target_model": "crm.lead",
                        "payload": {
                            "model": "crm.lead",
                            "operation": "create",
                            "values": _build_crm_create_values(opportunity_name, client_name),
                        },
                    }
                ],
            }

        if update_intent:
            return {
                "reply": (
                    f"Perfecto. Preparé la accion para modificar la oportunidad '{opportunity_name}' "
                    f"del cliente '{client_name}'."
                ),
                "suggested_actions": [
                    {
                        "title": "Modificar oportunidad CRM",
                        "rationale": (
                            "Actualizar crm.lead de tipo opportunity usando nombre de oportunidad y cliente como filtro."
                        ),
                        "action_type": "odoo_write",
                        "policy_key": policy_key,
                        "target_model": "crm.lead",
                        "payload": {
                            "model": "crm.lead",
                            "operation": "write_by_domain",
                            "domain": [
                                ["type", "=", "opportunity"],
                                ["name", "ilike", opportunity_name],
                                ["partner_name", "ilike", client_name],
                            ],
                            "values": update_values,
                        },
                    }
                ],
            }

        return {
            "reply": (
                f"Perfecto. Preparé la accion para borrar la oportunidad '{opportunity_name}' "
                f"del cliente '{client_name}'."
            ),
            "suggested_actions": [
                {
                    "title": "Borrar oportunidad CRM",
                    "rationale": (
                        "Eliminar crm.lead de tipo opportunity filtrando por nombre de oportunidad y cliente para evitar borrados ambiguos."
                    ),
                    "action_type": "odoo_write",
                    "policy_key": policy_key,
                    "target_model": "crm.lead",
                    "payload": {
                        "model": "crm.lead",
                        "operation": "unlink_by_domain",
                        "domain": [
                            ["type", "=", "opportunity"],
                            ["name", "ilike", opportunity_name],
                            ["partner_name", "ilike", client_name],
                        ],
                    },
                }
            ],
        }

    async def _complete_chat_reply(
        self,
        messages: list[dict[str, str]],
        *,
        chosen_model: str,
        temperature: float,
        max_tokens: int,
        fallback_model: str | None = None,
    ) -> dict[str, Any]:
        if self.openrouter.configured:
            models_to_try = [chosen_model]
            selected_fallback = (fallback_model or settings.openrouter_fallback_model or "").strip()
            if selected_fallback and selected_fallback not in models_to_try:
                models_to_try.append(selected_fallback)

            last_error: str | None = None
            for model_name in models_to_try:
                try:
                    raw_reply = await self.openrouter.chat_reply(
                        messages,
                        model=model_name,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    reply, actions = _parse_llm_envelope(raw_reply)
                    return {
                        "kind": "completed",
                        "summary": "Generated a chat reply.",
                        "reply": reply,
                        "suggested_actions": actions,
                        "model": model_name,
                        "provider": "openrouter",
                    }
                except (OpenRouterError, httpx.HTTPError, ValueError) as exc:
                    last_error = str(exc)
                    log.warning("OpenRouter chat reply failed for %s: %s", model_name, exc)

            if last_error:
                log.warning("OpenRouter chat reply fell back to local output: %s", last_error)

        last_user_message = next((message["content"] for message in reversed(messages) if message["role"] == "user"), "")
        fallback_reply = (
            "OpenClaw chat is running in local fallback mode. "
            f"I received: {last_user_message or 'an empty message'}."
        )
        return {
            "kind": "completed",
            "summary": "Generated a local fallback chat reply.",
            "reply": fallback_reply,
            "suggested_actions": [],
            "provider": "local",
            "model": None,
        }

    async def tool_chat_reply(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw_messages = arguments.get("messages") or []
        if not isinstance(raw_messages, list) or not raw_messages:
            return {"kind": "rejected", "summary": "chat.reply requires messages."}

        messages: list[dict[str, str]] = []
        for item in raw_messages:
            if not isinstance(item, dict):
                continue
            role = item.get("role") or "user"
            if role not in {"system", "user", "assistant"}:
                role = "user"
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            messages.append({"role": role, "content": content})

        if not messages:
            return {"kind": "rejected", "summary": "chat.reply requires non-empty messages."}

        policy_context = arguments.get("policy_context") or {}
        if has_runtime_bundle(arguments):
            try:
                runtime_request = build_runtime_chat_request(
                    arguments=arguments,
                    messages=messages,
                    policy_context=policy_context,
                )
            except RuntimeBundleValidationError as exc:
                return {"kind": "rejected", "summary": str(exc)}
            return await self._complete_chat_reply(
                runtime_request["messages"],
                chosen_model=runtime_request["model"],
                fallback_model=runtime_request["fallback_model"],
                temperature=runtime_request["temperature"],
                max_tokens=runtime_request["max_tokens"],
            )

        routed_reply = await self._build_cif_chat_reply(messages, policy_context)
        if routed_reply is None:
            routed_reply = self._route_chat_reply(messages, policy_context)
        if routed_reply is not None:
            return {
                "kind": "completed",
                "summary": "Generated a routed chat reply.",
                "reply": routed_reply.get("reply") or "",
                "suggested_actions": routed_reply.get("suggested_actions") or [],
                "model": "router",
                "provider": "local",
            }

        messages = self._inject_policy_system_prompt(messages, policy_context)

        chosen_model = (arguments.get("model") or settings.openrouter_model).strip()
        temperature = float(arguments.get("temperature", 0.5))
        max_tokens = int(arguments.get("max_tokens", 800))
        return await self._complete_chat_reply(
            messages,
            chosen_model=chosen_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def tool_shell_execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not settings.openclaw_shell_enabled:
            return {"kind": "rejected", "summary": "Shell execution is disabled by policy."}
        command = (arguments.get("command") or "").strip()
        cwd = (arguments.get("cwd") or settings.openclaw_workspace_root).strip()
        if not command:
            return {"kind": "rejected", "summary": "command is required."}
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await process.communicate()
        output = stdout.decode(errors="replace").strip()
        return {
            "kind": "completed" if process.returncode == 0 else "failed",
            "summary": output.splitlines()[-1] if output else f"Shell exited with {process.returncode}",
            "command": command,
            "cwd": cwd,
            "exit_code": process.returncode,
            "output": output,
        }

    @staticmethod
    def _decode_mcp_result(result: dict[str, Any] | Any) -> dict[str, Any]:
        if not isinstance(result, dict):
            return {"kind": "completed", "result": _json_safe(result)}
        content = result.get("content") or []
        if content and isinstance(content, list):
            first = content[0]
            if isinstance(first, dict) and first.get("type") == "text":
                text = first.get("text") or ""
                try:
                    decoded = json.loads(text)
                except json.JSONDecodeError:
                    decoded = {"text": text}
                if isinstance(decoded, dict):
                    return decoded
                return {"kind": "completed", "result": decoded}
        return _json_safe(result)


gateway = OpenClawMCPGateway()
