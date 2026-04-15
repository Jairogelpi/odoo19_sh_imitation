# Odoo 19 Self-Hosted Platform Design

Date: 2026-04-15
Status: Approved for planning
Scope: Single Odoo project, professional self-hosted platform, one Docker host per environment

## 1. Objective

Build a replicable Odoo 19 platform that covers the operational capabilities that matter most in Odoo.sh:

- production, staging, and development environments
- Git-driven delivery flow
- reproducible Docker-based deployment
- serious backups and restore
- secure reverse proxy and HTTPS
- operational guardrails for staging
- clean separation between code, config, and persistent state

This design is intentionally not trying to clone the full Odoo.sh product UI. The goal is to replicate the useful operational capabilities, not its internal control panel.

## 2. Current Repository Baseline

Current repository state on 2026-04-15:

- basic local `docker-compose.yml` with `odoo`, `postgres`, and `pgAdmin`
- no `nginx`
- no `redis`
- no `pgBackRest`
- no CI/CD
- no multi-environment structure
- no `.gitignore`
- credentials committed in plain text in:
  - `docker-compose.yml`
  - `config/odoo.conf`
- runtime PostgreSQL data stored inside the repository under `postgres/`

This is a valid local sandbox, but not yet a platform template.

## 3. Final Design Decisions

The following decisions were explicitly settled during design:

- project model: single Odoo project
- environment model: one Docker host per environment
- delivery model: `GitHub Actions + GHCR + deploy over SSH`
- hosting model: core services self-hosted
- managed edge and offsite services allowed where they improve operations:
  - `Cloudflare` for DNS/TLS/WAF/rate limiting
  - `S3-compatible` storage for offsite backups

## 4. Recommended Architecture

### 4.1 Core services

Each environment runs the same platform shape:

- `nginx`
- `odoo`
- `postgres`
- `redis`
- `pgbackrest`

Optional services:

- `pgAdmin` only in admin profile
- `Mailpit` in `dev` and optionally `staging`
- `Loki/Promtail` and `Grafana` in later phase
- `Prometheus` in later phase

### 4.2 Network topology

Public traffic path:

`Cloudflare -> Nginx -> Odoo`

Private-only services:

- PostgreSQL
- Redis
- pgBackRest repository
- pgAdmin

Exposure rules:

- only `80/443` open publicly on the server
- no public `ports:` for PostgreSQL
- no public `ports:` for Redis
- no public `ports:` for internal Odoo app ports
- admin tools available only through SSH tunnel, VPN, Tailscale, or strict allowlist

### 4.3 Odoo runtime model

Environment-specific runtime:

- `dev`: simpler settings, lower workers, development tooling allowed
- `staging`: production-like settings plus neutralization
- `prod`: hardened settings, no admin utilities exposed

Production-like environments must use:

- `proxy_mode = True`
- reverse proxy in front of Odoo
- dedicated websocket route to the `gevent` port
- multiprocess workers

## 5. Repo Structure

Target repository structure:

```text
odoo-platform/
  .env.example
  .gitignore
  compose.yaml
  compose.dev.yaml
  compose.staging.yaml
  compose.prod.yaml
  compose.admin.yaml
  .github/
    workflows/
  odoo/
    Dockerfile
    requirements.txt
    config/
      odoo.conf
      odoo.dev.conf
      odoo.staging.conf
      odoo.prod.conf
    addons/
    scripts/
  nginx/
    conf.d/
      odoo.conf.template
  pgbackrest/
    pgbackrest.conf
    scripts/
  backup/
    scripts/
  ops/
    bootstrap/
    restore/
    hardening/
  docs/
    architecture/
    runbooks/
    superpowers/
      specs/
```

Design rule:

- repository stores code, config templates, scripts, and docs
- repository does not store live database files
- repository does not store live filestore contents
- repository does not store real secrets

## 6. Persistent Data Layout

Persistent state must live outside the git checkout.

Recommended Linux layout per environment:

```text
/srv/odoo/<project>/<env>/
  postgres/
  filestore/
  pgbackrest/
  logs/
  env/
```

This keeps deployments repeatable and avoids mixing runtime state with source control.

## 7. Compose Strategy

Compose layering model:

- `compose.yaml`: base platform
- `compose.dev.yaml`: development overrides
- `compose.staging.yaml`: staging overrides
- `compose.prod.yaml`: production overrides
- `compose.admin.yaml`: temporary admin tools

Examples:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d
docker compose -f compose.yaml -f compose.staging.yaml up -d
docker compose -f compose.yaml -f compose.prod.yaml up -d
docker compose -f compose.yaml -f compose.prod.yaml -f compose.admin.yaml up -d pgadmin
```

## 8. Image Strategy

Do not depend only on `odoo:19.0` at runtime.

Build a project image:

- base: `odoo:19.0`
- Python dependencies pinned in `requirements.txt`
- optional system packages required by the project
- predictable addon paths
- minimal operational tooling

Benefits:

- repeatable builds
- predictable deploys
- environment parity
- easier rollback through image tags

## 9. Nginx and Reverse Proxy Design

`nginx` is mandatory in `staging` and `prod`.

Required behavior:

- redirect HTTP to HTTPS
- forward standard app traffic to Odoo HTTP port
- route `/websocket/` to the Odoo `gevent` port
- send `X-Forwarded-For`, `X-Forwarded-Host`, `X-Forwarded-Proto`
- support websocket upgrade headers
- enforce upload size limits appropriate for Odoo documents
- set conservative proxy timeouts suitable for Odoo requests
- enable compression where safe

`proxy_mode` must be enabled only in environments actually behind the proxy.

## 10. Redis Role

Redis is included as platform infrastructure, even though base Odoo can run without it.

Reasons:

- future-ready support for queue/worker patterns
- caching for custom integrations
- background processing ecosystems such as `queue_job`
- rate limiting or auxiliary platform services

This keeps the platform closer to a professional template than a minimal local stack.

## 11. Backup and Restore Design

### 11.1 Backup policy

Production backup policy mirrors Odoo.sh retention behavior:

- 7 daily
- 4 weekly
- 3 monthly

Backup units:

- PostgreSQL database via `pgBackRest`
- Odoo filestore
- key configuration snapshots:
  - environment files
  - Odoo config
  - deployment scripts
  - custom addons manifest state

Production backups go to:

- local backup repository
- offsite `S3-compatible` storage

### 11.2 Staging backup policy

Default policy:

- no continuous automatic backup requirement for staging
- optional manual pre-change backup if staging contains valuable test work

This follows the Odoo.sh operational model where automated backups focus on production.

### 11.3 Restore policy

The platform must include restore scripts for:

- database-only restore
- filestore-only restore
- full restore to staging
- disaster restore to a clean host

Minimum restore workflow:

1. restore PostgreSQL backup
2. restore filestore
3. inject environment-specific config
4. apply staging neutralization if target is staging
5. run smoke checks

### 11.4 Restore drill

Backups are not considered complete unless restore is tested regularly.

The platform must include a scheduled restore drill into staging or a disposable validation environment.

## 12. Staging Neutralization

Staging is a neutralized copy of production, not a second production environment.

Required staging controls:

- block real outbound mail, redirect to `Mailpit` or a sink
- disable or control sensitive scheduled actions
- disable or fake dangerous external integrations
- prevent accidental customer-facing actions
- avoid production license key misuse

Operational model:

- restore fresh production copy into staging when needed
- validate candidate code there
- discard/rebuild staging rather than treating it as a long-lived authoritative system

## 13. Git and Delivery Model

Branching model:

- `main`: production
- `staging`: preproduction
- `develop`: integration
- `feature/*`: feature work

Promotion model:

- push/merge to `develop` -> deploy to dev
- push/merge to `staging` -> deploy to staging
- push/merge to `main` -> deploy to production

Advanced option:

- use git submodules only if private addon repos or client-specific addon repos become necessary

## 14. CI/CD Design

Platform pipeline in `GitHub Actions`:

1. lint and static checks
2. build project image
3. push image to `GHCR`
4. deploy over SSH to target server
5. `docker compose pull`
6. `docker compose up -d`
7. run post-deploy smoke checks

Recommended deployment characteristics:

- immutable image tags per commit SHA
- human-readable tags per branch/environment
- explicit environment secrets in GitHub Actions
- separate deploy jobs per environment
- rollback by redeploying previous image tag

## 15. Secrets and Configuration Management

Immediate rule:

- no secrets committed to git

Minimum acceptable:

- `.env` files outside git

Preferred professional path:

- `SOPS + age`
- or `1Password Secrets`
- or `Vault`

Secret categories:

- PostgreSQL credentials
- Odoo admin password
- SMTP credentials
- Cloudflare tokens
- S3 backup credentials
- GitHub deploy SSH keys

## 16. Security Baseline

Required baseline:

- SSH keys only
- disable password SSH login
- firewall allowing only required ports
- PostgreSQL never public
- Redis never public
- pgAdmin never public by default
- least-privilege runtime users where practical
- image update process under change control
- TLS termination at nginx with Cloudflare in front
- health checks on core services
- log rotation and retention policy

Recommended next layer:

- fail2ban where appropriate
- WAF/rate limiting in Cloudflare
- centralized logs
- alerting for backup failures and service health failures

## 17. Observability Roadmap

Phase 1 does not need full observability stack, but the design reserves space for it.

Recommended later additions:

- `Loki + Promtail` for logs
- `Grafana` dashboards
- `Prometheus` metrics
- service-level alerts
- backup success/failure alerts

## 18. Non-Goals

This project does not try to recreate:

- Odoo.sh internal web editor
- Odoo.sh UI for branch administration
- Odoo-managed upgrade platform
- full HA/multi-node orchestration on day one

Those features add a lot of engineering cost without improving the core objective for a single-project platform.

## 19. Implementation Phases

### Phase 1

- restructure repo into platform layout
- move secrets out of source control
- add `.gitignore`
- introduce project Docker image
- add `nginx`
- add environment-specific compose files
- add production-safe Odoo config
- remove live PostgreSQL data from repository layout

### Phase 2

- add `redis`
- add `pgBackRest`
- add filestore backup scripts
- add staging environment
- add `GitHub Actions`
- add `GHCR` publishing
- add deploy scripts

### Phase 3

- add centralized logging
- add dashboards/metrics
- add offsite backup automation
- add restore drill automation
- add staging neutralization automation
- add UI/branding enhancements

## 20. Official Guidance Used To Validate This Design

Checked on 2026-04-15.

Primary sources:

- Odoo 19 on-prem deployment guidance:
  - https://www.odoo.com/documentation/19.0/administration/on_premise/deploy.html
- Odoo.sh branches:
  - https://www.odoo.com/documentation/18.0/administration/odoo_sh/getting_started/branches.html
- Odoo.sh builds:
  - https://www.odoo.com/documentation/18.0/administration/odoo_sh/getting_started/builds.html
- Odoo knowledge article summarizing Odoo.sh operational behavior:
  - https://www.odoo.com/knowledge/article/31989

Validated points:

- production should run behind reverse proxy
- websocket traffic requires dedicated handling with the `gevent` worker
- `proxy_mode` must match real proxy deployment
- staging behaves as a neutralized production duplicate
- Odoo.sh backup retention model is `7 daily / 4 weekly / 3 monthly`
- automated Odoo.sh backups focus on production rather than staging/development

## 21. Recommendation

Proceed with this design as the base platform spec.

Next step after user review:

- create a detailed implementation plan
- then execute the platform refactor in phases
