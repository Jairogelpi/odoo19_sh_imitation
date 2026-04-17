# Runtime Validation

## Goal

Capture what has been validated for real in this workspace, what commands were used, and what is still pending.

This runbook is the truth source for "verified now" versus "planned but not yet exercised".

## Validation snapshot

Validation snapshot date:

- April 16, 2026

Validated from this repository checkout on a Windows host with Docker Desktop running.

## What has been verified

### Compose contract

These compose variants resolve successfully:

- `compose.yaml` + `compose.dev.yaml`
- `compose.yaml` + `compose.staging.yaml`
- `compose.yaml` + `compose.prod.yaml`
- `compose.yaml` + `compose.dev.yaml` + `compose.admin.yaml`

Primary verification commands:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml config
docker compose -f compose.yaml -f compose.staging.yaml config
docker compose -f compose.yaml -f compose.prod.yaml config
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml config
python -m unittest discover -s tests -p 'test_*.py' -v
```

Current result:

- scaffold contract tests pass
- compose resolution passes for dev, staging, and prod overrides

### Local base stack

The local development stack has been validated end to end:

- `db`
- `redis`
- `pgbackrest`
- `odoo`
- `nginx`

Primary verification commands:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml up -d
powershell -ExecutionPolicy Bypass -File .\ops\health\check-local-stack.ps1
docker compose -f compose.yaml -f compose.dev.yaml exec -T redis redis-cli ping
docker compose -f compose.yaml -f compose.dev.yaml exec -T pgbackrest /scripts/check-db.sh
docker compose -f compose.yaml -f compose.dev.yaml exec -T pgbackrest /scripts/backup-db.sh
```

Observed result:

- Odoo direct returns HTTP `200`
- Odoo through Nginx returns HTTP `200`
- Redis returns `PONG`
- pgBackRest binary and local backup flow work

### Optional admin and knowledge layer

The admin stack has also been validated live:

- `homepage`
- `pgadmin`
- `obsidian`
- `portainer`

Primary verification commands:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d
powershell -ExecutionPolicy Bypass -File .\ops\health\check-admin-stack.ps1
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml ps
```

Observed result:

- Homepage lobby returns HTTP `200`
- pgAdmin returns HTTP `200`
- Obsidian returns HTTP `401`, which is expected because it is auth-gated
- Portainer is reachable on local HTTPS

### Homepage lobby behavior

The lobby has been validated both through internal probes and through a real rendered browser page.

Internal monitor routes now use container-reachable addresses:

- `http://nginx/healthz`
- `http://odoo:8069/web/login`
- `http://pgadmin:80`
- `http://portainer:9000`

Intentional non-monitored services:

- `obsidian`: auth-gated, so Docker status only
- `pgbackrest`: CLI-only, so Docker status only

Primary verification commands:

```powershell
docker exec odoo19-homepage-1 sh -lc "wget -q -S -O - http://nginx/healthz 2>&1 | sed -n '1,8p'"
docker exec odoo19-homepage-1 sh -lc "wget -q -S -O - http://odoo:8069/web/login 2>&1 | sed -n '1,12p'"
docker exec odoo19-homepage-1 sh -lc "wget -q -S -O - http://pgadmin:80 2>&1 | sed -n '1,12p'"
docker exec odoo19-homepage-1 sh -lc "wget -q -S -O - http://portainer:9000 2>&1 | sed -n '1,12p'"
```

Observed result:

- `nginx/healthz` returns HTTP `204`
- Odoo direct monitor path resolves successfully
- pgAdmin monitor path resolves successfully
- Portainer monitor path resolves successfully
- final browser snapshot shows `Ejecutando` for Odoo, Odoo directo, Nginx, Portainer, pgAdmin, pgBackRest, and Obsidian

Note:

- right after a restart, Homepage can briefly show `Desconocido` while its API cache refreshes
- after a few seconds, the final stable view matches the runtime state correctly

### Staging and production TLS path

The staging and production Nginx path has been validated with temporary self-signed certificates.

Primary verification flow:

- mount temporary `fullchain.pem` and `privkey.pem` through `NGINX_TLS_CERTS_DIR`
- start the stack with `compose.staging.yaml` or `compose.prod.yaml`
- probe HTTP and HTTPS paths

Observed result:

- `http://localhost/web/login` returns `301`
- redirect target is `https://localhost/web/login`
- HTTPS listener starts correctly on `443`
- Odoo behind TLS responds through Nginx
- the first Odoo HTTPS response is `303` to `/web/database/selector`
- following redirects ends at HTTP `200`

## Current known gaps

These items are still documented as pending because they have not been validated against real infrastructure yet:

- live deploy to a real remote target host
- post-deploy verification against a real remote environment
- restore drill against a real backup set
- scheduled restore drills and scheduled offsite runs

## Current configuration caveats

These are important because the repository still contains a few scaffold-era behaviors:

- `ODOO_ADMIN_PASSWORD` exists in the env example files, but the Odoo master password is still sourced from `admin_passwd` inside `config/odoo.conf`, `config/odoo.staging.conf`, and `config/odoo.prod.conf`
- changing the env value alone does not rotate the Odoo master password yet
- until config templating is added for Odoo itself, rotate the value in both places if you need a real password change

## Related runbooks

- [Local development](local-development.md)
- [Lobby (Homepage)](lobby-homepage.md)
- [Secrets and configuration](secrets-and-config.md)
- [Backup and restore](backup-and-restore.md)
- [Deployment over SSH](deployment-over-ssh.md)
