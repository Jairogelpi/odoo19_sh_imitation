# Control Plane Runbook

## Goal

Opinionated, stack-aware UI that replaces the hand-assembled SSH cookbooks for the three actions the operator performs most:

1. **Restore a pgBackRest backup** to a chosen environment with written confirmation.
2. **See GitHub deploy state** (workflow runs, branches, PRs) of `Jairogelpi/odoo19_sh_imitation` without leaving the browser.
3. **Navigate the `docs/` Obsidian vault** as rendered markdown with a working folder tree.

The control plane is a small FastAPI + Jinja2 service. It lives in `compose.admin.yaml`, doubles as the MCP gateway for OpenClaw, and is optional — the production base stack never starts it.

## Service definition

- Image: `odoo19-control-plane:local` (built from `./control-plane`)
- Compose layer: `compose.admin.yaml`
- Network: `odoo_net`
- Host port: `8082` → container `8082`
- User: `0:0` (must be root so it can read the root-owned Docker socket and issue `docker exec` against sibling containers)
- Volumes:
  - `/var/run/docker.sock` → read-only, used for `docker exec pgbackrest …` and `docker stop/start` during restore
  - `./docs` → `/app/docs`, writable, used by the docs browser and MCP docs tools
  - `./addons_custom` → `/workspace/addons_custom`, writable, used by MCP workspace tools for in-house modules

## URLs

- Entry (redirects to `/backups`): `http://localhost:8082`
- Backups: `http://localhost:8082/backups`
- Deploys: `http://localhost:8082/deploys`
- Docs browser: `http://localhost:8082/docs`
- MCP gateway: `http://localhost:8082/mcp`
- Healthcheck: `http://localhost:8082/healthz`

From the lobby the tiles live under the **Control plane** group and also replace the old pgBackRest tile in **Operaciones**.

## Source layout

All source lives under `control-plane/` in the repo.

```
control-plane/
├── Dockerfile              # python:3.12-slim + docker-ce-cli + uvicorn
├── requirements.txt
├── scripts/                # reserved for future CLI helpers
└── app/
    ├── config.py           # Settings dataclass, reads env
    ├── backups.py          # pgBackRest info + restore via `docker exec`
    ├── github_api.py       # REST wrapper over api.github.com
    ├── docs_browser.py     # walks docs/ and renders markdown
    ├── mcp_gateway.py      # MCP JSON-RPC gateway and tool registry
    ├── main.py             # FastAPI routes
    ├── static/app.css      # full design system (topbar, tables, dialog…)
    └── templates/          # base.html, backups.html, deploys.html, docs.html
```

The app **does not** expose the FastAPI auto docs (`/docs` is reserved for the Obsidian browser). `docs_url=None`, `redoc_url=None`, `openapi_url=None`.

## Environment variables

Defined in `.env.example`:

- `STACK_ENV` — which environment this instance represents (`dev|staging|prod`). **Only `dev` executes local restores**; `staging` and `prod` render the SSH recipe you paste on the destination host.
- `GITHUB_REPO` — `<owner>/<repo>`. Default: `Jairogelpi/odoo19_sh_imitation`.
- `GITHUB_TOKEN` — fine-grained PAT with `repo:read` + `actions:read`. Never committed.
- `PGBACKREST_CONTAINER` — default `odoo19-pgbackrest-1` (compose project name + service + replica).
- `ODOO_CONTAINER` — default `odoo19-odoo-1`.
- `DB_CONTAINER` — default `odoo19-db-1`.
- `PGBACKREST_STANZA` — reuses the existing `PGBACKREST_STANZA` env, default `odoo`.
- `DOCS_ROOT` — fixed to `/app/docs` inside the container (bind-mounted from `./docs`).
- `OPENCLAW_ADDONS_CUSTOM_ROOT` — fixed to `/workspace/addons_custom` inside the container.
- `OPENCLAW_WORKSPACE_ROOT` — fixed to `/workspace` inside the container.
- `OPENCLAW_SHELL_ENABLED` — `0` by default; shell execution remains disabled unless explicitly enabled.
- `ALLOWED_ENVS` — comma-separated list of environments the dropdown accepts. Default `dev,staging,prod`.
- `OPENROUTER_API_KEY` — required for OpenRouter-backed draft generation.
- `OPENROUTER_MODEL` — default `z-ai/glm-4.5-air:free`, a free model that is explicitly tuned for agent-centric workflows.
- `OPENROUTER_FALLBACK_MODEL` — default `openrouter/elephant-alpha`, a second free model used if the primary model is unavailable.
- `OPENROUTER_REASONING_ENABLED` — `1` by default; enables reasoning on models that support it.
- `OPENROUTER_API_BASE` — default `https://openrouter.ai/api/v1`.
- `OPENROUTER_TITLE` / `OPENROUTER_REFERER` — optional OpenRouter routing headers.

If `GITHUB_TOKEN` is missing, the Deploys page renders an informational banner rather than crashing, so you can still use backups and docs.

## Start / stop

Bring up the full dev + admin stack:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d --build control-plane
```

Bring up only the control plane (base stack already running):

```powershell
docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d control-plane
```

Stop without tearing down the rest:

```powershell
docker compose -f compose.admin.yaml stop control-plane
```

Source changes under `control-plane/app/` need a **rebuild** (the Dockerfile `COPY`s the tree). `docker restart` alone is not enough.

## Restore workflow

1. Open `http://localhost:8082/backups`. The table lists every backup returned by `pgbackrest --stanza=<stanza> info --output=json`, with label, type (full/diff/incr), age, sizes, and WAL range.
2. Click **Recuperar** on the row you want. A modal opens.
3. Pick the **Entorno destino** (`dev`, `staging`, `prod`).
4. Type the same name in **Escribe el nombre del entorno para confirmar**. Client-side pattern is `^(dev|staging|prod)$` and the server re-checks that `confirm == target_env`.
5. Submit.

Behavior after submit:

- `target_env == "dev"` **and** `STACK_ENV == "dev"`: the app runs the restore locally:
  1. `docker stop odoo` and `docker stop db` (names come from env)
  2. `docker exec pgbackrest pgbackrest --stanza=<stanza> --delta --set <label> --type=immediate --target-action=promote restore`
  3. `docker start db`, `docker start odoo`
  4. redirects back to `/backups` with a success/failure flash.
- `target_env in {staging, prod}` (or `STACK_ENV != "dev"`): the app renders an HTML page with a ready-to-paste SSH recipe (see `app/backups.py::remote_restore_recipe`). Copy, paste on the destination host, done.

This matches the long-standing rule: **only `dev` restores from here**; staging/prod are never automated from a developer's laptop.

## Deploys page

- Calls `/repos/{repo}/actions/runs?per_page=15`, `/repos/{repo}/branches`, `/repos/{repo}/pulls?state=open` in parallel via `httpx`.
- Each call is wrapped in `safe()` — if one fails the others still render and the error is shown as a red banner.
- Badge colours map CI states:
  - `badge-success` (completed + success)
  - `badge-failure` (completed + failure)
  - `badge-running` (in_progress / queued)
  - `badge-cancelled` (cancelled / timed_out)
- Run table links straight to `run.html_url`; the repo link points to `repo_meta.html_url`.

## Docs browser

- `build_tree()` walks `/app/docs` and keeps directories plus `.md` files.
- `read_markdown(path)` guards against path escape (`..`, absolute paths) and only serves files under `DOCS_ROOT`.
- Markdown extensions loaded: `fenced_code`, `tables`, `toc`, `codehilite`, `sane_lists`.
- The URL `?path=<rel>` can point to either a file (renders it) or a directory (opens the tree at that node). Empty path shows the root with no article.
- Used by the lobby bookmarks (`Documentación` group) to deep-link into folders like `runbooks`, `architecture`, `superpowers`, `odoo19_schema`, and the brain entry point `00_Odoo_Brain.md`.

## Verification

Automated (recommended):

```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-admin-stack.ps1
```

Manual:

```bash
curl http://localhost:8082/healthz                      # {"status":"ok","env":"dev"}
curl -o /dev/null -w "%{http_code}" http://localhost:8082/backups   # 200
curl -o /dev/null -w "%{http_code}" http://localhost:8082/deploys   # 200
curl -o /dev/null -w "%{http_code}" http://localhost:8082/docs      # 200
```

## Maintenance

- **Renaming a service / container**: update `PGBACKREST_CONTAINER`, `ODOO_CONTAINER`, or `DB_CONTAINER` in `.env`. These must match `docker ps` output exactly; the defaults assume the compose project name `odoo19`.
- **Rotating the GitHub token**: edit `.env`, then `docker compose -f compose.yaml -f compose.dev.yaml -f compose.admin.yaml up -d control-plane`. The token is read at boot.
- **Editing Python source**: rebuild (`up -d --build control-plane`). A bare restart keeps the old code in the image.
- **Editing CSS or templates only**: same — rebuild. Source files are `COPY`ed, not mounted.
- **Changing the OpenRouter model**: edit `OPENROUTER_MODEL` in `.env` or set it in your shell, then rebuild the control-plane container. The current default is `z-ai/glm-4.5-air:free`; `openrouter/elephant-alpha` remains the fallback.

## Troubleshooting

- `/docs` returns Swagger UI: FastAPI's built-in docs are colliding with ours. Confirm `docs_url=None, redoc_url=None, openapi_url=None` in `app/main.py` and rebuild.
- Backups page shows `No se pudo leer pgbackrest info`: control-plane cannot reach `PGBACKREST_CONTAINER`. Check it exists (`docker ps | grep pgbackrest`) and that the Docker socket is mounted. The container must also be running.
- Deploys page says "GITHUB_TOKEN no configurado": expected when no token is set. Add it to `.env` and restart. Rotate if leaked.
- Deploys page shows HTTP 401: token is invalid or expired. Rotate on GitHub, update `.env`, restart.
- Restore modal says confirmation mismatch: the typed value must equal the dropdown value literally (`dev`, `staging`, `prod`).
- Restore in dev leaves Odoo stopped: check logs with `docker logs odoo19-control-plane-1`; the restore step logs its stdout/stderr. Start manually: `docker start odoo19-db-1 && docker start odoo19-odoo-1`.
- `EACCES /var/run/docker.sock`: the container is not running as root. Keep `user: "0:0"` in `compose.admin.yaml`.
- Docs browser shows empty tree: the bind mount `./docs:/app/docs` is missing or empty. `docker inspect odoo19-control-plane-1` to verify.

## Security notes

- The control plane has no authentication. **Never expose port 8082 outside localhost** without a reverse proxy + auth in front.
- The Docker socket is mounted read-only, but `docker exec` still allows arbitrary command execution inside the pgBackRest / Odoo / db containers. Treat the control plane the same way you treat root on the host.
- The GitHub token grants read access to the repo and Actions; set the fine-grained PAT to read-only scopes. Rotate on leak immediately.

## Related notes

- [Lobby runbook](lobby-homepage.md)
- [Backup and restore runbook](backup-and-restore.md)
- [Deployment over SSH](deployment-over-ssh.md)
- [CI/CD scaffold](ci-cd-scaffold.md)
- [Control plane brain note](../brain/control_plane.md)
- [Service map](../architecture/service-map.md)
- [Stack topology](../brain/stack_topology.md)
- [Services](../brain/services.md)
