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
- Homepage admin lobby
- bootstrap backup/restore scripts
- working local `pgBackRest` flow
- GHCR publish, SSH deploy, and scaffold contract workflow
- automated staging restore neutralization with `Mailpit`
- offsite backup replication scripts using ephemeral `rclone`

## Current service inventory

Core base stack:

- `db`: PostgreSQL 16 with `archive_mode` enabled for `pgBackRest`
- `redis`: local platform cache/queue primitive
- `pgbackrest`: backup/check utility container
- `odoo`: custom image scaffold based on `odoo:19.0`
- `nginx`: reverse proxy entrypoint for the app

Optional admin and knowledge stack:

- `homepage`: optional admin landing page and status lobby
- `pgadmin`: browser admin UI for PostgreSQL
- `portainer`: browser container-management UI
- `obsidian`: browser-accessible knowledge workspace over the `docs/` vault

Staging support stack:

- `mailpit`: local-only SMTP sink for neutralized staging restores

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

Admin layer verification:

```bash
powershell -ExecutionPolicy Bypass -File .\ops\health\check-admin-stack.ps1
```

Latest validated state:

- [Runtime validation](../runbooks/runtime-validation.md)

## Not implemented yet

- first-time server bootstrap automation
- live deploy validation against a real remote target
- deeper data anonymization for restored staging copies
- scheduled restore drills from offsite backup sets
- automatic Odoo master-password injection from `ODOO_ADMIN_PASSWORD`
