"""HTTP MCP server for Spanish CIF lookup.

Exposes two tools over JSON-RPC at POST /mcp:
  - cif.validate   — format-only validation (no network).
  - cif.lookup     — scrape public sources + optional Google Maps enrichment.

Writes to Odoo res.partner are intentionally NOT exposed here. The caller
(OpenClaw) must route the mapped payload through its own permission flow
so that policy, approval, and audit apply.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

from .lookup import buscar_empresa, mapear_a_res_partner, validar_cif

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cif-lookup-mcp")

MCP_PORT = int(os.getenv("MCP_PORT", "8093"))
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


async def _tool_validate(arguments: dict) -> dict:
    cif = str(arguments.get("cif") or "").strip()
    if not cif:
        return {"error": True, "mensaje": "Debes proporcionar un CIF."}
    ok, norm = validar_cif(cif)
    return {
        "error": False,
        "cif_original": cif,
        "cif_normalizado": norm,
        "es_valido": ok,
        "mensaje": "Formato válido." if ok else f"'{cif}' no es un CIF válido.",
    }


async def _tool_lookup(arguments: dict) -> dict:
    cif = str(arguments.get("cif") or "").strip()
    if not cif:
        return {"error": True, "mensaje": "Debes proporcionar un CIF."}
    datos = await buscar_empresa(cif)
    if arguments.get("include_partner_mapping") and not datos.get("error"):
        datos["_res_partner"] = mapear_a_res_partner(datos)
    return datos


TOOLS = {
    "cif.validate": {
        "description": "Validate the format of a Spanish CIF without any network call.",
        "inputSchema": {
            "type": "object",
            "properties": {"cif": {"type": "string", "description": "Spanish CIF, e.g. B12345678"}},
            "required": ["cif"],
            "additionalProperties": False,
        },
        "handler": _tool_validate,
    },
    "cif.lookup": {
        "description": (
            "Look up a Spanish company by CIF across public sources (infocif, infoempresa, "
            "axesor) and optionally enrich phone/website with Google Maps. Pass "
            "include_partner_mapping=true to also receive a values dict ready for Odoo res.partner."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cif": {"type": "string"},
                "include_partner_mapping": {"type": "boolean", "default": False},
            },
            "required": ["cif"],
            "additionalProperties": False,
        },
        "handler": _tool_lookup,
    },
}


class MCPHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        logger.info("%s - %s", self.address_string(), format % args)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            _json_response(self, 200, {"status": "ok", "service": "cif-lookup-mcp"})
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
                        "serverInfo": {"name": "cif-lookup-mcp", "version": "1.0.0"},
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
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"},
                    },
                )
                return

            try:
                result = asyncio.run(tool_cfg["handler"](arguments))
            except Exception as exc:
                logger.exception("tool %s failed", tool_name)
                _json_response(
                    self, 200,
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32000, "message": str(exc)},
                    },
                )
                return

            _json_response(
                self, 200,
                {"jsonrpc": "2.0", "id": request_id, "result": _tool_payload(result)},
            )
            return

        _json_response(
            self, 200,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unknown method: {method}"},
            },
        )


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", MCP_PORT), MCPHandler)
    logger.info("cif-lookup-mcp listening on :%d", MCP_PORT)
    server.serve_forever()
