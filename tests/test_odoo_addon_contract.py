from ast import literal_eval
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addons" / "flight_recorder"


def test_manifest_targets_odoo_19_and_loads_admin_access_rules():
    manifest = literal_eval((ADDON / "__manifest__.py").read_text(encoding="utf-8"))

    assert manifest["version"].startswith("19.0.")
    assert manifest["license"] == "AGPL-3"
    assert manifest["depends"] == ["base"]
    assert "security/ir.model.access.csv" in manifest["data"]
    assert manifest["installable"] is True


def test_trace_models_are_not_writable_or_deletable_through_access_rules():
    access = (ADDON / "security" / "ir.model.access.csv").read_text(encoding="utf-8")

    assert "base.group_system,1,0,1,0" in access
    assert access.count("base.group_system,1,0,1,0") == 2
