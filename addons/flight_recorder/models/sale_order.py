"""Explicit R1 instrumentation for sale-order confirmation."""

from odoo import models

from .recorder import PARENT_CONTEXT_KEY, TRACE_CONTEXT_KEY


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _flight_recorder_snapshot(self):
        """Keep compared values in memory; they are never written to trace payloads."""
        return {
            "orders": {order.id: order.state for order in self},
            "lines": {
                line.id: line.price_unit
                for line in self.order_line
                if line.display_type is False
            },
        }

    def _flight_recorder_changed_fields(self, before):
        changes = []
        for order in self:
            if before["orders"].get(order.id) != order.state:
                changes.append(("sale.order", order.id, ["state"]))
        for line in self.order_line.filtered(lambda item: not item.display_type):
            if before["lines"].get(line.id) != line.price_unit:
                changes.append(("sale.order.line", line.id, ["price_unit"]))
        return changes

    def action_confirm(self):
        if self.env.context.get(TRACE_CONTEXT_KEY):
            return super().action_confirm()

        recorder = self.env["flight.recorder.service"]
        next_method = super().action_confirm
        source = recorder.source_metadata(next_method)
        trace = recorder.begin_trace(self, operation="action_confirm", source=source)
        request_event = recorder.append_event(
            trace,
            kind="request",
            operation="sale_order_confirm",
            model_name=self._name,
            record_id=self.id if len(self) == 1 else None,
            source=source,
            payload={"record_count": len(self)},
        )
        method_event = recorder.append_event(
            trace,
            kind="method",
            operation="action_confirm",
            model_name=self._name,
            record_id=self.id if len(self) == 1 else None,
            parent_event=request_event,
            source=source,
        )
        before = self._flight_recorder_snapshot()
        traced_orders = self.with_context(
            **{
                TRACE_CONTEXT_KEY: trace.id,
                PARENT_CONTEXT_KEY: method_event.id,
            }
        )
        result = super(SaleOrder, traced_orders).action_confirm()

        for model_name, record_id, field_names in traced_orders._flight_recorder_changed_fields(
            before
        ):
            recorder.append_event(
                trace,
                kind="orm",
                operation="write",
                model_name=model_name,
                record_id=record_id,
                field_names=field_names,
                parent_event=method_event,
                source=source,
                payload={"changed_field_count": len(field_names)},
            )
        recorder.complete_trace(trace)
        return result
