# Service Map

This document explains what each service in the platform does, where it belongs, and how it is expected to behave across compose layers.

## Network topology

All services in the stack attach to the same user-defined bridge network, `odoo_net`.

Why this matters:

- services can resolve each other by compose service name
- the database, cache, backup, and application services stay private to the Docker network
- only the ports explicitly published in compose reach the host

Exposure model:

- `db`: no public port; private only
- `redis`: no public port; private only
- `pgbackrest`: no public port; private only
- `odoo`: private inside the Docker network, with direct host access only in dev through `8069`
- `nginx`: edge entrypoint, published in dev through `8088` and in staging or prod through `80/443`
- `pgadmin`: optional admin UI, published on `8080` only for local/admin access, not intended for public exposure
- `obsidian`: optional knowledge workspace, published on `3000` and `3001` only for local/admin access
- `portainer`: optional container manager, published on `9443` only for local/admin access
- `mailpit`: staging-only sink, published only on host loopback at `127.0.0.1:${STAGING_MAILPIT_UI_PORT:-8025}`

Practical rule:

- if a service is not published on a host port, it is meant to be reached from another container on `odoo_net` or through a published edge service

## Delivery and environment flow

The platform is intended to move through Git-backed environments rather than being edited only in a UI.

Recommended environment model:

- `feature/*`: local development branches
- `develop`: integration for day-to-day changes
- `staging`: neutralized preproduction validation
- `main`: production release line

Recommended deployment model:

- GitHub Actions validates the stack and publishes images
- remote hosts pull immutable GHCR tags
- environment files provide runtime-specific configuration
- Portainer is used for inspection and operations, not as the only delivery mechanism

Delivery rule:

- if a change matters beyond the current container session, it should be expressed in Git, compose, or the environment files as well as in Portainer

## Persistence model

Named volumes are the state boundary for the stack.

Current named volumes:

- `postgres-data`: live database data
- `postgres-run`: PostgreSQL runtime socket and process state
- `pgbackrest-repo`: backup repository and archive state
- `redis-data`: Redis persistence
- `odoo-web-data`: Odoo filestore and runtime data
- `pgadmin-data`: pgAdmin settings and state
- `obsidian-config`: Obsidian desktop state and vault selection persistence
- `portainer-data`: Portainer admin account and settings persistence

Rule of thumb:

- if a service owns data that should survive a restart, it should be backed by a named volume or an explicit external mount
- if a service is only a control plane or a transient helper, it should not become the only place where important state lives

## Base compose services

### `db`

Purpose:

- primary PostgreSQL 16 database
- owns the live cluster state
- exposes archive hooks for `pgBackRest`

Important details:

- built from `postgres_image/Dockerfile`
- can run from a local build or a GHCR-published image override
- runs with `archive_mode=on`
- shares the PostgreSQL socket and data volumes with `pgbackrest`
- should never be publicly exposed
- attaches to `odoo_net` so `odoo`, `pgbackrest`, and `pgadmin` can reach it by service name

### `redis`

Purpose:

- platform-level cache and queue auxiliary service
- supports future workers, caching, and rate-limiting patterns without baking them into the application image

Important details:

- runs in the internal Docker network only
- persists data in the `redis-data` volume
- should never be publicly exposed
- attaches to `odoo_net` so Odoo can use it as a cache/queue primitive

### `pgbackrest`

Purpose:

- manages local PostgreSQL backup checks and full backups
- owns the backup repository volume

Important details:

- built from `pgbackrest/Dockerfile`
- can run from a local build or a GHCR-published image override
- uses shared PostgreSQL data and socket volumes
- currently validated for local `stanza-create`, `check`, and `full backup`
- offsite replication is still pending
- attaches to `odoo_net` so it can speak to `db` and use the shared socket and data volumes

### `odoo`

Purpose:

- main application runtime

Important details:

- built from `odoo/Dockerfile`
- can run from a local build or a GHCR-published image override
- uses `config/` and `addons/` from the repository
- persists filestore data in `odoo-web-data`
- is internal in production-like layouts, with `nginx` as the edge
- attaches to `odoo_net` so it can reach `db` and `redis` without exposing those services to the host

### `nginx`

Purpose:

- reverse proxy and edge entrypoint

Important details:

- template lives at `nginx/conf.d/odoo.conf.template`
- serves dev through `8088`
- serves `80/443` in staging and production overrides
- carries websocket routing scaffold for Odoo
- attaches to `odoo_net` so it can proxy to `odoo` by service name

## Admin and knowledge layer services

These belong in `compose.admin.yaml`, not the production-safe base stack.

### `pgadmin`

Purpose:

- browser-based PostgreSQL administration UI

Important details:

- useful for inspection and emergency administration
- should stay optional and not be required by staging/prod runtime
- should be treated as local-admin-only access, not a public endpoint
- attaches to `odoo_net` so it can connect to `db` by service name

### `portainer`

Purpose:

- container management UI for the local Docker daemon

Important details:

- belongs in `compose.admin.yaml`
- uses the Docker socket to inspect and manage containers
- persists its own settings in the `portainer-data` volume
- should remain optional and not be required by staging/prod runtime
- attaches to `odoo_net` only for consistency with the compose stack; its management capability comes from the Docker socket, not from the network itself

### `obsidian`

Purpose:

- browser-accessible knowledge workspace backed by the repository `docs/` folder

Important details:

- treats `docs/` as the vault root
- helps keep technical docs and operational notes close to the code
- should remain optional and local/admin-oriented
- should not be treated as part of the core runtime
- attaches to `odoo_net` so it is reachable on the same compose network as the other admin tools

## Staging-only support service

### `mailpit`

Purpose:

- staging SMTP sink after restore neutralization
- safe inspection point for messages that must never leave staging

Important details:

- belongs in `compose.staging.yaml`
- SMTP stays internal on `mailpit:1025`
- UI is published only on loopback through `127.0.0.1:${STAGING_MAILPIT_UI_PORT:-8025}`
- should be accessed through SSH tunneling, not public exposure
- attaches to `odoo_net` so the restored Odoo environment can point mail delivery to it by service name

## Compose layer responsibilities

- `compose.yaml`: production-safe platform base
- `compose.dev.yaml`: developer-facing ports and local workflow behavior
- `compose.admin.yaml`: optional admin and knowledge services
- `compose.staging.yaml`: production-like staging behavior
- `compose.prod.yaml`: production-like edge exposure and config
- `docker-compose.yml`: legacy compatibility entrypoint

## How services are used together

- `db` stores the live PostgreSQL data and is reached by `odoo`, `pgbackrest`, and `pgadmin`
- `redis` is the internal cache/queue support service for Odoo
- `pgbackrest` validates backups, creates backups, and reads the shared PostgreSQL volumes
- `odoo` is the main ERP runtime and consumes the database and cache services
- `nginx` is the edge gateway for Odoo, especially in staging and production-like layouts
- `pgadmin` is for database inspection and emergency administration
- `obsidian` is for local documentation and operational notes in the `docs/` vault
- `portainer` is for container lifecycle management, inspection, and log access
- `mailpit` is for safe staging email handling after restore neutralization

Rule of thumb:

- use the browser UIs for inspection and simple lifecycle tasks
- use the compose files and scripts as the source of truth for configuration and repeatable deployment
- use the service name, not `localhost`, when one container needs to reach another container
- use GitHub Actions and GHCR for delivery and immutable image promotion

## Related notes

- [Odoo Brain](../00_Odoo_Brain.md)
- [Platform](../brain/platform.md)
- [Platform Bootstrap Status](../brain/platform_bootstrap_status.md)
- [Delivery](../brain/delivery.md)
- [Stack Topology](../brain/stack_topology.md)
- [Services](../brain/services.md)
- [Portainer](../brain/portainer.md)
- [Operations](../brain/operations.md)
