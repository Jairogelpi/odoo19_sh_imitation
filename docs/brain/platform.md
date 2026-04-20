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
- Portainer as the local container-management UI

## Current operational snapshot
- The local stack is running through Docker Desktop with `compose.yaml`, `compose.dev.yaml`, and `compose.admin.yaml`.
- Verified running services are `db`, `redis`, `pgbackrest`, `odoo`, `nginx`, `pgadmin`, `obsidian`, and `portainer`.
- Main local access points:
	- Odoo direct: `http://localhost:8069/web/login`
	- Odoo through Nginx: `http://localhost:8088/web/login`
	- pgAdmin: `http://localhost:8080`
	- Obsidian: `http://localhost:3000`
	- Portainer: `https://localhost:9443`
- Default local credentials documented in the repository are:
	- PostgreSQL: `odoo` / `change_me`
	- Odoo master password: `change_me`
	- pgAdmin: `admin@example.com` / `change_me`
	- Obsidian: `obsidian` / `change_me`
	- Portainer: first admin account is created on first launch
- Obsidian starts on its launcher, not inside the vault.
- The mounted vault path inside the container is `/config/ObsidianVault`, which maps to the repository `docs/` directory.
- After the first manual open, the vault choice should persist in the `obsidian-config` volume.

## Why this matters
This is the layer that keeps the stack repeatable. If the platform note changes, the compose file and environment defaults should change with it.

Delivery is the formal base of deployment here: Git, CI/CD, GHCR, environment files, and named volumes are the source of truth for repeatable releases.

## Source files
- [compose.yaml](../../compose.yaml)
- [compose.dev.yaml](../../compose.dev.yaml)
- [compose.admin.yaml](../../compose.admin.yaml)
- [compose.staging.yaml](../../compose.staging.yaml)
- [compose.prod.yaml](../../compose.prod.yaml)
- [compose.legacy.yaml](../../compose.legacy.yaml)
- [.env.example](../../.env.example)
- [Daily checklist](daily_checklist.md)
- [Portainer](portainer.md)
- [Portainer workflow](portainer_workflow.md)
- [Architecture overview](architecture_overview.md)
- [Stack topology](stack_topology.md)
- [Delivery](delivery.md)
- [Platform bootstrap doc](../architecture/platform-bootstrap.md)
- [Service map](../architecture/service-map.md)
- [Bootstrap status](platform_bootstrap_status.md)
- [Services](services.md)

## Service endpoints
- Odoo direct dev port: `http://localhost:8069`
- Nginx dev port: `http://localhost:8088`
- pgAdmin admin port: `http://localhost:8080`
- Obsidian GUI: `http://localhost:3000` and `https://localhost:3001`
- Portainer UI: `https://localhost:9443`

## Notes
- The architecture overview is the best first page when you want the whole stack in one view.
- `compose.yaml` is the base platform and should stay production-safe.
- `compose.admin.yaml` is where optional admin and knowledge services belong.
- Local backup flow is now testable with `pgBackRest` from the base stack.
- The custom `db`, `pgbackrest`, and `odoo` services can run from local builds or CI-published GHCR images.
- The staging layer now includes `mailpit` so restored copies cannot send real mail by default.
- Production offsite replication currently happens through wrapper scripts rather than a long-running backup service.
- The service ownership and boundaries live in the service map and should be updated whenever the stack changes.
- The Obsidian container is a browser-accessible desktop app, not the Windows desktop binary.
- Portainer manages the local Docker daemon through the socket mount in `compose.admin.yaml`.
- The Portainer note contains the operational checklist for container management.
- The vault root is the `docs/` directory, mounted into the container as `ObsidianVault`.
- If you change ports or service names, update this note, the home note, and the bootstrap status note together.
