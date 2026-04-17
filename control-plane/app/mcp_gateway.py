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
