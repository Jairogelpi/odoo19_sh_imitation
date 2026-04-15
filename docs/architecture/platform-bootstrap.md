# Platform Bootstrap

This repository is the versioned starting point for the Odoo 19 self-hosted platform.

## Current bootstrap scope

- safe GitHub-ready repository
- shared `compose.yaml`
- `compose.dev.yaml` for local development
- `compose.admin.yaml` for optional admin and knowledge tooling
- custom Odoo image scaffold
- custom PostgreSQL image scaffold with `pgBackRest` archive support
- Nginx reverse proxy template scaffold
- staging and production compose overrides
- Redis service
- bootstrap backup/restore scripts
- working local `pgBackRest` flow
- GHCR publish and SSH deploy workflow

## Current service inventory

Core base stack:

- `db`: PostgreSQL 16 with `archive_mode` enabled for `pgBackRest`
- `redis`: local platform cache/queue primitive
- `pgbackrest`: backup/check utility container
- `odoo`: custom image scaffold based on `odoo:19.0`
- `nginx`: reverse proxy entrypoint for the app

Optional admin and knowledge stack:

- `pgadmin`: browser admin UI for PostgreSQL
- `obsidian`: browser-accessible knowledge workspace over the `docs/` vault

## Runtime data policy

Do not store live runtime data inside the git checkout.

The legacy local directories `postgres/` and `pgadmin/` are now ignored and should be treated as disposable leftovers from the pre-platform sandbox.

Use named volumes during this bootstrap phase. In later phases, production-like environments should move persistent state to environment-specific external paths such as:

```text
/srv/odoo/<project>/<env>/
```

## Current local commands

Development stack:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d
```

Optional admin and knowledge stack:

```bash
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d
```

Legacy compatibility stack:

```bash
docker compose up -d
```

Health verification:

```bash
powershell -ExecutionPolicy Bypass -File .\ops\health\check-local-stack.ps1
```

## Not implemented yet

- staging neutralization automation
- offsite backups
- first-time server bootstrap automation
- live deploy validation against a real remote target
