# Operations

## What runs in Docker
- PostgreSQL 16 with `archive_mode` enabled for `pgBackRest`
- Redis
- pgBackRest utility container
- Odoo 19.0
- Nginx
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
- [Backup and restore runbook](../runbooks/backup-and-restore.md)

## Service ports
- Odoo direct dev: `8069`
- Nginx dev: `8088`
- pgAdmin admin: `8080`
- Obsidian GUI: `3000` and `3001`
- Staging/prod edge ports: `80` and `443`

## Start commands
- `docker compose -f compose.yaml -f compose.dev.yaml up -d`
- `docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d`
- `docker compose -f compose.yaml -f compose.dev.yaml logs -f odoo nginx`
- `docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml logs -f obsidian`
- `docker compose -f compose.yaml -f compose.dev.yaml exec redis redis-cli ping`
- `docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/stanza-create.sh`
- `docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/check-db.sh`
- `docker compose -f compose.yaml -f compose.dev.yaml exec pgbackrest /scripts/backup-db.sh`

## Notes
- `docker-compose.yml` remains a legacy local compatibility entrypoint.
- `compose.yaml` plus overrides is the forward-looking platform path.
- Obsidian uses a browser-accessible desktop session.
- The vault is the `docs/` directory, so the knowledge graph and the source notes stay in one place.
- If you change the vault layout, update the home note, this operations note, and the bootstrap status note together.
