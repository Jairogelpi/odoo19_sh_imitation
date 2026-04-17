# Environments and Promotions

## Environment model

This platform is designed around one Docker host per environment.

Target environments:

- `dev`
- `staging`
- `prod`

These are runtime targets, not just branch names and not just database names.

## Four different layers

The easiest way to understand this platform is to separate four layers that often get mixed together:

### Git

Git stores code, compose files, docs, and addon trees.

That includes:

- `compose.yaml` and environment overrides
- `config/odoo*.conf`
- `addons/`
- `addons_custom/`
- scripts, docs, and CI/CD workflow files

Git does not store live business state.

### Docker runtime

Docker turns the repository into running services.

Examples:

- `db`
- `odoo`
- `nginx`
- `redis`
- `pgbackrest`

The compose files decide which services run in each environment, but the containers themselves are not the source of truth. They are the runtime projection of the repository plus environment files plus named volumes.

### Live state

Docker named volumes store live runtime state.

Important state boundaries in this project:

- `postgres-data` -> PostgreSQL data directory
- `odoo-web-data` -> Odoo filestore and web data
- `pgbackrest-repo` -> backup repository used by pgBackRest

This is where the real ERP state lives:

- databases
- installed module state
- users
- companies
- products
- invoices
- attachments and filestore content

### Backups

Backups are copies of the live state, not copies of Git.

In this project that means:

- PostgreSQL backups through `pgbackrest`
- filestore backups through the backup scripts
- optional offsite replication of those backup artifacts

## Current reality in this workspace

Right now this machine is running a local development-shaped environment:

- `compose.yaml` + `compose.dev.yaml` for the base runtime
- `compose.admin.yaml` for optional admin and knowledge services

The current local database in this workspace is `essensi`.

That means:

- your code and addons live in the repository
- your live local ERP data lives in PostgreSQL and Odoo volumes
- your current Odoo app runtime is local dev, even if your Git branch changes

Changing branch does not automatically create a new environment. The environment is defined by which compose files and env files you start.

## Compose layer mapping

- `compose.yaml` + `compose.dev.yaml` -> local development
- `compose.yaml` + `compose.staging.yaml` -> staging
- `compose.yaml` + `compose.prod.yaml` -> production
- `compose.admin.yaml` -> optional admin and knowledge services where appropriate

## Database and filestore boundaries

Each environment should own its own state:

- its own PostgreSQL database set
- its own Odoo filestore
- its own environment file
- its own named volumes or host-mounted persistent data

In practice:

- local dev currently has `essensi`
- staging should expose only databases matching `staging_*`
- production should expose only databases matching `prod_*`

That last part comes from the environment-specific `dbfilter` settings in the tracked Odoo config files.

## Branch model

- `develop` -> development deployment target
- `staging` -> staging deployment target
- `main` -> production deployment target
- `feature/*` -> short-lived feature branches

Important nuance:

- locally, you can be on any branch and still run the dev stack
- remotely, the deployment model maps branches to environments

## Promotion model

Recommended path:

1. work on `feature/*`
2. merge into `develop`
3. validate in `dev`
4. merge into `staging`
5. validate in `staging`
6. merge into `main`
7. deploy to `prod`

## What travels through Git

The following things are promoted between environments through Git:

- compose files
- Odoo config files
- documentation
- scripts
- modules in `addons/`
- modules in `addons_custom/`

If `ss_enterprise_theme` exists in `addons_custom/`, that means the code is available to every environment that deploys the commit containing that folder.

## What does not travel through Git

The following things do not move automatically just because you commit code:

- PostgreSQL rows
- Odoo users
- installed module state
- server registrations inside pgAdmin
- dashboards and saved admin UI state
- filestore content

A module can exist in Git and still be uninstalled in a database.

That is normal.

Example:

- `addons_custom/ss_enterprise_theme` can exist in the repository
- Odoo can detect it on disk
- but each database still decides independently whether it is installed

## How backups fit in

Backups protect the live state layer, not the Git layer.

Use Git to recover:

- code
- config
- addons
- docs

Use backups to recover:

- PostgreSQL databases
- Odoo filestore
- production or staging data state

That is why both Git and backups are required. One does not replace the other.

## Runtime expectations by environment

### Development

- easiest local startup
- direct Odoo port exposed
- Nginx available for parity checks
- admin and knowledge layer allowed

### Staging

- production-like edge exposure
- production-like Odoo config
- must become a neutralized copy of production
- uses `Mailpit` as the default SMTP sink after restore neutralization
- should not depend on admin services to operate

### Production

- production-like edge exposure
- no optional admin/knowledge services in the critical path
- strict secrets and backup discipline
- offsite backup replication should be part of normal production operations

## Mental model to keep

Use this rule of thumb:

- Git defines what the platform should run
- Docker runs it
- PostgreSQL and the Odoo filestore hold what the business is actually doing
- backups protect that live business state

If something is confusing, ask first: "Is this code, runtime, live state, or backup state?"

## Remaining gaps

- first-time server bootstrap automation
- automated restore drills from offsite copies
- data anonymization beyond operational neutralization
