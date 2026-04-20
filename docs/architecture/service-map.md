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
- `obsidian-mcp`: no public port; private only
- `memory-mcp`: no public port; private only
- `context7-mcp`: no public port; private only
- `cif-lookup-mcp`: no public port; private only
- `odoo`: private inside the Docker network, with direct host access only in dev through `8069`
- `nginx`: edge entrypoint, published in dev through `8088` and in staging or prod through `80/443`
- `pgadmin`: optional admin UI, published on `8080` only for local/admin access, not intended for public exposure
- `obsidian`: optional knowledge workspace, published on `3000` and `3001` only for local/admin access
- `portainer`: optional container manager, published on `9443` only for local/admin access
- `homepage`: optional lobby dashboard, published on `8081` only for local/admin access
- `control-plane`: optional operator console (backups restore, GitHub deploys, docs browser), published on `8082` only for local/admin access
- `code-server`: optional browser IDE, published on `8083` only for local/admin access
- `dozzle`: optional live log viewer, published on `8084` only for local/admin access
- `web-terminal`: optional browser shell, published on `8085` only for local/admin access
- `cadvisor`: no public port; private only
- `node-exporter`: no public port; private only
- `prometheus`: no public port; private only
- `grafana`: optional dashboard UI, published on `3002` only for local/admin access
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
- `memory-mcp-data`: memory MCP JSON store
- `portainer-data`: Portainer admin account and settings persistence
- `code-server-config`: code-server user profile and extensions
- `prometheus-data`: Prometheus TSDB
- `grafana-data`: Grafana users, preferences, and dashboard state

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
- now auto-bootstraps the local stanza during the first archive push and is still validated for manual `stanza-create`, `check`, and `full backup`
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

- templates live at `nginx/templates/`
- startup selector lives at `nginx/scripts/configure-template.sh`
- exposes a static `/healthz` route for in-network monitoring by Homepage
- serves dev through `8088`
- serves `80/443` in staging and production overrides, with HTTP redirected to HTTPS once origin certs are mounted
- carries websocket routing scaffold for Odoo
- attaches to `odoo_net` so it can proxy to `odoo` by service name

## Admin and knowledge layer services

These belong in `compose.admin.yaml`, not the production-safe base stack.

### `obsidian-mcp`

Purpose:

- exposes docs-vault tools over MCP JSON-RPC for OpenClaw and the control-plane gateway

Important details:

- mounts `./docs` into `/vault`
- uses mandatory token auth through `OPENCLAW_OBSIDIAN_MCP_TOKEN`
- stays internal to `odoo_net`; no host port is published

### `memory-mcp`

Purpose:

- lightweight persistent memory service for OpenClaw workflows

Important details:

- persists state in the `memory-mcp-data` named volume
- uses mandatory token auth through `OPENCLAW_MEMORY_MCP_TOKEN`
- stays internal to `odoo_net`; no host port is published

### `context7-mcp`

Purpose:

- repository-backed documentation query service used by the OpenClaw bridge

Important details:

- mounts `./docs` into `/docs`
- uses mandatory token auth through `OPENCLAW_CONTEXT7_MCP_TOKEN`
- stays internal to `odoo_net`; no host port is published

### `cif-lookup-mcp`

Purpose:

- CIF/company enrichment service for OpenClaw CRM workflows

Important details:

- uses mandatory token auth through `OPENCLAW_CIF_LOOKUP_MCP_TOKEN`
- can optionally enrich with `GOOGLE_MAPS_API_KEY`
- stays internal to `odoo_net`; no host port is published

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
- is auth-gated, so Homepage should rely on Docker status rather than an HTTP site monitor
- attaches to `odoo_net` so it is reachable on the same compose network as the other admin tools

### `homepage`

Purpose:

- single lobby/landing page that links to every admin UI of the stack
- shows live container status by reading the host Docker socket in read-only mode

Important details:

- image `ghcr.io/gethomepage/homepage:latest`
- published on `8081` only for local/admin access
- configuration lives in `homepage/config/` and is bind-mounted into the container
- mounts `/var/run/docker.sock` read-only to drive the live status dots and CPU/RAM widgets
- uses container-reachable site monitors such as `http://nginx/healthz`, `http://odoo:8069/web/login`, `http://pgadmin:80`, and `http://portainer:9000`
- intentionally avoids `siteMonitor` for `obsidian` and `pgbackrest` because one is auth-gated and the other is CLI-only
- respects `HOMEPAGE_ALLOWED_HOSTS` — must be extended if the lobby is exposed beyond `localhost`
- has no built-in authentication; never expose publicly without a reverse proxy and auth in front
- attaches to `odoo_net` for consistency with the rest of the admin tools

### `control-plane`

Purpose:

- operator console for backups, deploy visibility, docs browsing, and OpenClaw gateway features

Important details:

- built from `control-plane/Dockerfile`
- published on `8082` for local/admin access
- mounts the Docker socket read-only plus `./docs` and `./addons_custom`
- depends on the internal MCP bridge services when the admin layer is up

### `dozzle`

Purpose:

- browser log viewer for Docker containers

Important details:

- published on `8084`
- reads the Docker socket in read-only mode
- has no built-in auth in this stack and must stay local/admin-only

### `code-server`

Purpose:

- browser IDE for selected workspace folders

Important details:

- published on `8083`
- protected only by `CODE_SERVER_PASSWORD`
- persists user/editor state in `code-server-config`
- mounts selected repo folders rather than the entire checkout

### `web-terminal`

Purpose:

- browser shell for Docker and container operations

Important details:

- built from `web-terminal/Dockerfile`
- published on `8085`
- ships `docker-ce-cli` plus `ttyd`
- mounts the Docker socket read-only but does not mount the repo workspace itself
- should be treated as an operationally sensitive admin surface

### `cadvisor`

Purpose:

- container metrics exporter for Prometheus

Important details:

- stays internal on `odoo_net`
- reads host/container runtime paths
- is consumed by Prometheus, not by browsers directly

### `node-exporter`

Purpose:

- host metrics exporter for Prometheus

Important details:

- stays internal on `odoo_net`
- exposes host metrics to Prometheus without publishing a host port

### `prometheus`

Purpose:

- metrics storage and scrape engine for the optional observability stack

Important details:

- uses `prometheus/prometheus.yml`
- scrapes `cadvisor:8080` and `node-exporter:9100`
- persists data in the `prometheus-data` volume
- stays internal to `odoo_net`; no host port is published

### `grafana`

Purpose:

- browser dashboards over Prometheus metrics

Important details:

- published on `3002`
- uses `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD`
- persists state in the `grafana-data` volume
- provisions its Prometheus datasource from `grafana/provisioning/datasources/prometheus.yml`

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
- `compose.legacy.yaml`: legacy compatibility entrypoint kept on a non-default filename

## How services are used together

- `db` stores the live PostgreSQL data and is reached by `odoo`, `pgbackrest`, and `pgadmin`
- `redis` is the internal cache/queue support service for Odoo
- `pgbackrest` validates backups, creates backups, and reads the shared PostgreSQL volumes
- `obsidian-mcp`, `memory-mcp`, `context7-mcp`, and `cif-lookup-mcp` are the internal bridge services behind the control-plane/OpenClaw integration
- `odoo` is the main ERP runtime and consumes the database and cache services
- `nginx` is the edge gateway for Odoo, especially in staging and production-like layouts
- `pgadmin` is for database inspection and emergency administration
- `obsidian` is for local documentation and operational notes in the `docs/` vault
- `portainer` is for container lifecycle management, inspection, and log access
- `homepage` is the lobby dashboard that links to every admin UI and shows live container status
- `control-plane` is the operator console and MCP gateway surface
- `code-server`, `dozzle`, and `web-terminal` are optional operator convenience tools
- `cadvisor` and `node-exporter` feed metrics to `prometheus`
- `grafana` is the browser entrypoint for those metrics dashboards
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
- [Lobby](../brain/lobby.md)
- [Operations](../brain/operations.md)
- [Admin and observability tooling](../runbooks/admin-observability-tooling.md)
