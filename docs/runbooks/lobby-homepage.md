# Lobby (Homepage) Runbook

## Goal

Single landing page that links to every admin UI of the platform — Odoo, Nginx, pgAdmin, Portainer, pgBackRest, Obsidian — with live container status pulled from the Docker socket.

The lobby is implemented with [`gethomepage/homepage`](https://gethomepage.dev/), a static YAML-driven dashboard. It lives in `compose.admin.yaml` and is therefore optional — the production base stack never starts it.

## Service definition

- Image: `ghcr.io/gethomepage/homepage:latest`
- Compose layer: `compose.admin.yaml`
- Network: `odoo_net`
- Host port: `8081` → container `3000`
- User: `0:0` (must be root so it can read the root-owned Docker socket on Docker Desktop; without this you get `EACCES /var/run/docker.sock` and every tile reports "Unknown")
- Volumes:
  - `./homepage/config` → `/app/config` (YAML configuration)
  - `/var/run/docker.sock` → read-only, used to show container status / CPU / RAM

## URLs

- Lobby entry point: `http://localhost:8081`

From the lobby the tiles link to the standard admin ports already used by the stack:

- Odoo via Nginx: `http://localhost:8088`
- Odoo direct: `http://localhost:8069`
- Portainer: `https://localhost:9443`
- pgAdmin: `http://localhost:8080`
- Obsidian: `http://localhost:3000`

## Configuration files

All config lives under `homepage/config/` in the repo.

- `settings.yaml`: title, theme, language, layout (3 rows: Plataforma, Operaciones, Conocimiento).
- `services.yaml`: tiles for each platform service, each one linked to a Docker container for live status via `my-docker` / `container: odoo19-*-1`.
- `widgets.yaml`: top widgets (host CPU/RAM/disk, search, date/time).
- `bookmarks.yaml`: external doc links (Odoo 19, pgBackRest, Portainer).
- `docker.yaml`: declares the `my-docker` socket source at `/var/run/docker.sock`.
- `kubernetes.yaml`: empty placeholder to silence the homepage warning when no k8s is present.

## Environment variables

Defined in `.env.example` and `.env.dev.example`:

- `HOMEPAGE_ALLOWED_HOSTS`: comma-separated hostnames allowed to serve the dashboard. Default: `localhost:8081,127.0.0.1:8081`. This is mandatory when accessing homepage from anything other than the default localhost.

The container also reads `PUID`, `PGID`, and `TZ`, which are already shared with Obsidian in the admin layer.

## Start / stop

Bring up the full dev + admin stack:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d
```

Bring up only the lobby (assumes the base stack is already running):

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d homepage
```

Stop the lobby without tearing down the rest:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml stop homepage
```

## Verification

Automated:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-admin-stack.ps1
```

This probes `http://localhost:8081` and expects HTTP 200.

Manual spot checks:

- open `http://localhost:8081` — lobby renders with tiles for each service
- edge and web tiles show a green dot only when their `siteMonitor` target answers from inside the Docker network
- auth-gated or CLI-only tiles rely on Docker container status instead of an HTTP site monitor
- `CPU` / `MEM` counters visible when you hover/click a tile with Docker integration
- full local validation evidence is tracked in `docs/runbooks/runtime-validation.md`

## Maintenance

When a service is added, renamed, or gets a new port:

1. Edit `homepage/config/services.yaml` — update or add the tile (`href`, `container`, `description`).
2. If the Docker project name is not the default `odoo19`, update the `container:` field accordingly — it must match the real container name (`docker ps` to verify).
3. Restart the lobby: `docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml restart homepage`.

site monitors must use container-reachable addresses:

- use Docker service names and container ports like `http://nginx/healthz`, `http://pgadmin:80`, or `http://portainer:9000`
- do not point `siteMonitor` at `localhost:<hostPort>` because inside the homepage container `localhost` is homepage itself
- do not use `siteMonitor` for services that require login on every request or do not expose HTTP at all; keep Docker status only for cases like Obsidian and pgBackRest

When exposing the lobby outside `localhost` (e.g. via a tunnel, VPN, or reverse proxy):

- Append the new hostname to `HOMEPAGE_ALLOWED_HOSTS` in the active `.env` file.
- Restart the lobby to pick up the new env value.
- Never expose the lobby publicly without a reverse proxy + authentication in front; the dashboard itself has no login.

## Troubleshooting

- Lobby returns `Invalid Host header`: add the hostname/port you are using to `HOMEPAGE_ALLOWED_HOSTS`.
- All container dots show "Unknown" with `EACCES /var/run/docker.sock` in the logs: the homepage container is not running as root. Keep `user: "0:0"` in `compose.admin.yaml`; Docker Desktop for Windows mounts the socket as `root:root 660`, so the default `node` user cannot read it.
- All siteMonitor dots are red with `ECONNREFUSED` in the logs: the `siteMonitor:` URL is pointing at `localhost:<hostPort>`. Inside the homepage container `localhost` is the container itself, not the host. Use the in-network Docker service name and container port (for example `http://nginx/healthz`, `http://pgadmin:80`, or `http://portainer:9000`), not `http://localhost:8088`.
- The Odoo or Nginx tile shows a failing site monitor after a proxy tweak: verify `http://nginx/healthz` from inside the homepage container before blaming Odoo. This route is intentionally static so it stays green even when the Odoo login path redirects or is temporarily warming up.
- Obsidian shows container status but no HTTP monitor: expected. Its web UI is auth-gated and `siteMonitor` only supports anonymous `HEAD`/`GET` probes.
- pgBackRest shows container status but no HTTP monitor: expected. It is a CLI backup service and does not expose a web endpoint to probe.
- Widgets at the top show errors: likely the container cannot reach the host. `resources` widget uses the container's own namespace — acceptable if the numbers look low.
- Page looks unstyled after edit: syntax error in one of the YAML files. Check the container logs: `docker compose -f compose.admin.yaml logs homepage`.

## Related notes

- [Service Map](../architecture/service-map.md)
- [Stack Topology](../brain/stack_topology.md)
- [Services](../brain/services.md)
- [Lobby brain note](../brain/lobby.md)
- [Local development runbook](local-development.md)
- [Runtime validation](runtime-validation.md)
