#!/usr/bin/env python3
"""Verify a `.odoo-incident` file without importing Odoo."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_MODULE = ROOT / "addons" / "flight_recorder" / "bundle.py"


def _load_verifier():
    spec = importlib.util.spec_from_file_location("flight_recorder_bundle", BUNDLE_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the Flight Recorder bundle verifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify structure, hashes, and causal ordering in an Odoo incident bundle."
    )
    parser.add_argument("incident", type=Path)
    args = parser.parse_args()
    module = _load_verifier()
    try:
        result = module.verify_bundle(args.incident.read_bytes())
    except (OSError, module.BundleVerificationError) as exc:
        parser.exit(1, f"INVALID: {exc}\n")
    print(
        f"VERIFIED incident={result.incident_id} "
        f"events={result.event_count} fixtures={result.fixture_count} "
        f"schema={result.schema_version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
