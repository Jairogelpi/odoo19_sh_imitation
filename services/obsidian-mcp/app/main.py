from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse


MCP_PORT = int(os.getenv("MCP_PORT", "8090"))
VAULT_ROOT = Path(os.getenv("OBSIDIAN_VAULT_ROOT", "/vault")).resolve()
AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "").strip()

if not AUTH_TOKEN:
    raise RuntimeError("MCP_AUTH_TOKEN is required for obsidian-mcp")


def _json_response(handler: BaseHTTPRequestHandler, code: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _safe_path(relative_path: str) -> Path:
    cleaned = (relative_path or "").strip().lstrip("/")
    candidate = (VAULT_ROOT / cleaned).resolve()
    if not str(candidate).startswith(str(VAULT_ROOT)):
        raise ValueError("Path escapes vault root")
    return candidate


def _tool_payload(value: dict) -> dict:
    return {
        "content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}],
        "isError": False,
    }


def _list_notes(arguments: dict) -> dict:
    relative_dir = str(arguments.get("path") or "")
    target = _safe_path(relative_dir)
    if not target.exists():
        return {"kind": "failed", "summary": f"Path not found: {relative_dir}", "notes": []}
    if target.is_file():
        if target.suffix.lower() == ".md":
            rel = str(target.relative_to(VAULT_ROOT)).replace("\\", "/")
            return {"kind": "completed", "summary": "Listed 1 note.", "notes": [rel]}
        return {"kind": "completed", "summary": "Listed 0 notes.", "notes": []}

    notes: list[str] = []
    for path in sorted(target.rglob("*.md")):
        notes.append(str(path.relative_to(VAULT_ROOT)).replace("\\", "/"))
    return {"kind": "completed", "summary": f"Listed {len(notes)} notes.", "notes": notes}


def _read_note(arguments: dict) -> dict:
    note_path = str(arguments.get("path") or "")
    if not note_path:
        return {"kind": "rejected", "summary": "path is required."}
    target = _safe_path(note_path)
    if not target.exists() or not target.is_file():
        return {"kind": "failed", "summary": f"Note not found: {note_path}"}
    content = target.read_text(encoding="utf-8")
    return {
        "kind": "completed",
        "summary": f"Read note: {note_path}",
        "path": str(target.relative_to(VAULT_ROOT)).replace("\\", "/"),
        "content": content,
    }


def _write_note(arguments: dict) -> dict:
    note_path = str(arguments.get("path") or "")
    content = str(arguments.get("content") or "")
    if not note_path:
        return {"kind": "rejected", "summary": "path is required."}
    target = _safe_path(note_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="\n")
    return {
        "kind": "completed",
        "summary": f"Wrote note: {note_path}",
        "path": str(target.relative_to(VAULT_ROOT)).replace("\\", "/"),
        "bytes_written": len(content.encode("utf-8")),
    }


def _search_notes(arguments: dict) -> dict:
    query = str(arguments.get("query") or "").strip().lower()
    max_results = int(arguments.get("max_results") or 20)
    if not query:
        return {"kind": "rejected", "summary": "query is required.", "results": []}

    results: list[dict] = []
    for path in sorted(VAULT_ROOT.rglob("*.md")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        rel = str(path.relative_to(VAULT_ROOT)).replace("\\", "/")
        for idx, line in enumerate(lines, start=1):
            if query in line.lower():
                results.append({"path": rel, "line": idx, "snippet": line.strip()[:240]})
                if len(results) >= max_results:
                    return {
                        "kind": "completed",
                        "summary": f"Found {len(results)} hit(s).",
                        "results": results,
                    }
    return {"kind": "completed", "summary": f"Found {len(results)} hit(s).", "results": results}


TOOLS = {
    "obsidian.list_notes": {
        "description": "List markdown notes under the Obsidian vault.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "additionalProperties": False,
        },
        "handler": _list_notes,
    },
    "obsidian.read_note": {
        "description": "Read a markdown note from the Obsidian vault.",
        "inputSchema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
        "handler": _read_note,
    },
    "obsidian.write_note": {
        "description": "Write a markdown note inside the Obsidian vault.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
        "handler": _write_note,
    },
    "obsidian.search_notes": {
        "description": "Search a text query across markdown notes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 200},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "handler": _search_notes,
    },
}


class MCPHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            _json_response(self, 200, {"status": "ok", "service": "obsidian-mcp"})
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
                    "serverInfo": {"name": "obsidian-mcp", "version": "1.0.0"},
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
    VAULT_ROOT.mkdir(parents=True, exist_ok=True)
    server = HTTPServer(("0.0.0.0", MCP_PORT), MCPHandler)
    server.serve_forever()
