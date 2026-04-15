# Platform

## What lives here
The platform now has a core runtime plus an optional knowledge/admin layer.

Core runtime:
- PostgreSQL 16 with `pgBackRest` archive support
- Redis
- pgBackRest utility container
- Odoo 19.0
- Nginx reverse proxy

Staging support layer:
- Mailpit as the post-restore SMTP sink

Operational backup layer:
- Offsite replication scripts that export snapshots and upload them with ephemeral `rclone`

Optional admin and knowledge layer:
- pgAdmin
- Obsidian as the local knowledge workspace

## Why this matters
This is the layer that keeps the stack repeatable. If the platform note changes, the compose file and environment defaults should change with it.

## Source files
- [compose.yaml](../../compose.yaml)
- [compose.dev.yaml](../../compose.dev.yaml)
- [compose.admin.yaml](../../compose.admin.yaml)
- [compose.staging.yaml](../../compose.staging.yaml)
- [compose.prod.yaml](../../compose.prod.yaml)
- [docker-compose.yml](../../docker-compose.yml)
- [.env.example](../../.env.example)
- [Platform bootstrap doc](../architecture/platform-bootstrap.md)
- [Service map](../architecture/service-map.md)
- [Bootstrap status](platform_bootstrap_status.md)
- [Services](services.md)

## Service endpoints
- Odoo direct dev port: `http://localhost:8069`
- Nginx dev port: `http://localhost:8088`
- pgAdmin admin port: `http://localhost:8080`
- Obsidian GUI: `http://localhost:3000` and `https://localhost:3001`

## Notes
- `compose.yaml` is the base platform and should stay production-safe.
- `compose.admin.yaml` is where optional admin and knowledge services belong.
- Local backup flow is now testable with `pgBackRest` from the base stack.
- The custom `db`, `pgbackrest`, and `odoo` services can run from local builds or CI-published GHCR images.
- The staging layer now includes `mailpit` so restored copies cannot send real mail by default.
- Production offsite replication currently happens through wrapper scripts rather than a long-running backup service.
- The service ownership and boundaries live in the service map and should be updated whenever the stack changes.
- The Obsidian container is a browser-accessible desktop app, not the Windows desktop binary.
- The vault root is the `docs/` directory, mounted into the container as `ObsidianVault`.
- If you change ports or service names, update this note, the home note, and the bootstrap status note together.
