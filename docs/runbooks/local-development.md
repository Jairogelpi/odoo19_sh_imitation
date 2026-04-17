# Local Development Runbook

## Goal

Run and verify the platform locally with the smallest reliable workflow.

On Windows, the recommended runtime is Docker Desktop with the WSL 2 backend.

## Recommended startup paths

Before first start:

- Make sure Docker Desktop is running.
- Confirm file sharing is enabled for the repository location.
- Keep the repository on the local disk rather than a removable or network drive.

Development base stack:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml up -d
```

Development plus admin and knowledge layer:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d
```

Legacy compatibility path:

```powershell
docker compose up -d
```

## Useful local endpoints

- Lobby (start here): `http://localhost:8081`
- Odoo direct: `http://localhost:8069/web/login`
- Odoo via Nginx: `http://localhost:8088/web/login`
- pgAdmin: `http://localhost:8080`
- Portainer: `https://localhost:9443`
- Obsidian: `http://localhost:3000`

## Verification

Primary local verification:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-local-stack.ps1
```

Admin and knowledge layer verification:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-admin-stack.ps1
```

Reference state and exact evidence:

- [Runtime validation](runtime-validation.md)
- [Lobby (Homepage) runbook](lobby-homepage.md)

Manual spot checks:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml exec -T redis redis-cli ping
docker compose -f compose.yaml -f compose.dev.yaml exec -T pgbackrest /scripts/check-db.sh
docker compose -f compose.yaml -f compose.dev.yaml exec -T pgbackrest /scripts/backup-db.sh
```

## Addon layout

Use this repository structure for modules that must travel through Git between environments:

```text
addons/
addons_custom/
```

Rules:

- third-party or OCA modules go in `addons/`
- in-house development goes in `addons_custom/<module_name>/`
- both trees are mounted inside Docker and read automatically by Odoo

## Logs

Base stack:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml logs -f
```

Focused logs:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml logs -f odoo nginx db redis pgbackrest
```

Admin and knowledge layer:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml logs -f pgadmin obsidian
```

## Stop commands

Base stack:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml down
```

Base plus admin:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml down
```

## Notes

- `compose.yaml` is the canonical base. Prefer it over `docker-compose.yml`.
- `compose.admin.yaml` is intentionally optional.
- `check-local-stack.ps1` verifies only the base dev stack.
- `check-admin-stack.ps1` adds pgAdmin, Obsidian, and Homepage checks for the optional admin layer.
- The `docs/` directory is both repository documentation and the Obsidian vault.
- Extra Odoo addons are split between `./addons` and `./addons_custom`.
