from __future__ import annotations

import json
from typing import Any

from .config import settings
from .schema_validation import SchemaValidationError, validate_payload


class RuntimeBundleValidationError(ValueError):
    pass


def has_runtime_bundle(arguments: dict[str, Any]) -> bool:
    runtime_bundle = arguments.get("runtime_bundle")
    return isinstance(runtime_bundle, dict) and bool(runtime_bundle)


def validate_runtime_bundle(payload: Any) -> dict[str, Any]:
    try:
        return validate_payload(payload, "runtime_bundle.v1.json")
    except SchemaValidationError as exc:
        raise RuntimeBundleValidationError(f"runtime_bundle invalid: {exc}") from exc


def _coerce_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def build_runtime_chat_request(
    *,
    arguments: dict[str, Any],
    messages: list[dict[str, str]],
    policy_context: dict[str, Any],
) -> dict[str, Any]:
    runtime_bundle = validate_runtime_bundle(arguments.get("runtime_bundle"))
    llm_profile = runtime_bundle.get("llm_profile") or {}
    prompt_sections = runtime_bundle.get("prompt_sections") or {}
    instruction = (
        "Respond as a single JSON object with keys `reply` (string) and "
        "`suggested_actions` (array). `reply` is the user-facing text. "
        "Each suggested action must have `title`, `rationale`, `action_type`, "
        "`policy_key`, and `payload` (object). "
        f"Only use policy_key values from this list: {json.dumps(policy_context.get('available_policies') or [], ensure_ascii=False)}. "
        "Never invent new action_type aliases. "
        f"Resolved runtime bundle: {json.dumps(runtime_bundle, ensure_ascii=False)}. "
        "Follow these prompt sections in order: "
        f"{json.dumps(prompt_sections, ensure_ascii=False)}. "
        "Never include text outside the JSON."
    )
    bundle_messages = list(messages)
    bundle_messages.insert(0, {"role": "system", "content": instruction})

    model_name = _coerce_string(llm_profile.get("model_name")) or _coerce_string(arguments.get("model")) or settings.openrouter_model
    fallback_model = _coerce_string(llm_profile.get("fallback_model_name")) or settings.openrouter_fallback_model
    temperature = _coerce_float(arguments.get("temperature"), default=_coerce_float(llm_profile.get("temperature"), default=0.5))
    max_tokens = _coerce_int(arguments.get("max_tokens"), default=_coerce_int(llm_profile.get("max_tokens"), default=800))
    return {
        "runtime_bundle": runtime_bundle,
        "messages": bundle_messages,
        "model": model_name,
        "fallback_model": fallback_model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
