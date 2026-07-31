#!/usr/bin/env python3
"""Create the deterministic sale-confirmation incident used by replay CI."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_MODULE = ROOT / "addons" / "flight_recorder" / "bundle.py"


def _bundle_module():
    spec = importlib.util.spec_from_file_location("flight_recorder_demo_bundle", BUNDLE_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load bundle module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    trace = {
        "correlation_id": "demo-sale-confirmation",
        "status": "completed",
        "started_at": "2026-07-31 10:00:00",
        "ended_at": "2026-07-31 10:00:01",
        "root_model": "sale.order",
        "root_record_id": 42,
        "root_operation": "action_confirm",
        "source_module": "sale",
        "source_path": "sale/models/sale_order.py",
        "git_revision": "demo",
    }
    base = {
        "model_name": "sale.order",
        "record_id": 42,
        "source_module": "sale",
        "source_path": "sale/models/sale_order.py",
        "payload": {"capture_mode": "metadata"},
        "payload_hash": "a" * 64,
    }
    events = [
        {
            **base,
            "sequence": 1,
            "parent_sequence": None,
            "kind": "request",
            "operation": "sale_order_confirm",
            "field_names": [],
            "occurred_at": "2026-07-31 10:00:00",
        },
        {
            **base,
            "sequence": 2,
            "parent_sequence": 1,
            "kind": "method",
            "operation": "action_confirm",
            "field_names": [],
            "occurred_at": "2026-07-31 10:00:00",
        },
        {
            **base,
            "sequence": 3,
            "parent_sequence": 2,
            "kind": "orm",
            "operation": "write",
            "field_names": ["state"],
            "occurred_at": "2026-07-31 10:00:01",
        },
    ]
    args.output.write_bytes(_bundle_module().build_bundle(trace, events))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
