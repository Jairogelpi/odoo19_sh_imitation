from ast import literal_eval
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addons" / "flight_recorder"


def test_manifest_targets_odoo_19_sale_and_loads_admin_access_rules():
    manifest = literal_eval((ADDON / "__manifest__.py").read_text(encoding="utf-8"))

    assert manifest["version"].startswith("19.0.")
    assert manifest["license"] == "AGPL-3"
    assert manifest["depends"] == ["base", "sale"]
    assert "security/ir.model.access.csv" in manifest["data"]
    assert "views/flight_recorder_views.xml" in manifest["data"]
    assert manifest["installable"] is True


def test_trace_models_are_not_writable_or_deletable_through_access_rules():
    access = (ADDON / "security" / "ir.model.access.csv").read_text(encoding="utf-8")

    assert "base.group_system,1,0,1,0" in access
    assert access.count("base.group_system,1,0,1,0") == 2


def test_r1_instruments_only_the_explicit_sale_confirmation_boundary():
    sale_order = (ADDON / "models" / "sale_order.py").read_text(encoding="utf-8")

    assert '_inherit = "sale.order"' in sale_order
    assert "def action_confirm(self):" in sale_order
    assert "_patch" not in sale_order
    assert 'models.Model, "write"' not in sale_order
