# Local Development Runbook

## Goal

Run and verify the platform locally with the smallest reliable workflow.

## Recommended startup paths

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

- Odoo direct: `http://localhost:8069/web/login`
- Odoo via Nginx: `http://localhost:8088/web/login`
- pgAdmin: `http://localhost:8080`
- Obsidian: `http://localhost:3000`

## Verification

Primary local verification:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-local-stack.ps1
```

Manual spot checks:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml exec -T redis redis-cli ping
docker compose -f compose.yaml -f compose.dev.yaml exec -T pgbackrest /scripts/check-db.sh
docker compose -f compose.yaml -f compose.dev.yaml exec -T pgbackrest /scripts/backup-db.sh
```

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
- The `docs/` directory is both repository documentation and the Obsidian vault.
