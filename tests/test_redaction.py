from odoo_flight_recorder import REDACTED, redact


def test_metadata_mode_preserves_shape_but_not_scalar_values():
    payload = {
        "model": "res.partner",
        "values": {"email": "person@example.com", "active": True},
        "ids": [1, 2],
    }

    assert redact(payload) == {
        "model": REDACTED,
        "values": {"email": REDACTED, "active": REDACTED},
        "ids": [REDACTED, REDACTED],
    }


def test_secret_keys_are_denied_even_when_value_capture_is_enabled():
    payload = {
        "api-key": "secret",
        "nested": {"password": "secret", "name": "Allowed"},
    }

    assert redact(payload, allow_value_capture=True) == {
        "api-key": REDACTED,
        "nested": {"password": REDACTED, "name": "Allowed"},
    }
