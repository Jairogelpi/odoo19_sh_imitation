# Services

## Purpose

This note is the Obsidian-side shortcut into the platform service topology.

## Main references

- [Service map](../architecture/service-map.md)
- [Platform bootstrap](../architecture/platform-bootstrap.md)
- [Operations](operations.md)
- [Portainer](portainer.md)

## Quick service mental model

- `db`: PostgreSQL primary state, no public port in the base stack, default user `odoo`, default password `change_me`
- `redis`: cache and future queue primitive, no public port in the base stack
- `pgbackrest`: database backup/check utility, no public port in the base stack
- `odoo`: main app runtime, direct dev access on `http://localhost:8069/web/login`
- `nginx`: reverse proxy, direct dev access on `http://localhost:8088/web/login`
- `pgadmin`: optional admin UI, direct access on `http://localhost:8080`, default login `admin@example.com` / `change_me`
- `obsidian`: optional knowledge layer, direct access on `http://localhost:3000` and `http://localhost:3001`, default login `obsidian` / `change_me`
- `portainer`: optional container-management UI, direct access on `https://localhost:9443`, first admin user created on first launch
- `mailpit`: staging-only SMTP sink, UI on `127.0.0.1:8025` by default in staging

The custom `db`, `pgbackrest`, and `odoo` services now support both local builds and GHCR-published image overrides.
`mailpit` exists only to keep restored staging environments safe.

## Use this note when you need

- to remember which compose layer owns a service
- to see which services are optional versus core
- to navigate quickly to the authoritative service documentation
