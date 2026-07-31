from typing import ClassVar
from uuid import uuid4

from odoo import fields, models


class FlightRecorderTrace(models.Model):
    _name = "flight.recorder.trace"
    _description = "Flight Recorder Trace"
    _order = "started_at desc, id desc"

    correlation_id = fields.Char(
        required=True,
        readonly=True,
        index=True,
        default=lambda self: str(uuid4()),
    )
    status = fields.Selection(
        [
            ("recording", "Recording"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        required=True,
        readonly=True,
        default="recording",
        index=True,
    )
    started_at = fields.Datetime(required=True, readonly=True, default=fields.Datetime.now)
    ended_at = fields.Datetime(readonly=True)
    actor_id = fields.Many2one("res.users", readonly=True, index=True)
    root_model = fields.Char(readonly=True, index=True)
    root_record_id = fields.Integer(readonly=True, index=True)
    git_revision = fields.Char(readonly=True, index=True)
    event_ids = fields.One2many("flight.recorder.event", "trace_id", readonly=True)
    event_count = fields.Integer(compute="_compute_event_count")

    _sql_constraints: ClassVar[list[tuple[str, str, str]]] = [
        (
            "correlation_id_unique",
            "unique(correlation_id)",
            "A Flight Recorder correlation ID must be unique.",
        ),
    ]

    def _compute_event_count(self):
        grouped = self.env["flight.recorder.event"].read_group(
            [("trace_id", "in", self.ids)],
            ["trace_id"],
            ["trace_id"],
        )
        counts = {item["trace_id"][0]: item["trace_id_count"] for item in grouped}
        for trace in self:
            trace.event_count = counts.get(trace.id, 0)


class FlightRecorderEvent(models.Model):
    _name = "flight.recorder.event"
    _description = "Flight Recorder Event"
    _order = "trace_id, sequence, id"

    trace_id = fields.Many2one(
        "flight.recorder.trace",
        required=True,
        readonly=True,
        index=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(required=True, readonly=True)
    parent_event_id = fields.Many2one(
        "flight.recorder.event",
        readonly=True,
        index=True,
        ondelete="set null",
    )
    kind = fields.Selection(
        [
            ("request", "Request"),
            ("method", "Method"),
            ("orm", "ORM Mutation"),
            ("automation", "Automation"),
            ("cron", "Scheduled Action"),
            ("external", "External Call"),
            ("error", "Error"),
        ],
        required=True,
        readonly=True,
        index=True,
    )
    model_name = fields.Char(readonly=True, index=True)
    record_id = fields.Integer(readonly=True, index=True)
    operation = fields.Char(readonly=True, index=True)
    field_names = fields.Json(readonly=True)
    source_module = fields.Char(readonly=True, index=True)
    source_path = fields.Char(readonly=True)
    payload = fields.Json(readonly=True)
    payload_hash = fields.Char(required=True, readonly=True, index=True)
    occurred_at = fields.Datetime(required=True, readonly=True, default=fields.Datetime.now)

    _sql_constraints: ClassVar[list[tuple[str, str, str]]] = [
        (
            "trace_sequence_unique",
            "unique(trace_id, sequence)",
            "Event sequence numbers must be unique inside a trace.",
        ),
    ]
