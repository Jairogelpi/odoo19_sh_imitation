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
