# Backup and Restore Runbook

## Scope

This runbook documents the bootstrap backup and restore flow until `pgBackRest` and offsite automation are fully wired.

## Database backups

The platform now includes a `pgbackrest` utility container and repository volume in the base compose.

No manual `stanza-create` step is required for the first local startup anymore.

The `db` container now bootstraps the stanza automatically the first time PostgreSQL needs to archive a WAL file.

Bootstrap and repair commands:

```bash
docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/stanza-create.sh
docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/check-db.sh
docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/backup-db.sh
```

If you ever replace the `pgbackrest-repo` volume manually, the explicit `stanza-create` command remains the fastest repair step.

Current local status:

- `stanza-create` passes
- `check` passes
- full local backup passes
- PostgreSQL is using `archive_mode=on` with `pgbackrest archive-push`
- offsite replication scripts now exist for production backup artifacts

Remaining follow-up:

- production retention hardening
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

Current verification status:

- the wrapper and neutralization flow are syntax-checked in CI and still validated for compose consistency
- end-to-end restore drill against a real backup set is still pending
- local runtime validation evidence lives in `docs/runbooks/runtime-validation.md`

## Next step

Upgrade this bootstrap runbook with:

- production retention policy refinement
- scheduled production offsite runs
- scheduled restore drills
- automated restore drill scheduling

## Offsite replication

Use:

```bash
OFFSITE_ENV_FILE=/srv/odoo/env/prod.env \
bash backup/scripts/run-offsite-backup.sh
```

Details live in:

- `docs/runbooks/offsite-backups.md`
- `docs/runbooks/runtime-validation.md`
