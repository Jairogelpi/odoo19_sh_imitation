# Daily Checklist

## Purpose
Quick operational reminder for the current local stack state.

## Current state
- Stack target: Docker Desktop with `compose.yaml`, `compose.dev.yaml`, and `compose.admin.yaml`.
- Running services: `db`, `redis`, `pgbackrest`, `odoo`, `nginx`, `pgadmin`, `obsidian`, `portainer`.
- Main URLs:
  - Odoo direct: `http://localhost:8069/web/login`
  - Odoo via Nginx: `http://localhost:8088/web/login`
  - pgAdmin: `http://localhost:8080`
  - Obsidian: `http://localhost:3000`
  - Portainer: `https://localhost:9443`

## Default credentials
- PostgreSQL: `odoo` / `change_me`
- Odoo master password: `change_me`
- pgAdmin: `admin@example.com` / `change_me`
- Obsidian: `obsidian` / `change_me`
- Portainer: first admin account is created on first launch

## Obsidian reminder
- The container opens to the launcher first.
- Open `/config/ObsidianVault` manually on first launch.
- That path maps to the repository `docs/` directory.
- The selection should persist in the `obsidian-config` volume.

## Portainer reminder
- Open `https://localhost:9443`.
- Expect a browser certificate warning on the first visit because the local HTTPS endpoint is self-signed.
- Create the first admin user during initial setup.
- Use the local Docker socket environment so Portainer can manage this stack.