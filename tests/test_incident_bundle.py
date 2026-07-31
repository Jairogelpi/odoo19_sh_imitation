import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_MODULE = ROOT / "addons" / "flight_recorder" / "bundle.py"
SPEC = importlib.util.spec_from_file_location("flight_recorder_bundle_test", BUNDLE_MODULE)
assert SPEC and SPEC.loader
bundle = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = bundle
SPEC.loader.exec_module(bundle)


def _trace():
    return {
        "correlation_id": "incident-001",
        "status": "completed",
        "started_at": "2026-07-31 10:00:00",
        "ended_at": "2026-07-31 10:00:01",
        "root_model": "sale.order",
        "root_record_id": 42,
        "root_operation": "action_confirm",
        "source_module": "sale",
        "source_path": "sale/models/sale_order.py",
        "git_revision": "abc123",
    }


def _events():
    return [
        {
            "sequence": 1,
            "parent_sequence": None,
            "kind": "request",
            "model_name": "sale.order",
            "record_id": 42,
            "operation": "sale_order_confirm",
            "field_names": [],
            "source_module": "sale",
            "source_path": "sale/models/sale_order.py",
            "occurred_at": "2026-07-31 10:00:00",
            "payload": {"capture_mode": "metadata"},
            "payload_hash": "a" * 64,
        },
        {
            "sequence": 2,
            "parent_sequence": 1,
            "kind": "orm",
            "model_name": "sale.order",
            "record_id": 42,
            "operation": "write",
            "field_names": ["state"],
            "source_module": "sale",
            "source_path": "sale/models/sale_order.py",
            "occurred_at": "2026-07-31 10:00:01",
            "payload": {"capture_mode": "metadata"},
            "payload_hash": "b" * 64,
        },
    ]


def test_bundle_is_deterministic_anonymized_and_offline_verifiable():
    first = bundle.build_bundle(_trace(), _events())
    second = bundle.build_bundle(_trace(), _events())

    assert first == second
    assert b'"record_id"' not in first
    result = bundle.verify_bundle(first)
    assert result.incident_id == "incident-001"
    assert result.event_count == 2
    assert result.fixture_count == 1

    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        events = json.loads(archive.read("events.json"))
        fixtures = json.loads(archive.read("fixtures.json"))
    assert events["events"][0]["record_ref"] == "record-0001"
    assert fixtures["records"] == [
        {"fields": {}, "model": "sale.order", "ref": "record-0001"}
    ]


def test_verifier_rejects_tampered_evidence():
    original = bundle.build_bundle(_trace(), _events())
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as source:
        files = {name: source.read(name) for name in source.namelist()}
    events = json.loads(files["events.json"])
    events["events"][1]["field_names"] = ["state", "amount_total"]
    files["events.json"] = bundle._canonical_bytes(events)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as target:
        for name, content in files.items():
            target.writestr(name, content)

    with pytest.raises(bundle.BundleVerificationError, match="Hash or size mismatch"):
        bundle.verify_bundle(output.getvalue())


def test_verifier_rejects_extra_archive_members():
    original = bundle.build_bundle(_trace(), _events())
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as source, zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_STORED
    ) as target:
        for name in source.namelist():
            target.writestr(name, source.read(name))
        target.writestr("../unexpected.txt", b"unsafe")

    with pytest.raises(bundle.BundleVerificationError, match="Unexpected or missing"):
        bundle.verify_bundle(output.getvalue())


def test_builder_rejects_secret_keys_even_when_source_evidence_is_forged():
    events = _events()
    events[0]["payload"]["access_token"] = "must-never-leave-odoo"

    with pytest.raises(bundle.BundleVerificationError, match="Forbidden secret key"):
        bundle.build_bundle(_trace(), events)
