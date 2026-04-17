# Control Plane

## Purpose

Obsidian-side shortcut into the **operator console** that sits next to the lobby: a small FastAPI UI at `http://localhost:8082` that groups the three actions the operator performs most — restore a backup, see GitHub deploy state, browse the docs vault — with enough safety checks that it can live inside the admin stack without becoming a footgun.

This is a pragmatic, current-stack service. The multi-tenant control plane designed in [Future Control Plane](future_control_plane.md) is a separate, future shape.

## Quick model

- Image: built from `./control-plane` (Dockerfile: `python:3.12-slim` + `docker-ce-cli` + `uvicorn`)
- Compose layer: `compose.admin.yaml` (optional, never in the prod-safe base)
- URL: `http://localhost:8082`
- Code directory: `control-plane/app/` at the repo root
- Reads `/var/run/docker.sock` read-only to issue `docker exec` against sibling containers
- Bind-mounts `./docs` read-only so the docs browser sees the exact vault
- No built-in auth — localhost only

## Surfaces it exposes

- **Backups** (`/backups`) — live table from `pgbackrest info --output=json`, with a "Recuperar" modal that requires a written confirmation equal to the chosen target environment.
- **Deploys** (`/deploys`) — live read from the GitHub REST API for `Jairogelpi/odoo19_sh_imitation`: workflow runs, branches, open PRs.
- **Docs** (`/docs`) — renders any markdown under `docs/` with a folder tree sidebar; the lobby bookmarks deep-link into `runbooks`, `architecture`, `superpowers`, `odoo19_schema`, and the brain entry `00_Odoo_Brain.md`.

## Restore rule

- Only `dev` restores execute from here **and** only when `STACK_ENV=dev`.
- `staging` and `prod` render a ready-to-paste SSH recipe instead of running anything.
- Confirmation string must literally equal the dropdown value (`dev|staging|prod`).

## Main references

- [Control plane runbook](../runbooks/control-plane.md)
- [Backup and restore runbook](../runbooks/backup-and-restore.md)
- [Lobby runbook](../runbooks/lobby-homepage.md)
- [Deployment over SSH](../runbooks/deployment-over-ssh.md)
- [CI/CD scaffold](../runbooks/ci-cd-scaffold.md)
- [Service map](../architecture/service-map.md)
- [Stack topology](stack_topology.md)
- [Lobby brain note](lobby.md)
- [Services](services.md)
- [Future Control Plane](future_control_plane.md)

## Use this note when you need

- to remember which URL is the control plane and what each tab does
- to recall the restore contract (which env runs here, which only prints a recipe)
- to find the runbook for configuration, env vars, and troubleshooting
- to separate the current pragmatic console from the future multi-tenant control plane

## Related notes

- [OpenClaw](openclaw.md)
- [Odoo Brain](../00_Odoo_Brain.md)
- [Lobby](lobby.md)
- [Services](services.md)
- [Stack Topology](stack_topology.md)
- [Operations](operations.md)
- [Delivery](delivery.md)
- [Future Control Plane](future_control_plane.md)
