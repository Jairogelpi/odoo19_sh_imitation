import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .config import settings


@dataclass
class BackupEntry:
    label: str
    type: str
    started: datetime
    stopped: datetime
    size_bytes: int
    db_size_bytes: int
    wal_start: str
    wal_stop: str

    @property
    def size_human(self) -> str:
        return _humanize_bytes(self.size_bytes)

    @property
    def db_size_human(self) -> str:
        return _humanize_bytes(self.db_size_bytes)

    @property
    def duration_seconds(self) -> int:
        return int((self.stopped - self.started).total_seconds())

    @property
    def age_human(self) -> str:
        now = datetime.now(timezone.utc)
        delta = now - self.stopped
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds}s"
        if seconds < 3600:
            return f"{seconds // 60} min"
        if seconds < 86400:
            return f"{seconds // 3600} h"
        return f"{seconds // 86400} d"


def _humanize_bytes(size: int) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PiB"


async def _run(*args: str, timeout: int = 30) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise
    return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")


async def list_backups() -> tuple[list[BackupEntry], dict[str, Any]]:
    code, out, err = await _run(
        "docker",
        "exec",
        settings.pgbackrest_container,
        "pgbackrest",
        f"--stanza={settings.stanza}",
        "info",
        "--output=json",
    )
    if code != 0:
        raise RuntimeError(f"pgbackrest info failed ({code}): {err}")

    data = json.loads(out)
    if not data:
        return [], {}

    stanza = data[0]
    entries: list[BackupEntry] = []
    for backup in stanza.get("backup", []):
        entries.append(
            BackupEntry(
                label=backup["label"],
                type=backup["type"],
                started=datetime.fromtimestamp(backup["timestamp"]["start"], tz=timezone.utc),
                stopped=datetime.fromtimestamp(backup["timestamp"]["stop"], tz=timezone.utc),
                size_bytes=backup["info"]["repository"]["size"],
                db_size_bytes=backup["info"]["size"],
                wal_start=backup["archive"]["start"],
                wal_stop=backup["archive"]["stop"],
            )
        )
    entries.sort(key=lambda e: e.started, reverse=True)

    stanza_meta = {
        "name": stanza["name"],
        "status": stanza.get("status", {}).get("message", "unknown"),
        "db_count": len(stanza.get("db", [])),
        "total_backups": len(entries),
        "repo_size_human": _humanize_bytes(
            sum(e.size_bytes for e in entries)
        ),
    }
    return entries, stanza_meta


async def restore_local(label: str) -> tuple[bool, str]:
    """Restore the local dev stack's db to the given backup label.

    Steps:
    1. stop odoo (so it releases connections)
    2. stop postgres cleanly
    3. invoke pgbackrest restore via the pgbackrest container (which shares postgres volumes)
    4. start postgres and odoo again
    """
    log: list[str] = []

    async def step(title: str, *cmd: str, timeout: int = 120) -> bool:
        log.append(f"$ {' '.join(cmd)}")
        code, out, err = await _run(*cmd, timeout=timeout)
        log.append(out.strip())
        if err:
            log.append(err.strip())
        log.append(f"(exit {code})")
        return code == 0

    if not await step("stop-odoo", "docker", "stop", settings.odoo_container):
        return False, "\n".join(log)

    if not await step("stop-db", "docker", "stop", settings.db_container):
        return False, "\n".join(log)

    restore_ok = await step(
        "restore",
        "docker",
        "exec",
        settings.pgbackrest_container,
        "pgbackrest",
        f"--stanza={settings.stanza}",
        "--delta",
        "--set",
        label,
        "--type=immediate",
        "--target-action=promote",
        "restore",
        timeout=600,
    )

    await step("start-db", "docker", "start", settings.db_container)
    await step("start-odoo", "docker", "start", settings.odoo_container)

    return restore_ok, "\n".join(log)


def remote_restore_recipe(env: str, label: str) -> str:
    """Return a copy-pasteable SSH recipe for restoring a remote env."""
    return (
        f"# Restore backup {label} on {env} (run from your workstation)\n"
        f"ssh deploy@{env}.your-host.example \\\n"
        f"  'cd /srv/odoo && \\\n"
        f"   docker compose -f compose.yaml -f compose.{env}.yaml stop odoo db && \\\n"
        f"   docker compose -f compose.yaml -f compose.{env}.yaml exec -T pgbackrest \\\n"
        f"     pgbackrest --stanza={settings.stanza} --delta --set {label} \\\n"
        f"     --type=immediate --target-action=promote restore && \\\n"
        f"   docker compose -f compose.yaml -f compose.{env}.yaml start db odoo'\n"
    )
