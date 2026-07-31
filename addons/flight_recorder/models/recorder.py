"""Small, explicit recording service for the first causal tracing slice."""

from __future__ import annotations

import inspect
import json
import os
from hashlib import sha256
from typing import Any

from odoo import fields, models

TRACE_CONTEXT_KEY = "_flight_recorder_trace_id"
PARENT_CONTEXT_KEY = "_flight_recorder_parent_event_id"


class FlightRecorderService(models.AbstractModel):
    _name = "flight.recorder.service"
    _description = "Flight Recorder Service"

    def source_metadata(self, method) -> dict[str, Any]:
        """Return portable source attribution without leaking server paths."""
        function = inspect.unwrap(getattr(method, "__func__", method))
        module_name = getattr(function, "__module__", "") or ""
        parts = module_name.split(".")
        source_module = ""
        source_path = ""
        if "addons" in parts:
            addon_index = parts.index("addons") + 1
            if addon_index < len(parts):
                source_module = parts[addon_index]
                source_path = "/".join(parts[addon_index:]) + ".py"
        elif module_name:
            source_module = parts[0]
            source_path = module_name.replace(".", "/") + ".py"

        try:
            source_line = inspect.getsourcelines(function)[1]
        except (OSError, TypeError):
            source_line = None

        return {
            "source_module": source_module or None,
            "source_path": source_path or None,
            "source_line": source_line,
        }

    def begin_trace(self, records, *, operation: str, source: dict[str, Any]):
        """Create an administrator-readable trace for an explicit business action."""
        return self.env["flight.recorder.trace"].sudo().create(
            {
                "actor_id": self.env.user.id,
                "root_model": records._name,
                "root_record_id": records.id if len(records) == 1 else 0,
                "root_operation": operation,
                "source_module": source.get("source_module"),
                "source_path": source.get("source_path"),
                "git_revision": os.getenv("ODOO_FLIGHT_RECORDER_GIT_REVISION"),
            }
        )

    def append_event(
        self,
        trace,
        *,
        kind: str,
        operation: str,
        model_name: str | None = None,
        record_id: int | None = None,
        field_names: list[str] | None = None,
        parent_event=None,
        source: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ):
        """Append one immutable, metadata-only fact to a trace."""
        safe_payload = {
            "capture_mode": "metadata",
            **(payload or {}),
        }
        sequence = self.env["flight.recorder.event"].sudo().search_count(
            [("trace_id", "=", trace.id)]
        ) + 1
        digest_input = {
            "trace": trace.correlation_id,
            "sequence": sequence,
            "kind": kind,
            "operation": operation,
            "model": model_name,
            "record_id": record_id,
            "field_names": sorted(field_names or []),
            "parent_sequence": parent_event.sequence if parent_event else None,
            "source_module": (source or {}).get("source_module"),
            "source_path": (source or {}).get("source_path"),
            "payload": safe_payload,
        }
        payload_hash = sha256(
            json.dumps(
                digest_input,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode()
        ).hexdigest()
        return self.env["flight.recorder.event"].sudo().create(
            {
                "trace_id": trace.id,
                "sequence": sequence,
                "parent_event_id": parent_event.id if parent_event else False,
                "kind": kind,
                "model_name": model_name,
                "record_id": record_id or 0,
                "operation": operation,
                "field_names": sorted(field_names or []),
                "source_module": (source or {}).get("source_module"),
                "source_path": (source or {}).get("source_path"),
                "payload": safe_payload,
                "payload_hash": payload_hash,
            }
        )

    def complete_trace(self, trace):
        trace.sudo().write(
            {
                "status": "completed",
                "ended_at": fields.Datetime.now(),
            }
        )
