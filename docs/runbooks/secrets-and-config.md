# Secrets and Configuration

## Goal

Define how configuration should be split between tracked examples and real environment secrets.

## Tracked example files

- `.env.example`
- `.env.dev.example`
- `.env.staging.example`
- `.env.prod.example`

These files are safe templates only. They must never contain real passwords, tokens, or customer-specific domains.

## Real runtime files

Recommended local pattern:

- copy the appropriate example file
- create a real untracked `.env`
- run the compose command with that local `.env`

Examples:

```powershell
Copy-Item .env.dev.example .env
docker compose -f compose.yaml -f compose.dev.yaml up -d
```

For staging and production, the preferred longer-term approach is:

- store secrets outside the repository
- inject them through GitHub environment secrets, Vault, 1Password, or SOPS-managed files

For staging restore automation, the wrapper script also expects:

- `STAGING_ENV_FILE`

This should point to the real untracked staging env file on the target host.

## Current variable groups

### Database and Odoo core

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `ODOO_ADMIN_PASSWORD`
- `PGBACKREST_STANZA`

### Reverse proxy

- `SERVER_NAME`

### Optional image overrides

- `POSTGRES_IMAGE`
- `PGBACKREST_IMAGE`
- `ODOO_IMAGE`

### Staging restore and neutralization

- `STAGING_WEB_BASE_URL`
- `STAGING_MAILPIT_SMTP_HOST`
- `STAGING_MAILPIT_SMTP_PORT`
- `STAGING_MAILPIT_UI_PORT`

### Admin and knowledge layer

- `PGADMIN_DEFAULT_EMAIL`
- `PGADMIN_DEFAULT_PASSWORD`
- `PUID`
- `PGID`
- `TZ`
- `OBSIDIAN_CUSTOM_USER`
- `OBSIDIAN_PASSWORD`

## GitHub Environment secrets

These are not stored in the repository and should live in the GitHub Environments for `dev`, `staging`, and `prod`:

- `DEPLOY_HOST`
- `DEPLOY_PORT`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_KNOWN_HOSTS`
- `DEPLOY_APP_DIR`
- `DEPLOY_ENV_FILE`
- `DEPLOY_HEALTHCHECK_URL`
- `GHCR_PULL_USERNAME`
- `GHCR_PULL_TOKEN`

## Environment intent

### Development

- easiest local boot path
- permissive defaults
- admin and knowledge layer usually enabled

### Staging

- production-like hostname
- production-like Odoo settings
- admin layer only when explicitly needed

### Production

- real public hostname
- no optional admin/knowledge services in normal runtime
- secrets should come from a managed source, not a hand-edited `.env` in the repo

## Rules

- never commit real environment files
- never commit tokens or passwords to tracked config
- keep example files aligned with compose and workflow changes
- prefer GitHub Environment secrets plus server-side env files for staging and production deploys
- update this runbook and the Obsidian brain when variables are added or removed
