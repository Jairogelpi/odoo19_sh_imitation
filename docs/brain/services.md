# Services

## Purpose

This note is the Obsidian-side shortcut into the platform service topology.

## Main references

- [Service map](../architecture/service-map.md)
- [Platform bootstrap](../architecture/platform-bootstrap.md)
- [Operations](operations.md)

## Quick service mental model

- `db`: PostgreSQL primary state
- `redis`: cache and future queue primitive
- `pgbackrest`: database backup/check utility
- `odoo`: main app runtime
- `nginx`: reverse proxy
- `pgadmin`: optional admin UI
- `obsidian`: optional knowledge layer
- `mailpit`: staging-only SMTP sink

The custom `db`, `pgbackrest`, and `odoo` services now support both local builds and GHCR-published image overrides.
`mailpit` exists only to keep restored staging environments safe.

## Use this note when you need

- to remember which compose layer owns a service
- to see which services are optional versus core
- to navigate quickly to the authoritative service documentation
