# Admin and Observability Tooling

## Goal

Document the optional admin-only and observability services that live in `compose.admin.yaml` but are not part of the production-safe base stack.

These services fall into three groups:

- internal MCP bridge services used by OpenClaw
- operator-facing browser tools
- internal metrics collection plus Grafana dashboards

Use this runbook together with:

- [Control plane](control-plane.md)
- [Hardened OpenClaw deployment](hardened-openclaw-deployment.md)
- [Lobby (Homepage)](lobby-homepage.md)
- [Local development](local-development.md)

## Start commands

Full base + admin layer:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d
```

Only the optional admin/observability services after the base stack is already running:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d control-plane dozzle code-server web-terminal grafana
```

## User-facing endpoints

- Control plane: `http://localhost:8082`
- Code Server: `http://localhost:8083`
- Dozzle: `http://localhost:8084`
- Web terminal: `http://localhost:8085`
- Grafana: `http://localhost:3002`

These endpoints are for local/admin access only. None of them should be exposed publicly without an authenticated reverse proxy in front.

## Internal MCP bridge services

These services are internal only. They do not publish host ports and are meant to be called by `control-plane` over `odoo_net`.

### `obsidian-mcp`

- Purpose: expose the `docs/` vault as MCP JSON-RPC tools.
- Internal endpoint: `http://obsidian-mcp:8090/mcp`
- Mount: `./docs` -> `/vault`
- Required auth: `OPENCLAW_OBSIDIAN_MCP_TOKEN`
- Verification:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-openclaw-connectors.ps1
```

### `memory-mcp`

- Purpose: persistent key/value memory service for OpenClaw workflows.
- Internal endpoint: `http://memory-mcp:8091/mcp`
- Persistent state: named volume `memory-mcp-data`
- Required auth: `OPENCLAW_MEMORY_MCP_TOKEN`

### `context7-mcp`

- Purpose: documentation query bridge over the repo `docs/` tree.
- Internal endpoint: `http://context7-mcp:8092/mcp`
- Mount: `./docs` -> `/docs`
- Required auth: `OPENCLAW_CONTEXT7_MCP_TOKEN`

### `cif-lookup-mcp`

- Purpose: Spanish company lookup/enrichment by CIF.
- Internal endpoint: `http://cif-lookup-mcp:8093/mcp`
- Required auth: `OPENCLAW_CIF_LOOKUP_MCP_TOKEN`
- Optional enrichment: `GOOGLE_MAPS_API_KEY`
- Related note: [OpenClaw CIF lookup](../brain/openclaw_cif_lookup.md)

## Operator-facing browser tools

### `control-plane`

- Purpose: operator console for backups, deploy state, docs browsing, and MCP gateway features.
- Host route: `http://localhost:8082`
- Mounts:
  - `/var/run/docker.sock` read-only
  - `./docs` -> `/app/docs`
  - `./addons_custom` -> `/workspace/addons_custom`
- Related runbook: [Control plane](control-plane.md)

### `dozzle`

- Purpose: lightweight live container log viewer.
- Host route: `http://localhost:8084`
- Access model: Docker socket read-only mount, no repo bind mount
- Risk note: convenient for local operations, but it still exposes container log visibility; keep it private

### `code-server`

- Purpose: browser IDE over selected workspace folders.
- Host route: `http://localhost:8083`
- Auth: `CODE_SERVER_PASSWORD`
- Persistent state: named volume `code-server-config`
- Mounted workspace slices:
  - `./addons`
  - `./config`
  - `./docs`
  - `./control-plane`
  - `./homepage`

### `web-terminal`

- Purpose: browser shell based on `ttyd` plus `docker-ce-cli`.
- Host route: `http://localhost:8085`
- Access model: Docker socket mounted read-only, no direct repo bind mount
- Important limitation: this shell is mainly useful for Docker inspection/control, not for editing the repository files directly
- Risk note: even with a read-only socket bind, Docker API access is operationally sensitive; treat it like an admin surface

## Metrics and dashboards

### `cadvisor`

- Purpose: per-container metrics exporter.
- Internal target: `cadvisor:8080`
- Used by: `prometheus`
- Host exposure: none

### `node-exporter`

- Purpose: host-level CPU, memory, filesystem, and kernel metrics exporter.
- Internal target: `node-exporter:9100`
- Used by: `prometheus`
- Host exposure: none

### `prometheus`

- Purpose: scrape and store metrics for the admin stack.
- Internal target: `http://prometheus:9090`
- Host exposure: none
- Persistent state: named volume `prometheus-data`
- Config source: [prometheus/prometheus.yml](../../prometheus/prometheus.yml)
- Current scrape targets:
  - `cadvisor:8080`
  - `node-exporter:9100`

### `grafana`

- Purpose: browser dashboards over Prometheus metrics.
- Host route: `http://localhost:3002`
- Auth:
  - `GRAFANA_ADMIN_USER`
  - `GRAFANA_ADMIN_PASSWORD`
- Persistent state: named volume `grafana-data`
- Provisioning:
  - Prometheus datasource at `http://prometheus:9090`
  - default dashboard provider under `grafana/provisioning/dashboards/`

## Environment variables

Shared admin/observability variables already tracked in `.env.example`:

- `OPENCLAW_OBSIDIAN_MCP_TOKEN`
- `OPENCLAW_MEMORY_MCP_TOKEN`
- `OPENCLAW_CONTEXT7_MCP_TOKEN`
- `OPENCLAW_CIF_LOOKUP_MCP_TOKEN`
- `CODE_SERVER_PASSWORD`
- `GRAFANA_ADMIN_USER`
- `GRAFANA_ADMIN_PASSWORD`
- `GOOGLE_MAPS_API_KEY`

## Verification

Browser-accessible services:

- open `http://localhost:8082` -> control plane renders
- open `http://localhost:8083` -> Code Server login appears
- open `http://localhost:8084` -> Dozzle renders
- open `http://localhost:8085` -> ttyd shell loads
- open `http://localhost:3002` -> Grafana login appears

Connector verification:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-openclaw-connectors.ps1
```

Compose-level verification:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml ps
```

Prometheus/Grafana sanity checks:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml logs --tail 50 prometheus grafana
```

## Troubleshooting

- `control-plane` works but MCP bridge actions fail: verify the matching `OPENCLAW_*_MCP_TOKEN` values exist in both `control-plane` and the target MCP service.
- `code-server` opens but rejects login: check `CODE_SERVER_PASSWORD` in the active env file and recreate the service.
- `web-terminal` loads but cannot see the repo: expected. It does not mount the workspace; use it for container/Docker operations only.
- Grafana loads with no data: confirm `prometheus` is running and that the provisioned datasource still points to `http://prometheus:9090`.
- Prometheus is up but has no targets: inspect [prometheus/prometheus.yml](../../prometheus/prometheus.yml) and verify `cadvisor` and `node-exporter` are connected to `odoo_net`.
- Dozzle or web-terminal should never be internet-facing as-is. If you need remote access, put them behind an authenticated reverse proxy or VPN.

## Related files

- [compose.admin.yaml](../../compose.admin.yaml)
- [control-plane/Dockerfile](../../control-plane/Dockerfile)
- [web-terminal/Dockerfile](../../web-terminal/Dockerfile)
- [prometheus/prometheus.yml](../../prometheus/prometheus.yml)
- [grafana/provisioning/datasources/prometheus.yml](../../grafana/provisioning/datasources/prometheus.yml)
