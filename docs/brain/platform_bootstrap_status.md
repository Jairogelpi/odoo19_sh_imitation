# Platform Bootstrap Status

## Goal
Track the current state of the Odoo self-hosted platform while keeping the technical docs and the Obsidian brain aligned.

## Current architecture snapshot
- Core base compose: `compose.yaml`
- Dev override: `compose.dev.yaml`
- Admin and knowledge override: `compose.admin.yaml`
- Production-like overrides: `compose.staging.yaml`, `compose.prod.yaml`
- Legacy local compatibility stack: `docker-compose.yml`

## Implemented so far
- Repository sanitized for GitHub push.
- Secrets replaced with safe examples in tracked files.
- Runtime data ignored through `.gitignore` and `.dockerignore`.
- Custom Odoo image scaffold added.
- Nginx reverse proxy scaffold added.
- Staging and production Odoo config files added.
- Bootstrap backup and restore scripts added.
- GitHub Actions workflow skeleton added.
- Obsidian integrated as an optional admin/knowledge service instead of part of the production-safe base compose.

## Verification evidence already run
- `docker compose -f compose.yaml -f compose.dev.yaml config`
- `docker build -f odoo/Dockerfile .`
- `docker compose -f compose.yaml -f compose.dev.yaml up -d`
- `Invoke-WebRequest http://localhost:8088/web/login`
- `Invoke-WebRequest http://localhost:8069/web/login`
- `docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d obsidian pgadmin`
- `Invoke-WebRequest http://localhost:3000` -> `401` expected because Obsidian is access-controlled
- `docker compose -f compose.yaml -f compose.staging.yaml config`
- `docker compose -f compose.yaml -f compose.prod.yaml config`

## Why Obsidian is in the admin layer
- It is useful for local documentation and knowledge capture.
- It should not be required in staging or production runtime.
- Keeping it in `compose.admin.yaml` preserves a cleaner platform base.

## Next recommended implementation slice
- Add Redis to the platform.
- Add `pgBackRest` service and config.
- Add restore and neutralization automation for staging.
- Upgrade the CI workflow from validation-only to GHCR plus SSH deployment.

## Links
- [Platform](platform.md)
- [Operations](operations.md)
- [Platform bootstrap doc](../architecture/platform-bootstrap.md)
- [Backup and restore runbook](../runbooks/backup-and-restore.md)
