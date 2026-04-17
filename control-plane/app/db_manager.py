from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from .config import settings

log = logging.getLogger("control-plane.db")


@dataclass
class Database:
    name: str
    size_human: str


async def _run(cmd: list[str]) -> tuple[bool, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    return proc.returncode == 0, stdout.decode(errors="replace").strip()


async def list_databases() -> list[Database]:
    ok, output = await _run([
        "docker", "exec", settings.db_container,
        "psql", "-U", "odoo", "-d", "postgres", "-t", "-A", "-c",
        "SELECT datname, pg_size_pretty(pg_database_size(datname)) "
        "FROM pg_database WHERE datistemplate = false ORDER BY datname",
    ])
    if not ok:
        log.error("list_databases failed: %s", output)
        return []
    dbs: list[Database] = []
    for line in output.strip().splitlines():
        parts = line.split("|", 1)
        if len(parts) == 2:
            dbs.append(Database(name=parts[0].strip(), size_human=parts[1].strip()))
    return dbs


async def duplicate_database(source: str, target: str) -> tuple[bool, str]:
    ok, out = await _run([
        "docker", "exec", settings.db_container,
        "psql", "-U", "odoo", "-d", "postgres", "-c",
        f'CREATE DATABASE "{target}" WITH TEMPLATE "{source}" OWNER odoo',
    ])
    return ok, out


async def drop_database(name: str) -> tuple[bool, str]:
    if name in ("postgres", "odoo", "template0", "template1"):
        return False, f"No se permite eliminar la base de datos protegida: {name}"
    terminate = (
        f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        f"WHERE datname = '{name}' AND pid <> pg_backend_pid()"
    )
    await _run([
        "docker", "exec", settings.db_container,
        "psql", "-U", "odoo", "-d", "postgres", "-c", terminate,
    ])
    ok, out = await _run([
        "docker", "exec", settings.db_container,
        "psql", "-U", "odoo", "-d", "postgres", "-c",
        f'DROP DATABASE IF EXISTS "{name}"',
    ])
    return ok, out


async def create_database(name: str) -> tuple[bool, str]:
    ok, out = await _run([
        "docker", "exec", settings.db_container,
        "psql", "-U", "odoo", "-d", "postgres", "-c",
        f'CREATE DATABASE "{name}" OWNER odoo',
    ])
    return ok, out
