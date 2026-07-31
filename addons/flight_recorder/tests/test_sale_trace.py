import json

from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user

from ..models.recorder import TRACE_CONTEXT_KEY


@tagged("post_install", "-at_install")
class TestSaleConfirmationTrace(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Flight Recorder Customer"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Recorded Product",
                "list_price": 25.0,
            }
        )

    def _new_order(self):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": 25.0,
                        },
                    )
                ],
            }
        )

    def test_confirmation_creates_one_ordered_metadata_only_trace(self):
        order = self._new_order()

        order.action_confirm()

        trace = self.env["flight.recorder.trace"].sudo().search(
            [
                ("root_model", "=", "sale.order"),
                ("root_record_id", "=", order.id),
                ("root_operation", "=", "action_confirm"),
            ],
            limit=1,
        )
        self.assertTrue(trace)
        self.assertEqual(trace.status, "completed")
        self.assertEqual(trace.actor_id, self.env.user)
        self.assertEqual(trace.source_module, "sale")

        events = trace.event_ids.sorted("sequence")
        self.assertEqual(events.mapped("sequence"), list(range(1, len(events) + 1)))
        self.assertEqual(events[:2].mapped("kind"), ["request", "method"])
        self.assertTrue(events[1].parent_event_id == events[0])

        state_event = events.filtered(
            lambda event: event.kind == "orm"
            and event.model_name == "sale.order"
            and event.record_id == order.id
        )
        self.assertEqual(len(state_event), 1)
        self.assertEqual(state_event.field_names, ["state"])
        self.assertEqual(state_event.parent_event_id, events[1])
        self.assertEqual(state_event.payload["capture_mode"], "metadata")
        self.assertNotIn("draft", json.dumps(events.mapped("payload")))
        self.assertNotIn("sale", json.dumps(events.mapped("payload")))

    def test_existing_trace_context_prevents_nested_duplicate_trace(self):
        order = self._new_order()

        order.with_context(**{TRACE_CONTEXT_KEY: 123}).action_confirm()

        trace = self.env["flight.recorder.trace"].sudo().search(
            [("root_record_id", "=", order.id)]
        )
        self.assertFalse(trace)

    def test_non_admin_cannot_read_recorded_evidence(self):
        order = self._new_order()
        order.action_confirm()
        salesperson = new_test_user(
            self.env,
            login="flight-recorder-salesperson",
            groups="sales_team.group_sale_salesman",
        )

        with self.assertRaises(AccessError):
            self.env["flight.recorder.trace"].with_user(salesperson).search([])
