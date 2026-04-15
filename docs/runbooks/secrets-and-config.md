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

## Current variable groups

### Database and Odoo core

- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `ODOO_ADMIN_PASSWORD`
- `PGBACKREST_STANZA`

### Reverse proxy

- `SERVER_NAME`

### Admin and knowledge layer

- `PGADMIN_DEFAULT_EMAIL`
- `PGADMIN_DEFAULT_PASSWORD`
- `PUID`
- `PGID`
- `TZ`
- `OBSIDIAN_CUSTOM_USER`
- `OBSIDIAN_PASSWORD`

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
- update this runbook and the Obsidian brain when variables are added or removed
