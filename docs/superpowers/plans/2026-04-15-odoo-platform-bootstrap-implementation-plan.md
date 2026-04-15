# Odoo Platform Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current local Odoo 19 sandbox into a safe, versioned starting point for the self-hosted platform and bootstrap the GitHub remote without leaking secrets or runtime data.

**Architecture:** Keep the first implementation slice focused on repository hygiene and platform scaffolding. Separate versioned infrastructure from live state, introduce environment-aware compose files and templates, and make the current project safe to push before layering in reverse proxy, backup, and CI/CD work.

**Tech Stack:** Docker Compose, Odoo 19, PostgreSQL 16, Nginx, Git, GitHub Actions, GHCR

---

## File Structure Map

### Existing files to modify

- `docker-compose.yml`
  - Replace hard-coded credentials with environment references or move it into a versioned base compose shape.
- `config/odoo.conf`
  - Remove real credentials from the tracked file and convert it into a safe template or non-secret baseline.
- `docs/superpowers/specs/2026-04-15-odoo-self-hosted-platform-design.md`
  - Keep as the approved architecture reference; no content changes expected unless implementation reveals a gap.

### Existing paths to stop tracking as live state

- `postgres/`
  - Live PostgreSQL data directory that must never be committed.
- `pgadmin/`
  - Local runtime/admin state that must never be committed.

### New files to create

- `.gitignore`
  - Exclude runtime data, secrets, editor noise, backup artifacts, and local overrides.
- `.env.example`
  - Safe example of required environment variables.
- `config/odoo.conf.example`
  - Safe tracked example file for local setup.
- `compose.yaml`
  - New shared base compose definition.
- `compose.dev.yaml`
  - Development overrides.
- `compose.admin.yaml`
  - Optional admin tools such as pgAdmin.
- `odoo/Dockerfile`
  - Project image scaffold based on `odoo:19.0`.
- `odoo/requirements.txt`
  - Pinned Python dependency placeholder.
- `nginx/conf.d/odoo.conf.template`
  - Reverse proxy template with websocket routing scaffold.
- `docs/architecture/platform-bootstrap.md`
  - Short operator note describing local bootstrap and data locations.

### Future files intentionally deferred to later tasks

- `compose.staging.yaml`
- `compose.prod.yaml`
- `pgbackrest/pgbackrest.conf`
- `.github/workflows/deploy.yml`
- `ops/restore/*`

These stay deferred so the first slice remains small, testable, and safe to push.

### Task 1: Make the repository safe for GitHub

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `config/odoo.conf.example`
- Modify: `docker-compose.yml`
- Modify: `config/odoo.conf`

- [ ] **Step 1: Inventory the current sensitive and runtime files**

Run: `Get-ChildItem -Force; Get-ChildItem postgres,pgadmin,config -Force`
Expected: Confirm that `postgres/`, `pgadmin/`, and `config/odoo.conf` contain data or credentials that must not be committed as-is.

- [ ] **Step 2: Write the failing safety check**

Run: `git status --short`
Expected: `fatal: not a git repository` or an empty result if a repo already exists. This confirms Git safety checks are not yet in place.

- [ ] **Step 3: Add the ignore rules**

Create `.gitignore` with at least:

```gitignore
.env
.env.*
!.env.example
postgres/
pgadmin/
backups/
*.log
__pycache__/
.DS_Store
.idea/
.vscode/
```

- [ ] **Step 4: Replace tracked secrets with safe examples**

Create `.env.example` and `config/odoo.conf.example`, then sanitize the tracked `docker-compose.yml` and `config/odoo.conf` so they no longer contain real passwords or live-only values.

Use example content like:

```env
POSTGRES_DB=postgres
POSTGRES_USER=odoo
POSTGRES_PASSWORD=change_me
ODOO_ADMIN_PASSWORD=change_me
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=change_me
```

- [ ] **Step 5: Verify no obvious secrets remain in tracked files**

Run: `rg -n "Gusano2001@|Admin123!|admin_passwd =|db_password =" .`
Expected: No matches in tracked files except optional example placeholders that are clearly non-secret.

- [ ] **Step 6: Commit**

```bash
git add .gitignore .env.example docker-compose.yml config/odoo.conf config/odoo.conf.example
git commit -m "chore: sanitize repo for initial git bootstrap"
```

### Task 2: Initialize Git and connect the GitHub remote

**Files:**
- Modify: `.git/config`
- Test: Git history and remote metadata

- [ ] **Step 1: Initialize the repository if needed**

Run: `git init -b main`
Expected: A local Git repository on branch `main`.

- [ ] **Step 2: Add the GitHub remote**

Run: `git remote add origin https://github.com/Jairogelpi/odoo19_sh_imitation.git`
Expected: `git remote -v` shows `origin`.

- [ ] **Step 3: Stage the current safe starting point**

Run: `git add .`
Expected: Only sanitized source files and docs are staged, not `postgres/` or `pgadmin/`.

- [ ] **Step 4: Create the initial bootstrap commit**

Run: `git commit -m "chore: bootstrap odoo platform repository"`
Expected: First commit created successfully.

- [ ] **Step 5: Push to GitHub**

Run: `git push -u origin main`
Expected: Remote branch `main` created on `Jairogelpi/odoo19_sh_imitation`.

### Task 3: Introduce the platform compose scaffold

**Files:**
- Create: `compose.yaml`
- Create: `compose.dev.yaml`
- Create: `compose.admin.yaml`
- Modify: `docker-compose.yml`
- Create: `docs/architecture/platform-bootstrap.md`

- [ ] **Step 1: Write a failing compose verification**

Run: `docker compose -f compose.yaml -f compose.dev.yaml config`
Expected: FAIL because the new compose files do not exist yet.

- [ ] **Step 2: Create the base compose file**

Add `compose.yaml` with the shared services skeleton:

```yaml
services:
  db:
    image: postgres:16
  odoo:
    build:
      context: .
      dockerfile: odoo/Dockerfile
  nginx:
    image: nginx:1.27-alpine
```

- [ ] **Step 3: Create dev/admin overrides**

Add:
- `compose.dev.yaml` for local ports, local bind mounts, and dev-only defaults
- `compose.admin.yaml` for `pgadmin`

- [ ] **Step 4: Preserve backward compatibility during transition**

Either:
- keep `docker-compose.yml` as a thin compatibility wrapper
- or replace it with a comment-only migration note and point users to the new compose files

Choose the path that keeps the local repo runnable with minimal confusion.

- [ ] **Step 5: Verify merged compose output**

Run: `docker compose -f compose.yaml -f compose.dev.yaml config`
Expected: PASS with a valid merged configuration.

- [ ] **Step 6: Commit**

```bash
git add compose.yaml compose.dev.yaml compose.admin.yaml docker-compose.yml docs/architecture/platform-bootstrap.md
git commit -m "feat: add platform compose scaffold"
```

### Task 4: Add the Odoo image and config baseline

**Files:**
- Create: `odoo/Dockerfile`
- Create: `odoo/requirements.txt`
- Modify: `config/odoo.conf`
- Create: `odoo/scripts/entrypoint-notes.md`

- [ ] **Step 1: Write a failing image build check**

Run: `docker build -f odoo/Dockerfile .`
Expected: FAIL because the Dockerfile does not exist yet.

- [ ] **Step 2: Create the Dockerfile scaffold**

Use a minimal build:

```dockerfile
FROM odoo:19.0
COPY odoo/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
```

- [ ] **Step 3: Create a safe config baseline**

Keep `config/odoo.conf` free of real passwords and ensure it only contains non-secret options such as:

```ini
[options]
addons_path = /mnt/extra-addons
data_dir = /var/lib/odoo
proxy_mode = False
list_db = True
dbfilter = ^.*$
```

- [ ] **Step 4: Verify the image builds**

Run: `docker build -f odoo/Dockerfile .`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add odoo/Dockerfile odoo/requirements.txt config/odoo.conf odoo/scripts/entrypoint-notes.md
git commit -m "feat: add custom odoo image baseline"
```

### Task 5: Add Nginx reverse proxy scaffold

**Files:**
- Create: `nginx/conf.d/odoo.conf.template`
- Modify: `compose.yaml`
- Test: `docker compose -f compose.yaml -f compose.dev.yaml config`

- [ ] **Step 1: Write the failing proxy file check**

Run: `Test-Path nginx/conf.d/odoo.conf.template`
Expected: `False`

- [ ] **Step 2: Add the Nginx template**

Include:
- app upstream to Odoo HTTP
- websocket location routed to `8072`
- forwarded headers
- upload size and timeout baseline

- [ ] **Step 3: Wire Nginx into the compose scaffold**

Mount the template and expose `80/443` only through nginx in the future production shape. Dev may still expose app ports if needed during transition.

- [ ] **Step 4: Verify compose output remains valid**

Run: `docker compose -f compose.yaml -f compose.dev.yaml config`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add nginx/conf.d/odoo.conf.template compose.yaml
git commit -m "feat: add nginx reverse proxy scaffold"
```

### Task 6: Document the bootstrap and next implementation slice

**Files:**
- Create: `docs/architecture/platform-bootstrap.md`
- Modify: `docs/superpowers/plans/2026-04-15-odoo-platform-bootstrap-implementation-plan.md`

- [ ] **Step 1: Write operator bootstrap notes**

Document:
- required local files
- where persistent runtime data should live
- which compose files to use
- what is intentionally not implemented yet

- [ ] **Step 2: Verify documentation paths are valid**

Run: `Get-ChildItem docs/architecture,docs/superpowers/plans`
Expected: Both paths exist and contain the expected docs.

- [ ] **Step 3: Commit**

```bash
git add docs/architecture/platform-bootstrap.md docs/superpowers/plans/2026-04-15-odoo-platform-bootstrap-implementation-plan.md
git commit -m "docs: add platform bootstrap runbook"
```

## Notes for Execution

- Do not push anything until Task 1 completes and secrets are sanitized.
- Do not track `postgres/` or `pgadmin/` even if they already exist locally.
- Prefer keeping the first implementation slice small enough to verify with `docker compose config` and image build checks.
- Once this bootstrap plan is complete, the next plan should cover:
  - `compose.staging.yaml`
  - `compose.prod.yaml`
  - `pgBackRest`
  - restore scripts
  - GitHub Actions deployment workflow
