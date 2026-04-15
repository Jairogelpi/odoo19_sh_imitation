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
- `docker compose -f compose.yaml -f compose.dev.yaml exec redis redis-cli ping` -> `PONG`
- `docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/check-db.sh` -> success
- `docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/backup-db.sh` -> full backup completed
- `powershell -ExecutionPolicy Bypass -File .\ops\health\check-local-stack.ps1` -> local stack verification script added
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
- offsite backup scripts are present, pending end-to-end upload validation with real offsite credentials

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
- [Local development runbook](../runbooks/local-development.md)
- [Environments and promotions](../runbooks/environments-and-promotions.md)
- [Secrets and configuration](../runbooks/secrets-and-config.md)
- [CI/CD scaffold](../runbooks/ci-cd-scaffold.md)
- [Deployment over SSH](../runbooks/deployment-over-ssh.md)
- [Backup and restore runbook](../runbooks/backup-and-restore.md)
- [Staging neutralization runbook](../runbooks/staging-neutralization.md)
- [Offsite backups runbook](../runbooks/offsite-backups.md)
- [Offsite backups runbook](../runbooks/offsite-backups.md)
