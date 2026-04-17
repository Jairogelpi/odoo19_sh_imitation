# Lobby

## Purpose

This note is the Obsidian-side shortcut into the platform **lobby**: the single landing page that groups every admin UI of the stack.

## Quick model

- Image: `ghcr.io/gethomepage/homepage:latest`
- Compose layer: `compose.admin.yaml` (optional, never in the prod-safe base)
- URL: `http://localhost:8081`
- Config directory: `homepage/config/` at the repo root
- Reads `/var/run/docker.sock` read-only to show live container status
- Uses in-network HTTP monitors like `http://nginx/healthz` rather than host `localhost` ports
- Leaves `obsidian` and `pgbackrest` on Docker status only because they are not good anonymous HTTP probe targets

## Tiles it exposes

- **Plataforma**: Odoo (via Nginx), Odoo directo, Nginx
- **Operaciones**: Portainer, pgAdmin, pgBackRest (links to control-plane `/backups`)
- **Control plane**: Backups, Deploys, Docs (served by `control-plane` on port 8082)
- **Conocimiento**: Obsidian, Runbooks, Arquitectura
- **Documentación** (bookmarks): Brain, Arquitectura, Runbooks, Superpoderes, Schema

## Main references

- [Lobby runbook](../runbooks/lobby-homepage.md)
- [Runtime validation](../runbooks/runtime-validation.md)
- [Service map](../architecture/service-map.md)
- [Stack topology](stack_topology.md)
- [Services](services.md)
- [Portainer](portainer.md)

## Use this note when you need

- to remember which URL is the lobby and how to start it
- to see the full list of tiles that should appear on the dashboard
- to navigate into the runbook for configuration and troubleshooting

## Related notes

- [Odoo Brain](../00_Odoo_Brain.md)
- [Control Plane](control_plane.md)
- [Services](services.md)
- [Stack Topology](stack_topology.md)
- [Portainer](portainer.md)
- [Operations](operations.md)
