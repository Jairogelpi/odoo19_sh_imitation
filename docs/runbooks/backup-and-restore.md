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
./ops/restore/restore-to-staging.sh <db_dump_path> <filestore_archive> <staging_filestore_dir>
```

This script prints the operator checklist for restoring a recent production copy into staging.

## Next step

Upgrade this bootstrap runbook with:

- production retention policy refinement
- offsite `S3-compatible` copy
- scheduled restore drills
- staging neutralization checklist
