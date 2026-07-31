#!/usr/bin/env python3
"""Replay one verified incident in a disposable, network-isolated Odoo stack."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_MODULE = ROOT / "addons" / "flight_recorder" / "bundle.py"


def _load_bundle_module():
    spec = importlib.util.spec_from_file_location("flight_recorder_replay_bundle", BUNDLE_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the incident verifier")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _run(
    command: list[str],
    *,
    stdin: str | None = None,
    ignore_failure: bool = False,
) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode and not ignore_failure:
        details = "\n".join(part for part in (result.stdout, result.stderr) if part)
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}\n{details}")


def _compose(project: str, override: Path, *arguments: str) -> list[str]:
    return [
        "docker",
        "compose",
        "-p",
        project,
        "-f",
        str(ROOT / "compose.yaml"),
        "-f",
        str(override),
        *arguments,
    ]


def _override_content(replay_dir: Path) -> str:
    volume = json.dumps(f"{replay_dir}:/replay:rw")
    return "\n".join(
        [
            "services:",
            "  odoo:",
            "    environment:",
            "      FLIGHT_RECORDER_REPLAY_ISOLATED: \"1\"",
            "    volumes:",
            f"      - {volume}",
            "networks:",
            "  default:",
            "    internal: true",
            "",
        ]
    )


def _prepare_exchange(replay_dir: Path, incident: Path) -> Path:
    """Make only the disposable exchange readable/writable by the container UID."""
    replay_dir.chmod(0o777)
    incident_copy = replay_dir / "incident.odoo-incident"
    shutil.copyfile(incident, incident_copy)
    incident_copy.chmod(0o644)
    return incident_copy


def replay(incident: Path, output: Path) -> dict:
    bundle = _load_bundle_module()
    incident_data = incident.read_bytes()
    verification = bundle.verify_bundle(incident_data)
    digest = sha256(incident_data).hexdigest()[:10]
    project = f"flight-recorder-replay-{digest}-{os.getpid()}".lower()
    database = f"flight_recorder_replay_{digest}"

    with tempfile.TemporaryDirectory(prefix="flight-recorder-replay-") as directory:
        replay_dir = Path(directory)
        _prepare_exchange(replay_dir, incident)
        override = replay_dir / "compose.replay.yaml"
        override.write_text(_override_content(replay_dir), encoding="utf-8")
        shell_script = """
import json
from pathlib import Path

data = Path('/replay/incident.odoo-incident').read_bytes()
report = env['flight.recorder.replay.service'].replay_bundle(data)
Path('/replay/report.json').write_text(
    json.dumps(report, ensure_ascii=False, separators=(',', ':'), sort_keys=True),
    encoding='utf-8',
)
env.cr.commit()
"""
        try:
            _run(_compose(project, override, "up", "-d", "--wait", "db"))
            _run(
                _compose(
                    project,
                    override,
                    "run",
                    "--rm",
                    "odoo",
                    "odoo",
                    "--database",
                    database,
                    "--init",
                    "flight_recorder",
                    "--stop-after-init",
                    "--no-http",
                    "--without-demo",
                    "all",
                    "--max-cron-threads",
                    "0",
                )
            )
            _run(
                _compose(
                    project,
                    override,
                    "run",
                    "--rm",
                    "-T",
                    "odoo",
                    "odoo",
                    "shell",
                    "--database",
                    database,
                    "--no-http",
                    "--max-cron-threads",
                    "0",
                ),
                stdin=shell_script,
            )
            report = json.loads((replay_dir / "report.json").read_text(encoding="utf-8"))
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        finally:
            _run(
                _compose(project, override, "down", "--volumes", "--remove-orphans"),
                ignore_failure=True,
            )

    if report["incident_id"] != verification.incident_id:
        raise RuntimeError("Replay report incident ID mismatch")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("incident", type=Path)
    parser.add_argument("--output", type=Path, default=Path("replay-report.json"))
    args = parser.parse_args()
    try:
        report = replay(args.incident.resolve(), args.output.resolve())
    except Exception as exc:
        parser.exit(1, f"REPLAY FAILED: {exc}\n")
    status = "MATCH" if report["matched"] else "MISMATCH"
    print(
        f"REPLAY {status} incident={report['incident_id']} "
        f"expected={report['expected_event_count']} "
        f"observed={report['observed_event_count']} report={args.output}"
    )
    return 0 if report["matched"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
