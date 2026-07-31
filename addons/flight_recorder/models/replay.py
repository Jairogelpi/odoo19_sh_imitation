"""R3 replay service. It only runs inside the disposable replay worker."""

from __future__ import annotations

import os

from odoo import _, models
from odoo.exceptions import UserError

from ..bundle import compare_event_streams, read_bundle

REPLAY_CONTEXT_KEY = "_flight_recorder_replay"
REPLAY_DATABASE_PREFIX = "flight_recorder_replay_"


class FlightRecorderReplayService(models.AbstractModel):
    _name = "flight.recorder.replay.service"
    _description = "Flight Recorder Isolated Replay Service"

    def _assert_isolated_worker(self):
        if os.getenv("FLIGHT_RECORDER_REPLAY_ISOLATED") != "1":
            raise UserError(_("Replay is allowed only inside the isolated replay worker."))
        if not self.env.cr.dbname.startswith(REPLAY_DATABASE_PREFIX):
            raise UserError(_("Replay requires a disposable replay database."))

    def _synthetic_sale_order(self, incident_id: str):
        suffix = incident_id[:12]
        partner = self.env["res.partner"].create(
            {"name": f"Flight Recorder Replay Customer {suffix}"}
        )
        product = self.env["product.product"].create(
            {
                "name": f"Flight Recorder Replay Product {suffix}",
                "list_price": 25.0,
            }
        )
        return self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": 25.0,
                        },
                    )
                ],
            }
        )

    def replay_bundle(self, data: bytes):
        self._assert_isolated_worker()
        documents = read_bundle(data)
        manifest = documents["manifest"]
        original_document = documents["events"]
        trace_metadata = original_document["trace"]
        if (
            trace_metadata.get("root_model") != "sale.order"
            or trace_metadata.get("root_operation") != "action_confirm"
        ):
            raise UserError(_("R3 currently replays only sale-order confirmation incidents."))

        order = self._synthetic_sale_order(manifest["incident_id"])
        order.with_context(**{REPLAY_CONTEXT_KEY: True}).action_confirm()
        replay_trace = self.env["flight.recorder.trace"].sudo().search(
            [
                ("root_model", "=", "sale.order"),
                ("root_record_id", "=", order.id),
                ("root_operation", "=", "action_confirm"),
            ],
            order="id desc",
            limit=1,
        )
        if not replay_trace:
            raise UserError(_("Replay produced no Flight Recorder trace."))

        observed = [
            {
                "sequence": event.sequence,
                "parent_sequence": event.parent_event_id.sequence or None,
                "kind": event.kind,
                "model_name": event.model_name,
                "operation": event.operation,
                "field_names": event.field_names,
            }
            for event in replay_trace.event_ids.sorted("sequence")
        ]
        comparison = compare_event_streams(original_document["events"], observed)
        return {
            "schema": "odoo-flight-recorder.replay-report",
            "schema_version": 1,
            "incident_id": manifest["incident_id"],
            "replay_trace_id": replay_trace.correlation_id,
            "root_model": trace_metadata["root_model"],
            "root_operation": trace_metadata["root_operation"],
            "safety": {
                "database": "disposable",
                "network_egress": "denied",
                "cron": "disabled",
                "external_email": "denied_by_network",
                "external_payment": "denied_by_network",
                "external_http": "denied_by_network",
            },
            **comparison,
        }
