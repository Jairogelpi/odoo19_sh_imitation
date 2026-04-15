# Backup and Restore Runbook

## Scope

This runbook documents the bootstrap backup and restore flow until `pgBackRest` and offsite automation are fully wired.

## Database backups

The platform now includes a `pgbackrest` utility container and repository volume in the base compose.

Bootstrap commands:

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/stanza-create.sh
docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/check-db.sh
docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/backup-db.sh
```

Current local status:

- `stanza-create` passes
- `check` passes
- full local backup passes
- PostgreSQL is using `archive_mode=on` with `pgbackrest archive-push`

Remaining follow-up:

- production retention hardening
- offsite copy
- scheduled restore drill automation

## Filestore backups

Use:

```bash
./backup/scripts/backup-filestore.sh <source_filestore_dir> <backup_dir>
```

Example:

```bash
./backup/scripts/backup-filestore.sh /srv/odoo/project/prod/filestore /srv/odoo/project/backups
```

## Staging restore

Use:

```bash
STAGING_ENV_FILE=/srv/odoo/env/staging.env \
./ops/restore/restore-to-staging.sh <db_dump_path> <filestore_archive> <target_database>
```

Example:

```bash
STAGING_ENV_FILE=/srv/odoo/env/staging.env \
./ops/restore/restore-to-staging.sh \
  /srv/odoo/project/backups/prod-latest.sql.gz \
  /srv/odoo/project/backups/filestore-latest.tar.gz \
  staging_prod_latest
```

What it does now:

- validates the staging compose config
- starts the required staging services
- drops and recreates the target database
- restores the database dump
- restores the filestore into `/var/lib/odoo/filestore/<target_database>`
- applies `ops/restore/staging-neutralize.sql`
- prints post-restore smoke checks

Staging-specific neutralization details live in:

- `docs/runbooks/staging-neutralization.md`

Current limitation:

- the wrapper and neutralization flow are verified for compose validity and script syntax, but not yet exercised end-to-end against a real backup set from this workspace

## Next step

Upgrade this bootstrap runbook with:

- production retention policy refinement
- offsite `S3-compatible` copy
- scheduled restore drills
- automated restore drill scheduling
