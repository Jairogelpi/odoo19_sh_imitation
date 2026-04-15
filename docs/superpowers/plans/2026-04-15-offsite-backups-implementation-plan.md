# Offsite Backups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an offsite backup flow that exports production backup artifacts and replicates them to S3-compatible storage without adding a permanent runtime service.

**Architecture:** Keep the runtime stack unchanged and implement offsite replication as operational scripts. Export timestamped snapshots of the `pgBackRest` repository and Odoo filestore from existing containers, then upload them with ephemeral `rclone` containers configured through environment variables. Document the flow in runbooks and mirror it into the Obsidian brain.

**Tech Stack:** Docker Compose, Bash, rclone, pgBackRest, S3-compatible object storage, Markdown docs

---

## File Structure Map

### Existing files to modify

- `.env.example`
- `.env.prod.example`
- `docs/runbooks/backup-and-restore.md`
- `docs/runbooks/secrets-and-config.md`
- `docs/runbooks/environments-and-promotions.md`
- `docs/architecture/platform-bootstrap.md`
- `README.md`
- `docs/00_Odoo_Brain.md`
- `docs/brain/operations.md`
- `docs/brain/platform.md`
- `docs/brain/platform_bootstrap_status.md`
- `docs/brain/delivery.md`

### New files to create

- `backup/scripts/export-pgbackrest-repo.sh`
- `backup/scripts/export-odoo-filestore.sh`
- `backup/scripts/offsite-sync-rclone.sh`
- `backup/scripts/run-offsite-backup.sh`
- `docs/runbooks/offsite-backups.md`

### Verification strategy

- `docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/export-pgbackrest-repo.sh`
- `docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/export-odoo-filestore.sh`
- `docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/offsite-sync-rclone.sh`
- `docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/run-offsite-backup.sh`
- `docker compose -f compose.yaml -f compose.prod.yaml config`
- `docker run --rm rclone/rclone:latest version`
- `git diff --check`

### Task 1: Define offsite backup variables

**Files:**
- Modify: `.env.example`
- Modify: `.env.prod.example`
- Modify: `docs/runbooks/secrets-and-config.md`

- [ ] **Step 1: Add offsite configuration variables**

Add safe example values for:

- `OFFSITE_ENV_FILE`
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

- [ ] **Step 2: Document what each variable is for**

Update the secrets runbook so operators know which variables live in the real prod env file and which are only used when invoking the wrapper script.

### Task 2: Add export and sync scripts

**Files:**
- Create: `backup/scripts/export-pgbackrest-repo.sh`
- Create: `backup/scripts/export-odoo-filestore.sh`
- Create: `backup/scripts/offsite-sync-rclone.sh`
- Create: `backup/scripts/run-offsite-backup.sh`

- [ ] **Step 1: Add pgBackRest export script**

Create a script that:

- requires `OFFSITE_ENV_FILE`
- validates the production compose config
- starts required services if needed
- exports `/var/lib/pgbackrest` from the `pgbackrest` container into a timestamped archive

- [ ] **Step 2: Add filestore export script**

Create a script that:

- requires `OFFSITE_ENV_FILE`
- validates the production compose config
- exports `/var/lib/odoo/filestore` from the `odoo` container into a timestamped archive

- [ ] **Step 3: Add rclone sync wrapper**

Create a script that:

- requires S3-compatible credentials and endpoint variables
- configures `rclone` through environment variables following official docs
- uploads a local directory to the configured remote path with an ephemeral `rclone` container

- [ ] **Step 4: Add one-shot orchestrator**

Create `run-offsite-backup.sh` that:

- requires `OFFSITE_ENV_FILE`
- runs `pgbackrest` full backup first
- exports the pgBackRest repository snapshot
- exports the filestore snapshot
- syncs both local archive directories to the offsite bucket
- prints the resulting archive paths and target prefixes

### Task 3: Document offsite operations and brain notes

**Files:**
- Create: `docs/runbooks/offsite-backups.md`
- Modify: `docs/runbooks/backup-and-restore.md`
- Modify: `docs/runbooks/environments-and-promotions.md`
- Modify: `docs/architecture/platform-bootstrap.md`
- Modify: `README.md`
- Modify: `docs/00_Odoo_Brain.md`
- Modify: `docs/brain/operations.md`
- Modify: `docs/brain/platform.md`
- Modify: `docs/brain/platform_bootstrap_status.md`
- Modify: `docs/brain/delivery.md`

- [ ] **Step 1: Add dedicated offsite runbook**

Document:

- the exact wrapper command
- what gets exported
- how the S3-compatible remote is configured
- current limitations

- [ ] **Step 2: Update the existing backup docs**

Link the offsite runbook from the main backup-and-restore runbook and mark offsite replication as implemented.

- [ ] **Step 3: Mirror it into the brain**

Update the Obsidian notes so operations, platform status, and delivery all mention the new offsite path.

### Task 4: Verify and commit

**Files:**
- Test: scripts and docs above

- [ ] **Step 1: Run fresh verification commands**

Run:

```powershell
docker compose -f compose.yaml -f compose.prod.yaml config
docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/export-pgbackrest-repo.sh
docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/export-odoo-filestore.sh
docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/offsite-sync-rclone.sh
docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/run-offsite-backup.sh
docker run --rm rclone/rclone:latest version
git diff --check
```

Expected: all commands PASS

- [ ] **Step 2: Commit**

```bash
git add .env.example .env.prod.example backup/scripts/export-pgbackrest-repo.sh backup/scripts/export-odoo-filestore.sh backup/scripts/offsite-sync-rclone.sh backup/scripts/run-offsite-backup.sh README.md docs/00_Odoo_Brain.md docs/architecture/platform-bootstrap.md docs/brain/operations.md docs/brain/platform.md docs/brain/platform_bootstrap_status.md docs/brain/delivery.md docs/runbooks/backup-and-restore.md docs/runbooks/offsite-backups.md docs/runbooks/secrets-and-config.md docs/runbooks/environments-and-promotions.md
git commit -m "feat: add offsite backup workflow"
```
