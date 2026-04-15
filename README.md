# Odoo 19 Self-Hosted Platform

Professional self-hosted Odoo 19 platform scaffold inspired by the operational shape of Odoo.sh.

## Current platform slices

- Git-safe repository with sanitized examples
- Base compose stack for Odoo, PostgreSQL, Nginx, Redis, and pgBackRest
- Dev, admin, staging, and production compose overrides
- Optional Obsidian knowledge layer and pgAdmin admin layer
- Bootstrap backup and restore scripts
- GitHub Actions validation workflow scaffold

## Main entrypoints

- Architecture spec: [docs/superpowers/specs/2026-04-15-odoo-self-hosted-platform-design.md](docs/superpowers/specs/2026-04-15-odoo-self-hosted-platform-design.md)
- Bootstrap plan: [docs/superpowers/plans/2026-04-15-odoo-platform-bootstrap-implementation-plan.md](docs/superpowers/plans/2026-04-15-odoo-platform-bootstrap-implementation-plan.md)
- Platform bootstrap doc: [docs/architecture/platform-bootstrap.md](docs/architecture/platform-bootstrap.md)
- Obsidian brain: [docs/00_Odoo_Brain.md](docs/00_Odoo_Brain.md)

## Local commands

Development stack:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml up -d
```

Admin and knowledge stack:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d
```

Local health check:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-local-stack.ps1
```

## Current local endpoints

- Odoo direct: `http://localhost:8069/web/login`
- Odoo through Nginx: `http://localhost:8088/web/login`
- pgAdmin: `http://localhost:8080`
- Obsidian: `http://localhost:3000`

## Notes

- `docker-compose.yml` remains as a legacy compatibility stack for local use.
- The forward-looking platform path is `compose.yaml` plus overrides.
- The `docs/` directory doubles as the Obsidian vault.
