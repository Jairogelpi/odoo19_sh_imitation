from datetime import datetime, timezone

from odoo_flight_recorder import EventEnvelope


def test_digest_is_deterministic_for_the_same_event():
    occurred_at = datetime(2026, 7, 31, 7, 30, tzinfo=timezone.utc)
    event = EventEnvelope(
        event_id="event-1",
        trace_id="trace-1",
        sequence=1,
        kind="orm",
        occurred_at=occurred_at,
        payload={"model": "sale.order", "fields": ["state"]},
    )

    equivalent = EventEnvelope(
        payload={"fields": ["state"], "model": "sale.order"},
        occurred_at=occurred_at,
        kind="orm",
        sequence=1,
        trace_id="trace-1",
        event_id="event-1",
    )

    assert event.digest() == equivalent.digest()
    assert event.canonical_json() == equivalent.canonical_json()


def test_digest_changes_when_evidence_changes():
    base = EventEnvelope(
        event_id="event-1",
        trace_id="trace-1",
        sequence=1,
        kind="orm",
        occurred_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
        payload={"model": "sale.order"},
    )
    changed = EventEnvelope(
        event_id="event-1",
        trace_id="trace-1",
        sequence=2,
        kind="orm",
        occurred_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
        payload={"model": "sale.order"},
    )

    assert base.digest() != changed.digest()

