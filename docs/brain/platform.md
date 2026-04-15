# Platform

## What lives here
The platform now has a core runtime plus an optional knowledge/admin layer.

Core runtime:
- PostgreSQL 16
- Odoo 19.0
- Nginx reverse proxy

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
- [Bootstrap status](platform_bootstrap_status.md)

## Service endpoints
- Odoo direct dev port: `http://localhost:8069`
- Nginx dev port: `http://localhost:8088`
- pgAdmin admin port: `http://localhost:8080`
- Obsidian GUI: `http://localhost:3000` and `https://localhost:3001`

## Notes
- `compose.yaml` is the base platform and should stay production-safe.
- `compose.admin.yaml` is where optional admin and knowledge services belong.
- The Obsidian container is a browser-accessible desktop app, not the Windows desktop binary.
- The vault root is the `docs/` directory, mounted into the container as `ObsidianVault`.
- If you change ports or service names, update this note, the home note, and the bootstrap status note together.
