# Offsite Backups

## Goal

Replicate production backup artifacts to S3-compatible object storage without adding a permanent backup service to the runtime stack.

## Approach

The offsite flow is script-driven:

1. trigger a fresh `pgBackRest` backup
2. export a timestamped snapshot of `/var/lib/pgbackrest`
3. export a timestamped snapshot of `/var/lib/odoo/filestore`
4. upload the local archive directories with an ephemeral `rclone` container

Scripts involved:

- `backup/scripts/export-pgbackrest-repo.sh`
- `backup/scripts/export-odoo-filestore.sh`
- `backup/scripts/offsite-sync-rclone.sh`
- `backup/scripts/run-offsite-backup.sh`

## Required variables

The production env file should define:

- `OFFSITE_LOCAL_ARCHIVE_DIR`
- `OFFSITE_S3_BUCKET`
- `OFFSITE_S3_PATH_PREFIX`
- `OFFSITE_S3_ENDPOINT`
- `OFFSITE_S3_REGION`
- `OFFSITE_S3_ACCESS_KEY_ID`
- `OFFSITE_S3_SECRET_ACCESS_KEY`
- `OFFSITE_S3_PROVIDER`
- `OFFSITE_S3_FORCE_PATH_STYLE`
- `OFFSITE_RCLONE_IMAGE`

The wrapper script also requires:

- `OFFSITE_ENV_FILE`

That variable is the path to the real untracked production env file on the host.

## One-shot production command

```bash
OFFSITE_ENV_FILE=/srv/odoo/env/prod.env \
bash backup/scripts/run-offsite-backup.sh
```

## What gets uploaded

Two remote subpaths are synchronized:

- `pgbackrest`
- `filestore`

They are created under:

```text
<bucket>/<OFFSITE_S3_PATH_PREFIX>/
```

Example:

```text
odoo-backups/project/prod/pgbackrest
odoo-backups/project/prod/filestore
```

## Current limitation

This slice implements offsite replication, but it does not yet:

- schedule itself automatically
- prune local archives beyond whatever operators choose to keep locally
- prove a full restore from offsite within this workspace

Those belong to the next hardening steps.
