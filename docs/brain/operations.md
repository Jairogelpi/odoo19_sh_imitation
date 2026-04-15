# Operations

## What runs in Docker
- PostgreSQL 16 with `archive_mode` enabled for `pgBackRest`
- Redis
- pgBackRest utility container
- Odoo 19.0
- Nginx
- Staging-only `Mailpit`
- Optional `pgAdmin`
- Optional Obsidian knowledge vault

## Compose entry points
- [compose.yaml](../../compose.yaml)
- [compose.dev.yaml](../../compose.dev.yaml)
- [compose.admin.yaml](../../compose.admin.yaml)
- [compose.staging.yaml](../../compose.staging.yaml)
- [compose.prod.yaml](../../compose.prod.yaml)
- [docker-compose.yml](../../docker-compose.yml)
- [.env.example](../../.env.example)
- [Local development runbook](../runbooks/local-development.md)
- [Environments and promotions](../runbooks/environments-and-promotions.md)
- [Secrets and configuration](../runbooks/secrets-and-config.md)
- [Deployment over SSH](../runbooks/deployment-over-ssh.md)
- [Local health check script](../../ops/health/check-local-stack.ps1)
- [Remote deploy script](../../ops/deploy/remote-deploy.sh)
- [Backup and restore runbook](../runbooks/backup-and-restore.md)
- [Staging neutralization runbook](../runbooks/staging-neutralization.md)
- [Staging restore wrapper](../../ops/restore/restore-to-staging.sh)
- [Staging neutralization SQL](../../ops/restore/staging-neutralize.sql)

## Service ports
- Odoo direct dev: `8069`
- Nginx dev: `8088`
- pgAdmin admin: `8080`
- Obsidian GUI: `3000` and `3001`
- Staging/prod edge ports: `80` and `443`
- Staging Mailpit UI on host loopback: `127.0.0.1:8025` by default

## Start commands
- `docker compose -f compose.yaml -f compose.dev.yaml up -d`
- `docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d`
- `docker compose -f compose.yaml -f compose.dev.yaml logs -f odoo nginx`
- `docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml logs -f obsidian`
- `docker compose -f compose.yaml -f compose.dev.yaml exec redis redis-cli ping`
- `docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/stanza-create.sh`
- `docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/check-db.sh`
- `docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/backup-db.sh`
- `powershell -ExecutionPolicy Bypass -File .\ops\health\check-local-stack.ps1`
- `bash ops/deploy/remote-deploy.sh`
- `STAGING_ENV_FILE=/srv/odoo/env/staging.env bash ops/restore/restore-to-staging.sh <db_dump> <filestore_archive> <target_db>`

## Notes
- `docker-compose.yml` remains a legacy local compatibility entrypoint.
- `compose.yaml` plus overrides is the forward-looking platform path.
- Obsidian uses a browser-accessible desktop session.
- The vault is the `docs/` directory, so the knowledge graph and the source notes stay in one place.
- If you change the vault layout, update the home note, this operations note, and the bootstrap status note together.
- Production-shaped deploys now pull immutable GHCR images instead of relying on local builds on the server.
- Restoring staging now includes automatic neutralization before the environment should be reopened.
