"""Framework-independent primitives for Flight Recorder for Odoo."""

from .events import EventEnvelope
from .redaction import REDACTED, redact

__all__ = ["REDACTED", "EventEnvelope", "redact"]
