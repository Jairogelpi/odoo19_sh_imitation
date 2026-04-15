# Backup and Restore Runbook

## Scope

This runbook documents the bootstrap backup and restore flow until `pgBackRest` and offsite automation are fully wired.

## Database backups

Short-term bootstrap recommendation:

- run logical database dumps before risky changes
- store dumps outside the git checkout
- promote to `pgBackRest` as the next platform step

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

- `pgBackRest` commands and retention policy
- offsite `S3-compatible` copy
- scheduled restore drills
- staging neutralization checklist
