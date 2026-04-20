"""HTTP MCP server for lead mining via OpenStreetMap (free).

JSON-RPC endpoint POST /mcp. Tools:
  - lead.categories → list supported business categories.
  - lead.search     → query Overpass by area/bbox + category, return normalised leads.

No writes to Odoo. The caller (openclaw_lead_mining wizard) decides which leads
to persist as crm.lead and applies policy/approval upstream.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

from .overpass import SUPPORTED_CATEGORIES, search_leads

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lead-mining-mcp")

MCP_PORT = int(os.getenv("MCP_PORT", "8094"))
AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "").strip()


def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _tool_payload(value: dict) -> dict:
    return {
        "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}],
        "isError": bool(value.get("error")),
    }


async def _tool_categories(_arguments: dict) -> dict:
    return {"error": False, "categories": sorted(SUPPORTED_CATEGORIES.keys())}


async def _tool_search(arguments: dict) -> dict:
    category = str(arguments.get("category") or "").strip().lower()
    if not category:
        return {"error": True, "mensaje": "category es obligatorio (usa lead.categories)."}
    area_name = (arguments.get("area_name") or "").strip() or None
    bbox = arguments.get("bbox")
    return await search_leads(
        category=category,
        area_name=area_name,
        bbox=bbox,
        require_website=bool(arguments.get("require_website", True)),
        require_phone=bool(arguments.get("require_phone", True)),
        limit=int(arguments.get("limit", 50)),
    )


TOOLS = {
    "lead.categories": {
        "description": "List supported OSM categories (use one of these as `category` in lead.search).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
        "handler": _tool_categories,
    },
    "lead.search": {
        "description": (
            "Search businesses in OpenStreetMap by area or bounding box and category. Results "
            "include name/phone/website/email/address when present, plus lat/lon and OSM id. "
            "Pass `area_name` OR `bbox` [south,west,north,east]."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "One of lead.categories output."},
                "area_name": {"type": "string", "description": "Administrative area name, e.g. 'Madrid'."},
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
        "handler": _tool_search,
    },
}


class MCPHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        logger.info("%s - %s", self.address_string(), format % args)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            _json_response(self, 200, {"status": "ok", "service": "lead-mining-mcp"})
            return
        _json_response(self, 404, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/mcp":
            _json_response(self, 404, {"error": "Not found"})
            return

        if AUTH_TOKEN:
            authz = self.headers.get("Authorization", "")
            if authz != f"Bearer {AUTH_TOKEN}":
                _json_response(self, 401, {"error": "Unauthorized"})
                return

        raw_len = int(self.headers.get("Content-Length", "0"))
        if raw_len <= 0:
            _json_response(self, 400, {"error": "Empty payload"})
            return
        payload = self.rfile.read(raw_len)

        try:
            request = json.loads(payload)
        except json.JSONDecodeError:
            _json_response(self, 400, {"error": "Invalid JSON"})
            return

        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}

        if method == "initialize":
            _json_response(
                self, 200,
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "lead-mining-mcp", "version": "1.0.0"},
                        "capabilities": {"tools": {"listChanged": False}},
                    },
                },
            )
            return

        if method == "tools/list":
            tools = [
                {"name": name, "description": cfg["description"], "inputSchema": cfg["inputSchema"]}
                for name, cfg in TOOLS.items()
            ]
            _json_response(self, 200, {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}})
            return

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}
            tool_cfg = TOOLS.get(tool_name)
            if not tool_cfg:
                _json_response(
                    self, 200,
                    {"jsonrpc": "2.0", "id": request_id,
                     "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"}},
                )
                return

            try:
                result = asyncio.run(tool_cfg["handler"](arguments))
            except Exception as exc:
                logger.exception("tool %s failed", tool_name)
                _json_response(
                    self, 200,
                    {"jsonrpc": "2.0", "id": request_id,
                     "error": {"code": -32000, "message": str(exc)}},
                )
                return

            _json_response(
                self, 200,
                {"jsonrpc": "2.0", "id": request_id, "result": _tool_payload(result)},
            )
            return

        _json_response(
            self, 200,
            {"jsonrpc": "2.0", "id": request_id,
             "error": {"code": -32601, "message": f"Unknown method: {method}"}},
        )


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", MCP_PORT), MCPHandler)
    logger.info("lead-mining-mcp listening on :%d", MCP_PORT)
    server.serve_forever()
