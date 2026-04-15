# Service Map

This document explains what each service in the platform does, where it belongs, and how it is expected to behave across compose layers.

## Base compose services

### `db`

Purpose:

- primary PostgreSQL 16 database
- owns the live cluster state
- exposes archive hooks for `pgBackRest`

Important details:

- built from `postgres_image/Dockerfile`
- runs with `archive_mode=on`
- shares the PostgreSQL socket and data volumes with `pgbackrest`
- should never be publicly exposed

## `redis`

Purpose:

- platform-level cache and future queue primitive
- supports a more production-shaped platform even before custom queue workloads exist

Important details:

- runs in the internal Docker network only
- persists data in the `redis-data` volume
- should never be publicly exposed

## `pgbackrest`

Purpose:

- manages local PostgreSQL backup checks and full backups
- owns the backup repository volume

Important details:

- built from `pgbackrest/Dockerfile`
- uses shared PostgreSQL data and socket volumes
- currently validated for local `stanza-create`, `check`, and `full backup`
- offsite replication is still pending

## `odoo`

Purpose:

- main application runtime

Important details:

- built from `odoo/Dockerfile`
- uses `config/` and `addons/` from the repository
- persists filestore data in `odoo-web-data`
- is internal in production-like layouts, with `nginx` as the edge

## `nginx`

Purpose:

- reverse proxy and edge entrypoint

Important details:

- template lives at `nginx/conf.d/odoo.conf.template`
- serves dev through `8088`
- serves `80/443` in staging and production overrides
- carries websocket routing scaffold for Odoo

## Admin and knowledge layer services

These belong in `compose.admin.yaml`, not the production-safe base stack.

### `pgadmin`

Purpose:

- browser-based PostgreSQL administration UI

Important details:

- useful for inspection and emergency administration
- should stay optional and not be required by staging/prod runtime

### `obsidian`

Purpose:

- browser-accessible knowledge workspace backed by the repository `docs/` folder

Important details:

- treats `docs/` as the vault root
- helps keep technical docs and operational notes close to the code
- should remain optional and local/admin-oriented

## Compose layer responsibilities

- `compose.yaml`: production-safe platform base
- `compose.dev.yaml`: developer-facing ports and local workflow behavior
- `compose.admin.yaml`: optional admin and knowledge services
- `compose.staging.yaml`: production-like staging behavior
- `compose.prod.yaml`: production-like edge exposure and config
- `docker-compose.yml`: legacy compatibility entrypoint

## Persistent state

Current named volumes:

- `postgres-data`
- `postgres-run`
- `pgbackrest-repo`
- `redis-data`
- `odoo-web-data`
- `pgadmin-data`
- `obsidian-config`

Longer-term direction:

- move production-like state to external environment-specific paths under `/srv/odoo/<project>/<env>/`
