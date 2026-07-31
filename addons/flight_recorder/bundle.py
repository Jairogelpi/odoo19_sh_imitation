"""Deterministic, framework-independent `.odoo-incident` bundles."""

from __future__ import annotations

import io
import itertools
import json
import zipfile
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

SCHEMA = "odoo-flight-recorder.incident"
SCHEMA_VERSION = 1
EXPECTED_FILES = frozenset({"manifest.json", "events.json", "fixtures.json"})
MAX_MEMBER_BYTES = 10_000_000
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_SECRET_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "cookie",
        "credit_card",
        "cvv",
        "password",
        "refresh_token",
        "secret",
        "session_id",
        "token",
    }
)


class BundleVerificationError(ValueError):
    """Raised when an incident bundle cannot be trusted."""


@dataclass(frozen=True, slots=True)
class VerificationResult:
    incident_id: str
    event_count: int
    fixture_count: int
    schema_version: int


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _normalized_key(value: object) -> str:
    return str(value).strip().lower().replace("-", "_")


def _assert_safe_structure(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = _normalized_key(key)
            if normalized in _SECRET_KEYS:
                raise BundleVerificationError(f"Forbidden secret key: {key}")
            if normalized in {"record_id", "root_record_id", "user_id", "actor_id"}:
                raise BundleVerificationError(f"Forbidden identity key: {key}")
            _assert_safe_structure(item)
    elif isinstance(value, list):
        for item in value:
            _assert_safe_structure(item)


def _record_keys(trace: dict[str, Any], events: list[dict[str, Any]]) -> list[tuple[str, int]]:
    keys = {
        (event["model_name"], int(event["record_id"]))
        for event in events
        if event.get("model_name") and event.get("record_id")
    }
    if trace.get("root_model") and trace.get("root_record_id"):
        keys.add((trace["root_model"], int(trace["root_record_id"])))
    return sorted(keys)


def _anonymized_documents(
    trace: dict[str, Any],
    events: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    references = {
        key: f"record-{index:04d}"
        for index, key in enumerate(_record_keys(trace, events), start=1)
    }
    fixture_records = [
        {
            "ref": reference,
            "model": model_name,
            "fields": {},
        }
        for (model_name, _record_id), reference in references.items()
    ]

    exported_events = []
    for event in sorted(events, key=lambda item: item["sequence"]):
        record_key = (event.get("model_name"), int(event.get("record_id") or 0))
        exported = {
            "sequence": int(event["sequence"]),
            "parent_sequence": event.get("parent_sequence"),
            "kind": event["kind"],
            "model": event.get("model_name"),
            "record_ref": references.get(record_key),
            "operation": event.get("operation"),
            "field_names": sorted(event.get("field_names") or []),
            "source": {
                "module": event.get("source_module"),
                "path": event.get("source_path"),
            },
            "occurred_at": event.get("occurred_at"),
            "payload": event.get("payload") or {},
            "source_payload_hash": event["payload_hash"],
        }
        exported["evidence_hash"] = _digest(_canonical_bytes(exported))
        exported_events.append(exported)

    root_key = (trace.get("root_model"), int(trace.get("root_record_id") or 0))
    events_document = {
        "schema": f"{SCHEMA}.events",
        "schema_version": SCHEMA_VERSION,
        "trace": {
            "correlation_id": trace["correlation_id"],
            "status": trace["status"],
            "started_at": trace.get("started_at"),
            "ended_at": trace.get("ended_at"),
            "actor_type": "odoo_user",
            "root_model": trace.get("root_model"),
            "root_record_ref": references.get(root_key),
            "root_operation": trace.get("root_operation"),
            "source_module": trace.get("source_module"),
            "source_path": trace.get("source_path"),
            "git_revision": trace.get("git_revision"),
        },
        "events": exported_events,
    }
    fixtures_document = {
        "schema": f"{SCHEMA}.fixtures",
        "schema_version": SCHEMA_VERSION,
        "records": fixture_records,
    }
    return events_document, fixtures_document


def build_bundle(trace: dict[str, Any], events: list[dict[str, Any]]) -> bytes:
    """Build a byte-for-byte deterministic, anonymized incident archive."""
    events_document, fixtures_document = _anonymized_documents(trace, events)
    _assert_safe_structure(events_document)
    _assert_safe_structure(fixtures_document)
    files = {
        "events.json": _canonical_bytes(events_document),
        "fixtures.json": _canonical_bytes(fixtures_document),
    }
    manifest = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "incident_id": trace["correlation_id"],
        "created_at": trace.get("ended_at") or trace.get("started_at"),
        "generator": {
            "name": "Flight Recorder for Odoo",
            "format_version": SCHEMA_VERSION,
        },
        "event_count": len(events_document["events"]),
        "fixture_count": len(fixtures_document["records"]),
        "files": {
            name: {
                "sha256": _digest(content),
                "bytes": len(content),
            }
            for name, content in sorted(files.items())
        },
    }
    files["manifest.json"] = _canonical_bytes(manifest)

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)
    return output.getvalue()


def _load_json(raw: bytes, name: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BundleVerificationError(f"{name} is not canonical UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise BundleVerificationError(f"{name} must contain a JSON object")
    if _canonical_bytes(value) != raw:
        raise BundleVerificationError(f"{name} is not canonically serialized")
    return value


def verify_bundle(data: bytes) -> VerificationResult:
    """Verify archive structure, file seals, event seals, and causal ordering."""
    try:
        archive = zipfile.ZipFile(io.BytesIO(data), "r")
    except (zipfile.BadZipFile, OSError) as exc:
        raise BundleVerificationError("Not a valid .odoo-incident archive") from exc

    with archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            raise BundleVerificationError("Duplicate archive member")
        if set(names) != EXPECTED_FILES:
            raise BundleVerificationError("Unexpected or missing archive member")
        if any(
            info.file_size > MAX_MEMBER_BYTES or info.compress_type != zipfile.ZIP_STORED
            for info in infos
        ):
            raise BundleVerificationError("Unsafe archive member")
        raw_files = {name: archive.read(name) for name in names}

    manifest = _load_json(raw_files["manifest.json"], "manifest.json")
    if manifest.get("schema") != SCHEMA or manifest.get("schema_version") != SCHEMA_VERSION:
        raise BundleVerificationError("Unsupported incident schema")
    sealed_files = manifest.get("files")
    if not isinstance(sealed_files, dict) or set(sealed_files) != {
        "events.json",
        "fixtures.json",
    }:
        raise BundleVerificationError("Invalid manifest file inventory")
    for name, seal in sealed_files.items():
        if seal != {"sha256": _digest(raw_files[name]), "bytes": len(raw_files[name])}:
            raise BundleVerificationError(f"Hash or size mismatch for {name}")

    events_document = _load_json(raw_files["events.json"], "events.json")
    fixtures_document = _load_json(raw_files["fixtures.json"], "fixtures.json")
    _assert_safe_structure(events_document)
    _assert_safe_structure(fixtures_document)
    if (
        events_document.get("schema") != f"{SCHEMA}.events"
        or events_document.get("schema_version") != SCHEMA_VERSION
        or fixtures_document.get("schema") != f"{SCHEMA}.fixtures"
        or fixtures_document.get("schema_version") != SCHEMA_VERSION
    ):
        raise BundleVerificationError("Unsupported incident subdocument schema")
    if (
        events_document.get("trace", {}).get("correlation_id")
        != manifest.get("incident_id")
    ):
        raise BundleVerificationError("Incident identifier mismatch")
    events = events_document.get("events")
    fixtures = fixtures_document.get("records")
    if not isinstance(events, list) or not isinstance(fixtures, list):
        raise BundleVerificationError("Invalid events or fixtures document")
    if manifest.get("event_count") != len(events) or manifest.get("fixture_count") != len(fixtures):
        raise BundleVerificationError("Manifest counts do not match contents")

    fixture_refs = [
        fixture.get("ref")
        for fixture in fixtures
        if isinstance(fixture, dict) and fixture.get("ref")
    ]
    if len(fixture_refs) != len(fixtures) or len(fixture_refs) != len(set(fixture_refs)):
        raise BundleVerificationError("Invalid or duplicate fixture reference")
    fixture_ref_set = set(fixture_refs)
    root_record_ref = events_document.get("trace", {}).get("root_record_ref")
    if root_record_ref and root_record_ref not in fixture_ref_set:
        raise BundleVerificationError("Trace references an unknown root fixture")
    expected_sequence = 1
    seen_sequences: set[int] = set()
    for event in events:
        if not isinstance(event, dict) or event.get("sequence") != expected_sequence:
            raise BundleVerificationError("Event sequence is not contiguous")
        evidence_hash = event.get("evidence_hash")
        evidence = {key: value for key, value in event.items() if key != "evidence_hash"}
        if evidence_hash != _digest(_canonical_bytes(evidence)):
            raise BundleVerificationError("Event evidence hash mismatch")
        parent_sequence = event.get("parent_sequence")
        if parent_sequence is not None and parent_sequence not in seen_sequences:
            raise BundleVerificationError("Event parent must precede its child")
        source_payload_hash = event.get("source_payload_hash")
        if not isinstance(source_payload_hash, str) or len(source_payload_hash) != 64:
            raise BundleVerificationError("Invalid source payload hash")
        if event.get("record_ref") and event["record_ref"] not in fixture_ref_set:
            raise BundleVerificationError("Event references an unknown fixture")
        seen_sequences.add(expected_sequence)
        expected_sequence += 1

    return VerificationResult(
        incident_id=manifest["incident_id"],
        event_count=len(events),
        fixture_count=len(fixtures),
        schema_version=manifest["schema_version"],
    )


def read_bundle(data: bytes) -> dict[str, Any]:
    """Return verified incident documents; never expose unverified JSON."""
    verify_bundle(data)
    with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
        return {
            "manifest": json.loads(archive.read("manifest.json")),
            "events": json.loads(archive.read("events.json")),
            "fixtures": json.loads(archive.read("fixtures.json")),
        }


def event_signature(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize original or observed evidence for behavior comparison."""
    return {
        "sequence": int(event["sequence"]),
        "parent_sequence": event.get("parent_sequence"),
        "kind": event["kind"],
        "model": event.get("model") or event.get("model_name"),
        "operation": event.get("operation"),
        "field_names": sorted(event.get("field_names") or []),
    }


def compare_event_streams(
    original: list[dict[str, Any]],
    observed: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compare causal behavior while ignoring IDs, timestamps, and hashes."""
    expected = [event_signature(event) for event in original]
    actual = [event_signature(event) for event in observed]
    differences = []
    for index, (left, right) in enumerate(
        itertools.zip_longest(expected, actual),
        start=1,
    ):
        if left != right:
            differences.append(
                {
                    "position": index,
                    "expected": left,
                    "observed": right,
                }
            )
    return {
        "matched": not differences,
        "expected_event_count": len(expected),
        "observed_event_count": len(actual),
        "differences": differences,
    }
