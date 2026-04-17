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
- Per-environment `.env` example files added for `dev`, `staging`, and `prod`.
- Runtime data ignored through `.gitignore` and `.dockerignore`.
- Custom Odoo image scaffold added.
- Nginx reverse proxy scaffold added.
- Staging and production Odoo config files added.
- Bootstrap backup and restore scripts added.
- Redis service added to the platform base.
- pgBackRest service, config, and utility scripts added.
- PostgreSQL custom image added so `pgBackRest` can run archive commands from the database container.
- GitHub Actions workflow upgraded to validate compose, publish custom images to GHCR, and deploy over SSH.
- Staging restore wrapper upgraded to automate database restore, filestore restore, and post-restore neutralization.
- Staging now includes `Mailpit` as a safe SMTP sink during neutralized operation.
- Offsite backup scripts added to export production backup artifacts and replicate them to S3-compatible storage.
- Obsidian integrated as an optional admin/knowledge service instead of part of the production-safe base compose.
- Portainer integrated as an optional admin/container-management service alongside Obsidian and pgAdmin.
- Homepage integrated as an optional admin landing page with Docker-backed status visibility.
- Staging and production Nginx now require mounted origin certificates and render HTTP or HTTPS templates at startup.
- Dual addon layout added: `addons/` remains the repository lane for third-party/shared modules, and `addons_custom/` now exists for in-house modules.

## Verification evidence already run
- `docker compose -f compose.yaml -f compose.dev.yaml config`
- `docker build -f odoo/Dockerfile .`
- `docker compose -f compose.yaml -f compose.dev.yaml up -d`
- `Invoke-WebRequest http://localhost:8088/web/login`
- `Invoke-WebRequest http://localhost:8069/web/login`
- `docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d homepage obsidian pgadmin portainer`
- `Invoke-WebRequest http://localhost:3000` -> `401` expected because Obsidian is access-controlled
- `docker compose -f compose.yaml -f compose.staging.yaml config`
- `docker compose -f compose.yaml -f compose.prod.yaml config`
- `docker compose -f compose.yaml -f compose.dev.yaml exec redis redis-cli ping` -> `PONG`
- `docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/check-db.sh` -> success
- `docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/backup-db.sh` -> full backup completed
- `powershell -ExecutionPolicy Bypass -File .\ops\health\check-local-stack.ps1` -> local stack verification script added
- `powershell -ExecutionPolicy Bypass -File .\ops\health\check-admin-stack.ps1` -> admin stack verification passes for pgAdmin, Obsidian auth gate, and Homepage
- remote deploy workflow and script implemented, pending validation against a real host with GitHub Environment secrets
- `docker compose -f compose.yaml -f compose.staging.yaml config` -> staging compose including `mailpit` is valid
- `docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/ops/restore/restore-to-staging.sh` -> restore wrapper syntax passes
- `docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/backup-filestore.sh` -> filestore backup script syntax passes
- staging compose now includes `mailpit` and restore/neutralization scripts are present, pending validation with a real backup set
- `docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/export-pgbackrest-repo.sh` -> pgBackRest export script syntax passes
- `docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/export-odoo-filestore.sh` -> filestore export script syntax passes
- `docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/offsite-sync-rclone.sh` -> offsite sync script syntax passes
- `docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/run-offsite-backup.sh` -> offsite wrapper syntax passes
- `docker run --rm rclone/rclone:latest version` -> rclone container is available
- offsite backup flow validated locally against a temporary MinIO target; real offsite credentials are still pending
- the filestore export helper now tolerates a missing filestore directory by writing an empty archive instead of failing
- local restore drill from the offsite artifacts completed successfully against isolated temporary volumes and a temporary PostgreSQL container
- `docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml ps` -> local admin stack is up with `homepage`, `pgadmin`, `obsidian`, and `portainer`
- `docker exec odoo19-homepage-1 wget http://nginx/healthz` -> HTTP `204`
- Homepage browser snapshot on April 16, 2026 shows stable `Ejecutando` status for Odoo, Odoo directo, Nginx, Portainer, pgAdmin, pgBackRest, and Obsidian
- staging and prod TLS path validated with temporary self-signed certificates: HTTP redirects to HTTPS and the final Odoo response resolves successfully behind TLS

## Current local runtime snapshot
- The project stack is currently up through Docker Desktop with `compose.yaml`, `compose.dev.yaml`, and `compose.admin.yaml`.
- The current local PostgreSQL databases in this workspace are `postgres` and `essensi`, and the active Odoo walkthroughs in this vault assume `essensi` as the local example database.
- Verified running services: `db`, `redis`, `pgbackrest`, `odoo`, `nginx`, `pgadmin`, `obsidian`, and `portainer`.
- Verified running admin landing page: `homepage`
- Local access points in this workspace:
	- Homepage lobby: `http://localhost:8081`
	- Odoo direct: `http://localhost:8069/web/login`
	- Odoo through Nginx: `http://localhost:8088/web/login`
	- pgAdmin: `http://localhost:8080`
	- Obsidian: `http://localhost:3000`
	- Portainer: `https://localhost:9443`
- Default local credentials currently documented in the repo:
	- PostgreSQL user: `odoo`
	- PostgreSQL password: `change_me`
	- Odoo master password: currently `change_me` from `config/odoo*.conf`
	- pgAdmin user: `admin@example.com`
	- pgAdmin password: `change_me`
	- Obsidian user: `obsidian`
	- Obsidian password: `change_me`
- Obsidian does not open the vault automatically on first launch; the vault must be opened from `/config/ObsidianVault`, which maps to the repository `docs/` directory.
- After the first manual open, the vault selection should persist in the `obsidian-config` volume.

## Current known gaps
- live deploy to a real target host is still pending
- restore drill against a real backup set is still pending
- Odoo master password still comes from `config/odoo*.conf`; `ODOO_ADMIN_PASSWORD` is not yet wired into the runtime config automatically

## Why Obsidian is in the admin layer
- It is useful for local documentation and knowledge capture.
- It should not be required in staging or production runtime.
- Keeping it in `compose.admin.yaml` preserves a cleaner platform base.

## Next recommended implementation slice
- Automate first-time server bootstrap.
- Exercise the live deploy path against real `dev`, `staging`, and `prod` targets.
- Add deeper data anonymization for restored staging data.
- Add scheduled restore drills from offsite backup sets.

## Links
- [Platform](platform.md)
- [Services](services.md)
- [Delivery](delivery.md)
- [Operations](operations.md)
- [Platform bootstrap doc](../architecture/platform-bootstrap.md)
- [Service map](../architecture/service-map.md)
- [Stack topology](stack_topology.md)
- [Environment State Model](environment_state_model.md)
- [Local development runbook](../runbooks/local-development.md)
- [Environments and promotions](../runbooks/environments-and-promotions.md)
- [Secrets and configuration](../runbooks/secrets-and-config.md)
- [CI/CD scaffold](../runbooks/ci-cd-scaffold.md)
- [Deployment over SSH](../runbooks/deployment-over-ssh.md)
- [Backup and restore runbook](../runbooks/backup-and-restore.md)
- [Staging neutralization runbook](../runbooks/staging-neutralization.md)
- [Offsite backups runbook](../runbooks/offsite-backups.md)
- [Runtime validation](../runbooks/runtime-validation.md)
