import base64
from urllib.parse import quote
from uuid import uuid4

from odoo import _, fields, models
from odoo.exceptions import AccessError

from ..bundle import build_bundle


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
    root_operation = fields.Char(readonly=True, index=True)
    source_module = fields.Char(readonly=True, index=True)
    source_path = fields.Char(readonly=True)
    git_revision = fields.Char(readonly=True, index=True)
    event_ids = fields.One2many("flight.recorder.event", "trace_id", readonly=True)
    event_count = fields.Integer(compute="_compute_event_count")

    _correlation_id_unique = models.Constraint(
        "UNIQUE(correlation_id)",
        "A Flight Recorder correlation ID must be unique.",
    )

    def _compute_event_count(self):
        grouped = self.env["flight.recorder.event"].read_group(
            [("trace_id", "in", self.ids)],
            ["trace_id"],
            ["trace_id"],
        )
        counts = {item["trace_id"][0]: item["trace_id_count"] for item in grouped}
        for trace in self:
            trace.event_count = counts.get(trace.id, 0)

    def action_export_incident(self):
        self.ensure_one()
        if not self.env.user.has_group("base.group_system"):
            raise AccessError(_("Only system administrators can export incident evidence."))
        events = self.event_ids.sorted("sequence")
        trace_data = {
            "correlation_id": self.correlation_id,
            "status": self.status,
            "started_at": fields.Datetime.to_string(self.started_at),
            "ended_at": fields.Datetime.to_string(self.ended_at) if self.ended_at else None,
            "root_model": self.root_model,
            "root_record_id": self.root_record_id,
            "root_operation": self.root_operation,
            "source_module": self.source_module,
            "source_path": self.source_path,
            "git_revision": self.git_revision,
        }
        event_data = [
            {
                "sequence": event.sequence,
                "parent_sequence": event.parent_event_id.sequence or None,
                "kind": event.kind,
                "model_name": event.model_name,
                "record_id": event.record_id,
                "operation": event.operation,
                "field_names": event.field_names,
                "source_module": event.source_module,
                "source_path": event.source_path,
                "occurred_at": fields.Datetime.to_string(event.occurred_at),
                "payload": event.payload,
                "payload_hash": event.payload_hash,
            }
            for event in events
        ]
        filename = f"{self.correlation_id}.odoo-incident"
        attachment = self.env["ir.attachment"].sudo().create(
            {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(build_bundle(trace_data, event_data)),
                "mimetype": "application/vnd.odoo.flight-recorder-incident+zip",
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": (
                f"/web/content/{attachment.id}/datas/"
                f"{quote(filename)}?download=true"
            ),
            "target": "self",
        }


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

    _trace_sequence_unique = models.Constraint(
        "UNIQUE(trace_id, sequence)",
        "Event sequence numbers must be unique inside a trace.",
    )
