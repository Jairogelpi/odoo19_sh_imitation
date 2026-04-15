# Staging Restore Neutralization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn staging restore from a manual checklist into an automated, production-safe flow that restores a database and filestore, then neutralizes outbound and scheduled activity before access is opened.

**Architecture:** Keep the implementation shell-first and environment-aware. Add a staging-only sink service (`Mailpit`), a SQL-based neutralization script that deactivates dangerous operational paths in the restored database, and a restore wrapper that orchestrates database restore, filestore extraction, and post-restore neutralization through Docker Compose. Mirror the resulting workflow in the runbooks and Obsidian brain.

**Tech Stack:** Docker Compose, Bash, PostgreSQL `psql`/`pg_restore`, Odoo 19 staging config, Mailpit, Markdown docs

---

## File Structure Map

### Existing files to modify

- `compose.staging.yaml`
  - Add a staging-only `mailpit` service and any safe access pattern needed for staging review.
- `.env.staging.example`
  - Add the variables required by the restore/neutralization flow.
- `ops/restore/restore-to-staging.sh`
  - Replace the checklist-only script with an actual orchestration script.
- `docs/runbooks/backup-and-restore.md`
  - Upgrade the restore section from checklist to executable workflow.
- `docs/runbooks/secrets-and-config.md`
  - Document the new staging restore and neutralization variables.
- `docs/runbooks/environments-and-promotions.md`
  - Record the new staging sink and neutralization expectations.
- `docs/architecture/platform-bootstrap.md`
  - Reflect that staging restore neutralization is implemented.
- `README.md`
  - Link to the upgraded restore flow.
- `docs/00_Odoo_Brain.md`
  - Add the upgraded restore flow to the main knowledge map.
- `docs/brain/operations.md`
  - Add the restore/neutralization operational entrypoints.
- `docs/brain/delivery.md`
  - Capture how staging promotion now depends on restore plus neutralization.
- `docs/brain/platform.md`
  - Reflect the staging sink and post-restore safeguards.
- `docs/brain/platform_bootstrap_status.md`
  - Move the restore/neutralization slice from planned to implemented.
- `docs/brain/services.md`
  - Add `mailpit` to the service mental model.
- `docs/architecture/service-map.md`
  - Explain the staging-only `mailpit` service and the staging boundary.

### New files to create

- `ops/restore/staging-neutralize.sql`
  - SQL script that deactivates dangerous outgoing and scheduled behaviors in a restored staging database.
- `docs/runbooks/staging-neutralization.md`
  - Focused runbook for what the neutralization script does and what operators should still verify manually.

### Verification strategy

- `docker compose -f compose.yaml -f compose.staging.yaml config`
- `docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/ops/restore/restore-to-staging.sh`
- `docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/backup/scripts/backup-filestore.sh`
- smoke-check the SQL file by ensuring the known table and column names match documented schema references
- `git diff --check`

### Task 1: Add staging mail sink support

**Files:**
- Modify: `compose.staging.yaml`
- Modify: `.env.staging.example`
- Modify: `docs/architecture/service-map.md`
- Modify: `docs/brain/services.md`

- [ ] **Step 1: Write the failing staging compose check**

Run: `docker compose -f compose.yaml -f compose.staging.yaml config`
Expected: PASS today without a `mailpit` service; this is the baseline before the staging sink is added.

- [ ] **Step 2: Add a staging-only `mailpit` service**

Add a `mailpit` service to `compose.staging.yaml` that:
- runs only in staging
- stays on the internal Docker network
- optionally exposes the web UI on a staging-specific port if that is the chosen operational access pattern

- [ ] **Step 3: Add staging example variables**

Add explicit staging variables such as:
- `STAGING_WEB_BASE_URL`
- `STAGING_MAILPIT_SMTP_HOST`
- `STAGING_MAILPIT_SMTP_PORT`

- [ ] **Step 4: Update the service docs**

Document `mailpit` as a staging-only neutralization support service in the service map and brain.

- [ ] **Step 5: Re-run the compose verification**

Run: `docker compose -f compose.yaml -f compose.staging.yaml config`
Expected: PASS with the new `mailpit` service present.

### Task 2: Add database neutralization SQL

**Files:**
- Create: `ops/restore/staging-neutralize.sql`
- Modify: `docs/runbooks/staging-neutralization.md`
- Modify: `docs/runbooks/environments-and-promotions.md`

- [ ] **Step 1: Write the neutralization SQL file**

Create `ops/restore/staging-neutralize.sql` with guarded SQL blocks that:
- deactivate all `ir_mail_server` rows, then redirect one server to `Mailpit` when possible
- deactivate `fetchmail_server`
- deactivate `ir_cron`
- cancel queued `mail_mail` rows in `outgoing`
- best-effort cancel queued `sms_sms` rows if the table exists
- set `web.base.url` in `ir_config_parameter` to the staging URL when provided

- [ ] **Step 2: Keep the SQL defensive**

Use `information_schema` checks or `IF EXISTS` blocks so the script remains safe if optional modules are absent.

- [ ] **Step 3: Document neutralization behavior**

Write down exactly what is disabled, what is redirected, and what still requires operator judgment.

### Task 3: Turn staging restore into an actual orchestration script

**Files:**
- Modify: `ops/restore/restore-to-staging.sh`
- Modify: `docs/runbooks/backup-and-restore.md`
- Create: `docs/runbooks/staging-neutralization.md`

- [ ] **Step 1: Replace the checklist wrapper**

Rewrite `ops/restore/restore-to-staging.sh` so it:
- accepts `db_dump_path`, `filestore_archive`, and `target_database`
- requires `STAGING_ENV_FILE`
- validates that the files exist
- validates the staging compose config

- [ ] **Step 2: Implement database restore**

Start the required staging services, then:
- terminate existing connections for the target database
- drop and recreate the target database
- restore via `psql` for plain SQL dumps or `pg_restore` for custom dumps

- [ ] **Step 3: Implement filestore restore**

Restore the archive into `/var/lib/odoo/filestore/<target_database>` inside the staging Odoo container or volume.

- [ ] **Step 4: Apply neutralization automatically**

Run `ops/restore/staging-neutralize.sql` through the staging database container after restore.

- [ ] **Step 5: Print post-restore smoke checks**

End the script with a concise checklist that tells the operator to:
- verify login
- verify no cron jobs are active
- verify outgoing mail points to `Mailpit`
- verify the expected `web.base.url`

- [ ] **Step 6: Verify script syntax**

Run: `docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/ops/restore/restore-to-staging.sh`
Expected: PASS

### Task 4: Align the docs and Obsidian brain

**Files:**
- Modify: `README.md`
- Modify: `docs/00_Odoo_Brain.md`
- Modify: `docs/runbooks/backup-and-restore.md`
- Create: `docs/runbooks/staging-neutralization.md`
- Modify: `docs/runbooks/secrets-and-config.md`
- Modify: `docs/runbooks/environments-and-promotions.md`
- Modify: `docs/architecture/platform-bootstrap.md`
- Modify: `docs/architecture/service-map.md`
- Modify: `docs/brain/operations.md`
- Modify: `docs/brain/delivery.md`
- Modify: `docs/brain/platform.md`
- Modify: `docs/brain/platform_bootstrap_status.md`
- Modify: `docs/brain/services.md`

- [ ] **Step 1: Update runbooks**

Describe:
- required staging env variables
- the exact restore command
- what the SQL neutralization changes
- how operators inspect `Mailpit`

- [ ] **Step 2: Update the brain**

Mirror the restore/neutralization flow in the home note plus the platform, operations, delivery, services, and bootstrap status notes.

- [ ] **Step 3: Verify doc integrity**

Run: `git diff --check`
Expected: PASS

### Task 5: Final verification and commit

**Files:**
- Test: `compose.staging.yaml`
- Test: `ops/restore/restore-to-staging.sh`
- Test: documentation paths above

- [ ] **Step 1: Re-run all fresh verification commands**

Run:

```powershell
docker compose -f compose.yaml -f compose.staging.yaml config
docker run --rm -v "${PWD}:/work" odoo19-odoo:test bash -n /work/ops/restore/restore-to-staging.sh
git diff --check
```

Expected: all commands PASS

- [ ] **Step 2: Commit**

```bash
git add compose.staging.yaml .env.staging.example ops/restore/restore-to-staging.sh ops/restore/staging-neutralize.sql README.md docs/00_Odoo_Brain.md docs/architecture/platform-bootstrap.md docs/architecture/service-map.md docs/brain/operations.md docs/brain/delivery.md docs/brain/platform.md docs/brain/platform_bootstrap_status.md docs/brain/services.md docs/runbooks/backup-and-restore.md docs/runbooks/staging-neutralization.md docs/runbooks/secrets-and-config.md docs/runbooks/environments-and-promotions.md
git commit -m "feat: automate staging restore neutralization"
```
