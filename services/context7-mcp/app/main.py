from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse


MCP_PORT = int(os.getenv("MCP_PORT", "8092"))
DOCS_ROOT = Path(os.getenv("CONTEXT7_DOCS_ROOT", "/docs")).resolve()
AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "").strip()

if not AUTH_TOKEN:
    raise RuntimeError("MCP_AUTH_TOKEN is required for context7-mcp")


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


def _catalog() -> list[dict[str, str]]:
    return [
        {
            "libraryId": "odoo/odoo-19",
            "name": "Odoo 19",
            "description": "Local Odoo 19 platform docs mounted from this repository.",
            "version": "19",
        },
        {
            "libraryId": "openclaw/platform",
            "name": "OpenClaw Platform",
            "description": "OpenClaw architecture, runbooks, and operational notes from the local docs vault.",
            "version": "local",
        },
    ]


def _score_library(library: dict[str, str], library_name: str, query: str) -> int:
    score = 0
    ln = library_name.lower().strip()
    q = query.lower().strip()

    lib_id = library["libraryId"].lower()
    name = library["name"].lower()
    desc = library["description"].lower()

    if ln and ln in name:
        score += 10
    if ln and ln in lib_id:
        score += 8
    if q:
        terms = [t for t in re.split(r"\W+", q) if t]
        for term in terms:
            if term in name:
                score += 4
            if term in desc:
                score += 2
            if term in lib_id:
                score += 2
    return score


def _resolve_library_id(arguments: dict) -> dict:
    library_name = str(arguments.get("libraryName") or "").strip()
    query = str(arguments.get("query") or "").strip()
    if not library_name:
        return {"kind": "rejected", "summary": "libraryName is required.", "result": []}

    ranked = []
    for library in _catalog():
        score = _score_library(library, library_name, query)
        ranked.append((score, library))

    ranked.sort(key=lambda item: item[0], reverse=True)
    results = []
    for score, library in ranked:
        if score <= 0:
            continue
        results.append(
            {
                "libraryId": library["libraryId"],
                "name": library["name"],
                "description": library["description"],
                "version": library["version"],
                "score": score,
            }
        )

    if not results:
        fallback = _catalog()[0]
        results = [
            {
                "libraryId": fallback["libraryId"],
                "name": fallback["name"],
                "description": fallback["description"],
                "version": fallback["version"],
                "score": 0,
            }
        ]

    return {
        "kind": "completed",
        "summary": f"Resolved {len(results)} candidate library id(s).",
        "result": results,
    }


def _collect_docs_files(library_id: str) -> list[Path]:
    if library_id == "odoo/odoo-19":
        candidates = [DOCS_ROOT]
    elif library_id == "openclaw/platform":
        candidates = [DOCS_ROOT / "brain", DOCS_ROOT / "runbooks"]
    else:
        candidates = [DOCS_ROOT]

    files: list[Path] = []
    for base in candidates:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.md")):
            files.append(path)
    return files


def _query_docs(arguments: dict) -> dict:
    library_id = str(arguments.get("libraryId") or "").strip()
    query = str(arguments.get("query") or "").strip()
    if not library_id or not query:
        return {"kind": "rejected", "summary": "libraryId and query are required.", "chunks": []}

    terms = [t.lower() for t in re.split(r"\W+", query) if t]
    if not terms:
        return {"kind": "rejected", "summary": "query must include searchable text.", "chunks": []}

    files = _collect_docs_files(library_id)
    chunks: list[dict] = []

    for path in files:
        rel = str(path.relative_to(DOCS_ROOT)).replace("\\", "/")
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        for line_no, line in enumerate(lines, start=1):
            lowered = line.lower()
            score = sum(1 for term in terms if term in lowered)
            if score <= 0:
                continue
            chunks.append(
                {
                    "libraryId": library_id,
                    "path": rel,
                    "line": line_no,
                    "score": score,
                    "snippet": line.strip()[:320],
                }
            )

    chunks.sort(key=lambda row: row["score"], reverse=True)
    chunks = chunks[:20]

    return {
        "kind": "completed",
        "summary": f"Found {len(chunks)} documentation chunk(s).",
        "libraryId": library_id,
        "query": query,
        "chunks": chunks,
    }


TOOLS = {
    "resolve-library-id": {
        "description": "Resolve a Context7 library identifier from a library name and query.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "libraryName": {"type": "string"},
                "query": {"type": "string"},
            },
            "required": ["libraryName"],
            "additionalProperties": False,
        },
        "handler": _resolve_library_id,
    },
    "query-docs": {
        "description": "Query local documentation chunks by libraryId and natural-language query.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "libraryId": {"type": "string"},
                "query": {"type": "string"},
            },
            "required": ["libraryId", "query"],
            "additionalProperties": False,
        },
        "handler": _query_docs,
    },
}


class MCPHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/healthz":
            _json_response(self, 200, {"status": "ok", "service": "context7-mcp"})
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
                self,
                200,
                {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "context7-mcp", "version": "1.0.0"},
                        "capabilities": {"tools": {"listChanged": False}},
                    },
                },
            )
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
    DOCS_ROOT.mkdir(parents=True, exist_ok=True)
    server = HTTPServer(("0.0.0.0", MCP_PORT), MCPHandler)
    server.serve_forever()
