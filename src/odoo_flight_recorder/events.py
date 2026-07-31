"""Stable event envelopes shared by the Odoo addon and future replay workers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
from uuid import uuid4


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    """One immutable fact in a causal Odoo trace.

    Payloads must already be redacted. The envelope deliberately has no
    framework dependency so incident bundles can be verified without Odoo.
    """

    kind: str
    trace_id: str
    sequence: int
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    parent_event_id: str | None = None
    occurred_at: datetime = field(default_factory=_utc_now)
    schema_version: int = 1

    def canonical_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["occurred_at"] = self.occurred_at.astimezone(timezone.utc).isoformat()
        return data

    def canonical_json(self) -> str:
        return json.dumps(
            self.canonical_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    def digest(self) -> str:
        return sha256(self.canonical_json().encode("utf-8")).hexdigest()
