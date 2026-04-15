# Platform Bootstrap

This repository is the versioned starting point for the Odoo 19 self-hosted platform.

## Current bootstrap scope

- safe GitHub-ready repository
- shared `compose.yaml`
- `compose.dev.yaml` for local development
- `compose.admin.yaml` for optional admin and knowledge tooling
- custom Odoo image scaffold
- Nginx reverse proxy template scaffold
- staging and production compose overrides
- bootstrap backup/restore scripts
- CI workflow skeleton

## Runtime data policy

Do not store live runtime data inside the git checkout.

The legacy local directories `postgres/` and `pgadmin/` are now ignored and should be treated as disposable leftovers from the pre-platform sandbox.

Use named volumes during this bootstrap phase. In later phases, production-like environments should move persistent state to environment-specific external paths such as:

```text
/srv/odoo/<project>/<env>/
```

## Current local commands

Development stack:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d
```

Optional admin and knowledge stack:

```bash
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d
```

Legacy compatibility stack:

```bash
docker compose up -d
```

## Not implemented yet

- Redis
- pgBackRest
- full GHCR deploy pipeline
- staging neutralization automation
- offsite backups
