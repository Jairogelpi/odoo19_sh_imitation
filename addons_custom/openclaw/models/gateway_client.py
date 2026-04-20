from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from itertools import count
from typing import Any


class OpenClawGatewayError(RuntimeError):
    pass


@dataclass
class OpenClawGatewayClient:
    base_url: str
    timeout: int = 60
    client_name: str = "openclaw"
    client_version: str = "19.0.1.0.0"

    def __post_init__(self) -> None:
        self._request_ids = count(1)

    def initialize(self) -> dict[str, Any]:
        result = self._rpc(
            "initialize",
            {
                "clientInfo": {
                    "name": self.client_name,
                    "version": self.client_version,
                },
                "capabilities": {"tools": {}},
            },
        )
        return result if isinstance(result, dict) else {}

    def list_tools(self) -> dict[str, Any]:
        result = self._rpc("tools/list")
        return result if isinstance(result, dict) else {}

    def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
        result = self._rpc(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments or {},
            },
        )
        return self._decode_result(result)

    def chat_reply(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float = 0.5,
        max_tokens: int = 800,
        runtime_bundle: dict[str, Any] | None = None,
        policy_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        arguments: dict[str, Any] = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if model:
            arguments["model"] = model
        if runtime_bundle:
            arguments["runtime_bundle"] = runtime_bundle
        if policy_context:
            arguments["policy_context"] = policy_context
        result = self._rpc(
            "tools/call",
            {"name": "chat.reply", "arguments": arguments},
        )
        decoded = self._decode_result(result)
        if isinstance(decoded, dict):
            reply = decoded.get("reply") or decoded.get("summary") or ""
            raw_actions = decoded.get("suggested_actions")
            actions = raw_actions if isinstance(raw_actions, list) else []
            return {
                "reply": str(reply),
                "suggested_actions": actions,
                "provider": decoded.get("provider") or "",
                "model": decoded.get("model"),
                "kind": decoded.get("kind") or "completed",
            }
        return {
            "reply": str(decoded) if decoded is not None else "",
            "suggested_actions": [],
            "provider": "",
            "model": None,
            "kind": "completed",
        }

    def _rpc(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if not self.base_url:
            raise OpenClawGatewayError("MCP gateway URL is not configured")

        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": next(self._request_ids),
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/mcp",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise OpenClawGatewayError(f"Gateway HTTP {exc.code}: {error_body}") from exc
        except OSError as exc:
            raise OpenClawGatewayError(str(exc)) from exc

        decoded = json.loads(raw_body)
        if isinstance(decoded, dict) and decoded.get("error"):
            error = decoded["error"]
            raise OpenClawGatewayError(error.get("message", "Gateway error"))
        return decoded.get("result") if isinstance(decoded, dict) else decoded

    @staticmethod
    def _decode_result(result: Any) -> Any:
        if not isinstance(result, dict):
            return result
        content = result.get("content") or []
        if content and isinstance(content, list):
            first = content[0]
            if isinstance(first, dict) and first.get("type") == "text":
                text = first.get("text") or ""
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"kind": "completed", "text": text}
        return result
