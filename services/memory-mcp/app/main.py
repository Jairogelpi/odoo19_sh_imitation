from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse


MCP_PORT = int(os.getenv("MCP_PORT", "8091"))
STORE_FILE = Path(os.getenv("MEMORY_STORE_FILE", "/data/memory_store.json")).resolve()
AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "").strip()
STORE_LOCK = Lock()

if not AUTH_TOKEN:
    raise RuntimeError("MCP_AUTH_TOKEN is required for memory-mcp")


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
        "isError": False,
    }


def _load_store() -> dict[str, str]:
    if not STORE_FILE.exists():
        return {}
    try:
        raw = STORE_FILE.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in data.items():
        result[str(key)] = str(value)
    return result


def _save_store(data: dict[str, str]) -> None:
    STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STORE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def _memory_get(arguments: dict) -> dict:
    key = str(arguments.get("key") or "").strip()
    if not key:
        return {"kind": "rejected", "summary": "key is required."}
    with STORE_LOCK:
        store = _load_store()
    if key not in store:
        return {"kind": "failed", "summary": f"Key not found: {key}", "key": key}
    return {"kind": "completed", "summary": f"Loaded key: {key}", "key": key, "value": store[key]}


def _memory_set(arguments: dict) -> dict:
    key = str(arguments.get("key") or "").strip()
    if not key:
        return {"kind": "rejected", "summary": "key is required."}
    value = arguments.get("value")
    value_str = "" if value is None else str(value)
    with STORE_LOCK:
        store = _load_store()
        store[key] = value_str
        _save_store(store)
    return {"kind": "completed", "summary": f"Stored key: {key}", "key": key}


def _memory_delete(arguments: dict) -> dict:
    key = str(arguments.get("key") or "").strip()
    if not key:
        return {"kind": "rejected", "summary": "key is required."}
    with STORE_LOCK:
        store = _load_store()
        existed = key in store
        if existed:
            del store[key]
            _save_store(store)
    if existed:
        return {"kind": "completed", "summary": f"Deleted key: {key}", "key": key}
    return {"kind": "failed", "summary": f"Key not found: {key}", "key": key}


def _memory_list(arguments: dict) -> dict:
    prefix = str(arguments.get("prefix") or "")
    with STORE_LOCK:
        store = _load_store()
    items = []
    for key, value in sorted(store.items(), key=lambda kv: kv[0]):
        if prefix and not key.startswith(prefix):
            continue
        items.append({"key": key, "value": value})
    return {"kind": "completed", "summary": f"Listed {len(items)} item(s).", "items": items}


TOOLS = {
    "memory.get": {
        "description": "Get a stored value by key.",
        "inputSchema": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
            "additionalProperties": False,
        },
        "handler": _memory_get,
    },
    "memory.set": {
        "description": "Set a key/value in persistent memory store.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["key", "value"],
            "additionalProperties": False,
        },
        "handler": _memory_set,
    },
    "memory.delete": {
        "description": "Delete a key from persistent memory store.",
        "inputSchema": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
            "additionalProperties": False,
        },
        "handler": _memory_delete,
    },
    "memory.list": {
        "description": "List stored keys with optional prefix filtering.",
        "inputSchema": {
            "type": "object",
            "properties": {"prefix": {"type": "string"}},
            "additionalProperties": False,
        },
        "handler": _memory_list,
    },
}


class MCPHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            _json_response(self, 200, {"status": "ok", "service": "memory-mcp"})
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
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "memory-mcp", "version": "1.0.0"},
                    "capabilities": {"tools": {"listChanged": False}},
                },
            }
            _json_response(self, 200, response)
            return

        if method == "tools/list":
            tools = []
            for name, cfg in TOOLS.items():
                tools.append(
                    {
                        "name": name,
                        "description": cfg["description"],
                        "inputSchema": cfg["inputSchema"],
                    }
                )
            _json_response(self, 200, {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}})
            return

        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments") or {}
            tool_cfg = TOOLS.get(tool_name)
            if not tool_cfg:
                _json_response(
                    self,
                    200,
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"},
                    },
                )
                return

            try:
                result_payload = tool_cfg["handler"](arguments)
            except Exception as exc:  # pragma: no cover
                _json_response(
                    self,
                    200,
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32000, "message": str(exc)},
                    },
                )
                return

            _json_response(self, 200, {"jsonrpc": "2.0", "id": request_id, "result": _tool_payload(result_payload)})
            return

        _json_response(
            self,
            200,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unknown method: {method}"},
            },
        )


if __name__ == "__main__":
    STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STORE_FILE.exists():
        _save_store({})
    server = HTTPServer(("0.0.0.0", MCP_PORT), MCPHandler)
    server.serve_forever()
