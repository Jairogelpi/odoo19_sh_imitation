import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "replay_incident.py"
SPEC = importlib.util.spec_from_file_location("flight_recorder_replay_runner_test", RUNNER)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def test_compose_override_quotes_the_complete_bind_mount():
    content = runner._override_content(Path("/tmp/replay directory"))

    assert '      - "/tmp/replay directory:/replay:rw"' in content
    assert '"/tmp/replay directory":/replay:rw' not in content
    assert "    internal: true" in content


def test_runner_prepares_a_world_writable_disposable_exchange_directory(tmp_path):
    replay_dir = tmp_path / "exchange"
    replay_dir.mkdir()
    source = tmp_path / "source.odoo-incident"
    source.write_bytes(b"evidence")

    incident = runner._prepare_exchange(replay_dir, source)

    assert replay_dir.stat().st_mode & 0o777 == 0o777
    assert incident.stat().st_mode & 0o777 == 0o644
    assert incident.read_bytes() == b"evidence"
