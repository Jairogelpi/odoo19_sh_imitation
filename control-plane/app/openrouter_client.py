from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from .config import settings


class OpenRouterError(RuntimeError):
    pass


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _extract_json(text: str) -> dict[str, Any]:
    stripped = _strip_code_fences(text)
    try:
        decoded = json.loads(stripped)
        if isinstance(decoded, dict):
            return decoded
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = stripped[start : end + 1]
        try:
            decoded = json.loads(candidate)
            if isinstance(decoded, dict):
                return decoded
        except json.JSONDecodeError:
            pass

    return {"summary": stripped}


@dataclass
class OpenRouterClient:
    api_key: str | None = settings.openrouter_api_key
    api_base: str = settings.openrouter_api_base
    default_model: str = settings.openrouter_model
    fallback_model: str = settings.openrouter_fallback_model
    reasoning_enabled: bool = settings.openrouter_reasoning_enabled
    timeout_seconds: int = settings.openrouter_timeout_seconds
    title: str = settings.openrouter_title
    referer: str = settings.openrouter_referer

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    @staticmethod
    def _supports_reasoning(model: str) -> bool:
        model = model.lower()
        return "glm-4.5" in model or "glm-5" in model or "reason" in model

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise OpenRouterError("OPENROUTER_API_KEY is not configured")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "HTTP-Referer": self.referer,
            "X-Title": self.title,
        }

    async def draft_plan(
        self,
        instruction: str,
        context: str = "",
        target: str = "",
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        chosen_model = (model or self.default_model).strip()
        system_prompt = (
            "You are the planning brain for an Odoo/OpenClaw agent. "
            "Return ONLY valid JSON. No markdown fences, no prose outside JSON. "
            "Optimize for practical execution: concise steps, explicit risks, and safe defaults. "
            "If the instruction is ambiguous, say what is missing instead of inventing facts."
        )
        user_prompt = json.dumps(
            {
                "instruction": instruction,
                "context": context,
                "target": target,
                "output_schema": {
                    "summary": "short human-readable summary",
                    "recommendation": "concise recommendation",
                    "steps": ["ordered step 1", "ordered step 2"],
                    "tools": ["optional tool names or capabilities"],
                    "risks": ["safety or quality risks"],
                    "confidence": "low|medium|high",
                },
            },
            ensure_ascii=False,
            indent=2,
        )

        payload: dict[str, Any] = {
            "model": chosen_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self.reasoning_enabled and self._supports_reasoning(chosen_model):
            payload["reasoning"] = {"enabled": True}

        endpoint = f"{self.api_base.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
            response = await client.post(endpoint, headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") or []
        if not choices:
            raise OpenRouterError("OpenRouter response did not include any choices")

        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        if isinstance(content, list):
            content = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )

        draft = _extract_json(str(content))
        draft.setdefault("summary", draft.get("recommendation") or "Generated draft plan.")
        draft.setdefault("recommendation", draft.get("summary"))
        draft.setdefault("steps", [])
        draft.setdefault("tools", [])
        draft.setdefault("risks", [])
        draft.setdefault("confidence", "medium")
        draft["provider"] = "openrouter"
        draft["model"] = chosen_model
        return draft