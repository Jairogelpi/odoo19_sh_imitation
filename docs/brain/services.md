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

## Use this note when you need

- to remember which compose layer owns a service
- to see which services are optional versus core
- to navigate quickly to the authoritative service documentation
