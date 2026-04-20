# Services

## Purpose

This note is the Obsidian-side shortcut into the platform service topology.

## Main references

- [Service map](../architecture/service-map.md)
- [Platform bootstrap](../architecture/platform-bootstrap.md)
- [Operations](operations.md)
- [Portainer](portainer.md)
- [Lobby](lobby.md)
- [Control Plane](control_plane.md)
- [Admin and observability tooling](../runbooks/admin-observability-tooling.md)
- [Vault token operations](../runbooks/vault-token-operations.md)

## Quick service mental model

- `db`: PostgreSQL primary state, no public port in the base stack, default user `odoo`, default password `change_me`
- `redis`: cache and future queue primitive, no public port in the base stack
- `pgbackrest`: database backup/check utility, no public port in the base stack
- `odoo`: main app runtime, direct dev access on `http://localhost:8069/web/login`
- `nginx`: reverse proxy, direct dev access on `http://localhost:8088/web/login`
- `pgadmin`: optional admin UI, direct access on `http://localhost:8080`, default login `admin@example.com` / `change_me`
- `obsidian`: optional knowledge layer, direct access on `http://localhost:3000` and `http://localhost:3001`, default login `obsidian` / `change_me`
- `portainer`: optional container-management UI, direct access on `https://localhost:9443`, first admin user created on first launch
- `homepage`: optional lobby dashboard, direct access on `http://localhost:8081`, links to every admin UI and shows live container status from the Docker socket
- `control-plane`: optional operator console, direct access on `http://localhost:8082`, backups restore UI, GitHub deploys, docs browser
- `obsidian-mcp`, `memory-mcp`, `context7-mcp`, `cif-lookup-mcp`: internal-only MCP bridge services behind OpenClaw/control-plane
- `code-server`: optional browser IDE on `http://localhost:8083`, password-protected by `CODE_SERVER_PASSWORD`
- `dozzle`: optional browser log viewer on `http://localhost:8084`
- `web-terminal`: optional browser shell on `http://localhost:8085`
- `cadvisor`, `node-exporter`, `prometheus`: internal-only metrics pipeline for the admin stack
- `grafana`: optional metrics dashboard UI on `http://localhost:3002`
- `mailpit`: staging-only SMTP sink, UI on `127.0.0.1:8025` by default in staging
- `certbot`: optional SSL sidecar for auto Let's Encrypt provisioning, uses `compose.ssl.yaml` overlay
- `vault`: optional self-hosted secrets sidecar on `http://localhost:8200` when `compose.vault.yaml` is used; see [Vault token operations](../runbooks/vault-token-operations.md)

The custom `db`, `pgbackrest`, and `odoo` services now support both local builds and GHCR-published image overrides.
`mailpit` exists only to keep restored staging environments safe.
The Homepage lobby uses internal monitor targets, not host `localhost` ports.

## Use this note when you need

- to remember which compose layer owns a service
- to see which services are optional versus core
- to navigate quickly to the authoritative service documentation
