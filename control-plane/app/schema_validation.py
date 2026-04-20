from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class SchemaValidationError(ValueError):
    pass


_SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "shared" / "openclaw_schemas"


@lru_cache(maxsize=None)
def load_schema(schema_name: str) -> dict[str, Any]:
    schema_path = _SCHEMA_ROOT / schema_name
    with schema_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=None)
def _validator(schema_name: str) -> Draft202012Validator:
    return Draft202012Validator(load_schema(schema_name))


def _format_error(error) -> str:
    path = ".".join(str(part) for part in error.absolute_path)
    if path:
        return f"{path}: {error.message}"
    return error.message


def validate_payload(payload: Any, schema_name: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SchemaValidationError("payload must be a JSON object")
    errors = sorted(_validator(schema_name).iter_errors(payload), key=lambda item: list(item.absolute_path))
    if errors:
        raise SchemaValidationError(_format_error(errors[0]))
    return payload
