"""Privacy-first redaction for trace metadata and future incident bundles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

REDACTED = "[REDACTED]"

DEFAULT_SECRET_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "cookie",
        "credit_card",
        "cvv",
        "password",
        "refresh_token",
        "secret",
        "session_id",
        "token",
    }
)


def _normalized_key(value: object) -> str:
    return str(value).strip().lower().replace("-", "_")


def redact(
    value: Any,
    *,
    secret_keys: frozenset[str] = DEFAULT_SECRET_KEYS,
    allow_value_capture: bool = False,
) -> Any:
    """Return a safe copy of nested trace data.

    Known secret keys are always denied. When value capture is disabled, scalar
    values are replaced while keys and container structure remain available for
    diagnostics.
    """

    if isinstance(value, Mapping):
        return {
            str(key): (
                REDACTED
                if _normalized_key(key) in secret_keys
                else redact(
                    item,
                    secret_keys=secret_keys,
                    allow_value_capture=allow_value_capture,
                )
            )
            for key, item in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            redact(
                item,
                secret_keys=secret_keys,
                allow_value_capture=allow_value_capture,
            )
            for item in value
        ]

    if value is None:
        return value

    return value if allow_value_capture else REDACTED
