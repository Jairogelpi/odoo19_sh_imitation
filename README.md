# Odoo 19 Self-Hosted Platform

Professional self-hosted Odoo 19 platform scaffold inspired by the operational shape of Odoo.sh.

## Current platform slices

- Git-safe repository with sanitized examples
- Base compose stack for Odoo, PostgreSQL, Nginx, Redis, and pgBackRest
- Dev, admin, staging, and production compose overrides
- Optional Homepage lobby, Obsidian knowledge layer, pgAdmin admin layer, Portainer container manager, OpenClaw MCP bridges, and operator/observability tooling
- Bootstrap backup and restore scripts
- Automated staging restore neutralization with Mailpit
- Offsite backup replication scripts for S3-compatible storage
- GitHub Actions pipeline for validation, GHCR publish, SSH deploy, and scaffold contract checks

## Current platform contract

This is the stable shape of the stack today.

| Layer | What belongs here | Status |
| --- | --- | --- |
| Edge | Nginx in front of Odoo | Stays the same |
| Core runtime | db, redis, pgBackRest, Odoo | Stays private and separate from any future control plane |
| Admin / support | Homepage, pgAdmin, Portainer, Obsidian, control-plane, MCP bridges, Code Server, Dozzle, web terminal, Grafana, Mailpit | Stays local or staging support |
| Delivery | Git, CI/CD, GHCR, env files, named volumes | Becomes the formal deployment base |

## Documentation map

- Platform bootstrap: [docs/architecture/platform-bootstrap.md](docs/architecture/platform-bootstrap.md)
- Service map: [docs/architecture/service-map.md](docs/architecture/service-map.md)
- Local development runbook: [docs/runbooks/local-development.md](docs/runbooks/local-development.md)
- Environments and promotions: [docs/runbooks/environments-and-promotions.md](docs/runbooks/environments-and-promotions.md)
- Secrets and configuration: [docs/runbooks/secrets-and-config.md](docs/runbooks/secrets-and-config.md)
- Runtime validation: [docs/runbooks/runtime-validation.md](docs/runbooks/runtime-validation.md)
- Backup and restore: [docs/runbooks/backup-and-restore.md](docs/runbooks/backup-and-restore.md)
- Control plane: [docs/runbooks/control-plane.md](docs/runbooks/control-plane.md)
- Admin and observability tooling: [docs/runbooks/admin-observability-tooling.md](docs/runbooks/admin-observability-tooling.md)
- Staging neutralization: [docs/runbooks/staging-neutralization.md](docs/runbooks/staging-neutralization.md)
- Offsite backups: [docs/runbooks/offsite-backups.md](docs/runbooks/offsite-backups.md)
- CI/CD scaffold: [docs/runbooks/ci-cd-scaffold.md](docs/runbooks/ci-cd-scaffold.md)
- Deployment over SSH: [docs/runbooks/deployment-over-ssh.md](docs/runbooks/deployment-over-ssh.md)
- Hardened OpenClaw deployment: [docs/runbooks/hardened-openclaw-deployment.md](docs/runbooks/hardened-openclaw-deployment.md)
- Cost-effective token management: [docs/runbooks/COST-EFFECTIVE-TOKEN-MANAGEMENT.md](docs/runbooks/COST-EFFECTIVE-TOKEN-MANAGEMENT.md)
- [Vault token operations](docs/runbooks/vault-token-operations.md)
- Email DNS records: [docs/runbooks/email-dns-records.md](docs/runbooks/email-dns-records.md)
- SSL certificates: [docs/runbooks/ssl-certificates.md](docs/runbooks/ssl-certificates.md)
- Lobby (Homepage): [docs/runbooks/lobby-homepage.md](docs/runbooks/lobby-homepage.md)
- Obsidian brain: [docs/00_Odoo_Brain.md](docs/00_Odoo_Brain.md)
- OpenClaw brain: [docs/brain/openclaw.md](docs/brain/openclaw.md)
- Agent Lightning integration: [docs/runbooks/agent-lightning-integration.md](docs/runbooks/agent-lightning-integration.md)
- [Training status](docs/training/TRAINING_READY.md)
- [Real Odoo training integration](docs/training/01-real-training-integration.md)
- [Hugging Face fine-tuning guide](docs/training/02-huggingface-finetuning.md)
- [Training script inventory](docs/training/03-training-script-inventory.md)

## Main entrypoints

- Architecture spec: [docs/superpowers/specs/2026-04-15-odoo-self-hosted-platform-design.md](docs/superpowers/specs/2026-04-15-odoo-self-hosted-platform-design.md)
- Bootstrap plan: [docs/superpowers/plans/2026-04-15-odoo-platform-bootstrap-implementation-plan.md](docs/superpowers/plans/2026-04-15-odoo-platform-bootstrap-implementation-plan.md)
- Platform bootstrap doc: [docs/architecture/platform-bootstrap.md](docs/architecture/platform-bootstrap.md)
- Runtime validation: [docs/runbooks/runtime-validation.md](docs/runbooks/runtime-validation.md)
- Obsidian brain: [docs/00_Odoo_Brain.md](docs/00_Odoo_Brain.md)
- OpenClaw brain: [docs/brain/openclaw.md](docs/brain/openclaw.md)

## Local commands

Windows and Docker Desktop:

1. Install Docker Desktop and enable the WSL 2 backend.
2. Open this repository in a Windows path that Docker Desktop can share.
3. Then use the development stack command below.

Development stack:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml up -d
```

The base stack now auto-bootstraps the local pgBackRest stanza on the first WAL archive, so the first local startup no longer depends on a manual `stanza-create` step.

Admin and knowledge stack:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d
```

Local health check:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-local-stack.ps1
```

Admin stack health check:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-admin-stack.ps1
```

OpenClaw external connector health check (gateway + Obsidian + Memory + Context7):

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-openclaw-connectors.ps1
```

## Current local endpoints

- Homepage lobby: `http://localhost:8081`
- Control plane: `http://localhost:8082`
- Code Server: `http://localhost:8083`
- Dozzle: `http://localhost:8084`
- Web terminal: `http://localhost:8085`
- Odoo direct: `http://localhost:8069/web/login`
- Odoo through Nginx: `http://localhost:8088/web/login`
- Grafana: `http://localhost:3002`
- pgAdmin: `http://localhost:8080`
- Obsidian: `http://localhost:3000`
- Portainer: `https://localhost:9443`

## Services, routes, and defaults

This stack is designed to run with Docker Desktop using the compose files in this repository.

| Service | Purpose | Local route / port | Default credentials or defaults | How to change it |
| --- | --- | --- | --- | --- |
| db | PostgreSQL database used by Odoo and pgBackRest | No public port in the base stack | Database: `postgres`<br>User: `odoo`<br>Password: `change_me` | Set `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` in `.env` or an environment-specific env file |
| odoo | Main ERP application | `http://localhost:8069/web/login` in dev<br>Behind nginx in staging and production | Odoo master password currently comes from `config/odoo*.conf` and defaults to `change_me`<br>DB host: `db`<br>DB user: `odoo`<br>DB password: `change_me` | Today, rotate the master password in both the env file and `config/odoo.conf`, `config/odoo.staging.conf`, or `config/odoo.prod.conf` as appropriate; `ODOO_ADMIN_PASSWORD` is present in the env examples but is not yet injected into Odoo automatically |
| nginx | Reverse proxy for Odoo | `http://localhost:8088/web/login` in dev<br>`https://<server>/web/login` in staging and production, with HTTP redirected to HTTPS | `SERVER_NAME=_` in dev | Set `SERVER_NAME` in the env file, and set `NGINX_TLS_CERTS_DIR` in staging and production so `/etc/nginx/certs/fullchain.pem` and `/etc/nginx/certs/privkey.pem` exist inside the container |
| pgbackrest | Backup and restore helper | No public port in the base stack | `PGBACKREST_STANZA=odoo` | Set `PGBACKREST_STANZA` in the env file if you rename the stanza |
| redis | Cache and future queue primitive | No public port in the base stack | No login | No credentials; change only if you replace the image or runtime settings |
| pgadmin | PostgreSQL admin UI | `http://localhost:8080` | Email: `admin@example.com`<br>Password: `change_me` | Set `PGADMIN_DEFAULT_EMAIL` and `PGADMIN_DEFAULT_PASSWORD` in `.env` or `.env.dev` |
| obsidian | Knowledge workspace backed by `docs/` | `http://localhost:3000` and `http://localhost:3001` | User: `obsidian`<br>Password: `change_me` | Set `OBSIDIAN_CUSTOM_USER` and `OBSIDIAN_PASSWORD` in `.env` or `.env.dev` |
| portainer | Container management UI for Docker Desktop | `https://localhost:9443` | No default login in the repo; first admin user is created on first launch | Keep `portainer-data` persistent and avoid removing the Docker socket mount if you want Portainer to manage local containers |
| homepage | Admin landing page and status lobby | `http://localhost:8081` | No built-in login; access is limited only by `HOMEPAGE_ALLOWED_HOSTS` unless you put a reverse proxy in front | Keep `HOMEPAGE_ALLOWED_HOSTS` aligned with the hostname you use; never expose the lobby publicly without authentication in front |
| control-plane | Operator console plus OpenClaw gateway bridge | `http://localhost:8082` | No built-in repo default login; access is whoever can reach the port | Keep the Docker socket mount read-only, keep `GITHUB_TOKEN` / `OPENROUTER_API_KEY` / `OPENCLAW_*` tokens in env, and rebuild on source changes |
| code-server | Browser IDE over selected workspace folders | `http://localhost:8083` | Password: `change_me` by default from compose fallback | Set `CODE_SERVER_PASSWORD`; do not expose publicly without authentication in front |
| dozzle | Browser log viewer over Docker containers | `http://localhost:8084` | No built-in login in this stack | Keep it local/admin-only; it reads the Docker socket and is operationally sensitive |
| web-terminal | Browser shell for Docker/container operations | `http://localhost:8085` | No built-in login in this stack | Treat it as an admin surface; it is for Docker operations and should stay private |
| grafana | Metrics dashboards backed by Prometheus | `http://localhost:3002` | User: `admin`<br>Password: `change_me` | Set `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD` in the env file |
| mailpit | Staging mail sink after restore neutralization | `http://127.0.0.1:8025` in staging | No login in the compose stack | Set `STAGING_MAILPIT_UI_PORT` in the staging env file |

Additional internal-only optional services from `compose.admin.yaml` are documented in [Admin and observability tooling](docs/runbooks/admin-observability-tooling.md):

- `obsidian-mcp`
- `memory-mcp`
- `context7-mcp`
- `cif-lookup-mcp`
- `cadvisor`
- `node-exporter`
- `prometheus`

Obsidian first launch:

- Open `http://localhost:3000`.
- Sign in with the Obsidian credentials above if the auth prompt appears.
- In the launcher, choose `Open folder as vault`.
- Select `/config/ObsidianVault`, which is the mounted `docs/` directory inside the container.
- After opening it once, Obsidian should remember the vault through the persistent `obsidian-config` volume.

Portainer first launch:

- Open `https://localhost:9443`.
- A browser certificate warning is expected on first access because Portainer uses local HTTPS.
- Create the first admin user when Portainer asks for it.
- Choose the local Docker environment/socket connection so it can see the containers from this compose project.
- Keep the `/var/run/docker.sock` bind mount and `portainer-data` volume in place so Portainer can manage the stack persistently.

## How to change defaults

Use the tracked example files as templates and keep your real values in an untracked `.env` file.

For local development:

```powershell
Copy-Item .env.dev.example .env
```

For staging:

```powershell
Copy-Item .env.staging.example .env
```

For production:

```powershell
Copy-Item .env.prod.example .env
```

Then edit the copied `.env` file and restart the relevant stack with Docker Compose.

Important files that control defaults:

- `.env.example`
- `.env.dev.example`
- `.env.staging.example`
- `.env.prod.example`
- `config/odoo.conf`
- `config/odoo.staging.conf`
- `config/odoo.prod.conf`

Notes:

- `config/odoo.conf` contains the local Odoo database login values and the master password used by Odoo itself.
- `config/odoo.staging.conf` and `config/odoo.prod.conf` still carry the Odoo `admin_passwd` too; env examples alone do not rotate that value yet.
- `compose.admin.yaml` enables the optional admin, knowledge, and container-management services.
- `compose.admin.yaml` also carries the optional MCP bridge, operator shell, and observability services documented in [Admin and observability tooling](docs/runbooks/admin-observability-tooling.md).
- `compose.staging.yaml` and `compose.prod.yaml` switch Nginx into required TLS mode and expect `NGINX_TLS_CERTS_DIR` to expose `fullchain.pem` and `privkey.pem` on the host.

## Current verified reality

As of April 16, 2026, the following has been validated from this workspace:

- local base stack boots and passes `check-local-stack.ps1`
- local admin stack boots and passes `check-admin-stack.ps1`
- Homepage lobby renders and shows stable status for Odoo, Odoo directo, Nginx, Portainer, pgAdmin, pgBackRest, and Obsidian
- internal lobby monitors use container-reachable targets instead of `localhost`
- staging and production Nginx overrides enforce real TLS and have been exercised with temporary self-signed certificates

Still pending:

- live deploy to a real remote target host
- restore drill against a real backup set
- automatic Odoo master-password injection from `ODOO_ADMIN_PASSWORD`

Full evidence and reproduction commands live in:

- [docs/runbooks/runtime-validation.md](docs/runbooks/runtime-validation.md)

## Addons layout

- `addons/` for third-party, OCA, or shared repository modules
- `addons_custom/` for in-house modules
- `addons_custom/openclaw/` is the permissioned AI agent shell for MCP-backed workflows
- Docker mounts both addon trees into the Odoo container in every environment
- Odoo resolves `/mnt/custom-addons` before `/mnt/extra-addons`

## Adding a module later

- Third-party or OCA modules belong in `addons/<module_name>/`.
- In-house modules belong in `addons_custom/<module_name>/`.
- Odoo loads both trees automatically through `/mnt/custom-addons,/mnt/extra-addons`.
- After adding a module, refresh the Apps list or install/update it with `-i` or `-u`.

## Core health commands

Redis:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml exec -T redis redis-cli ping
```

pgBackRest check:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml exec -T pgbackrest /scripts/check-db.sh
```

pgBackRest full backup:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml exec -T pgbackrest /scripts/backup-db.sh
```

Admin stack verification:

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-admin-stack.ps1
```

## Notes

- `compose.legacy.yaml` remains available as the legacy compatibility stack for local use.
- If you explicitly need that old stack shape, run `docker compose -f compose.legacy.yaml up -d`.
- The forward-looking platform path is `compose.yaml` plus overrides.
- Remote delivery now expects GHCR-published images plus server-side env files and GitHub Environment secrets.
- Critical operational wrappers are syntax-checked in CI, but staging restore and remote deploy still need live end-to-end drills against real infrastructure.
- The `docs/` directory doubles as the Obsidian vault.
