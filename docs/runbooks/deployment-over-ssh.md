# Deployment Over SSH

## Goal

Document the production-shaped delivery path for this platform: validate in CI, publish custom images to GHCR, then deploy remotely over SSH with pinned environment secrets.

## What the workflow does

The GitHub Actions workflow at `.github/workflows/platform-ci.yml` now performs three phases:

1. validate `compose.yaml` with `dev`, `staging`, and `prod` overrides
2. build the custom `db`, `pgbackrest`, and `odoo` images
3. on pushes to `develop`, `staging`, or `main`, publish those images to GHCR and deploy the matching environment over SSH

Branch-to-environment mapping:

- `develop` -> `dev`
- `staging` -> `staging`
- `main` -> `prod`

## Images published to GHCR

Each push publishes three images:

- `ghcr.io/<owner>/odoo19-db:<sha>`
- `ghcr.io/<owner>/odoo19-pgbackrest:<sha>`
- `ghcr.io/<owner>/odoo19-odoo:<sha>`

The workflow also tags each image with the branch name for quick inspection:

- `ghcr.io/<owner>/odoo19-db:<branch>`
- `ghcr.io/<owner>/odoo19-pgbackrest:<branch>`
- `ghcr.io/<owner>/odoo19-odoo:<branch>`

The remote deploy step uses the immutable `sha` tags.

## Required GitHub environment secrets

Define these in each GitHub Environment (`dev`, `staging`, `prod`):

- `DEPLOY_HOST`
- `DEPLOY_PORT`
- `DEPLOY_USER`
- `DEPLOY_SSH_KEY`
- `DEPLOY_KNOWN_HOSTS`
- `DEPLOY_APP_DIR`
- `DEPLOY_ENV_FILE`
- `DEPLOY_HEALTHCHECK_URL`
- `GHCR_PULL_USERNAME`
- `GHCR_PULL_TOKEN`

Notes:

- `DEPLOY_PORT` can be omitted if the host uses `22`
- `DEPLOY_KNOWN_HOSTS` should contain the pinned `known_hosts` line for the target server
- `GHCR_PULL_TOKEN` should have package read access only

## Remote host prerequisites

Each target host should already have:

- Docker Engine with the Compose plugin
- a clone of this repository at `DEPLOY_APP_DIR`
- the right branch available from `origin`
- an untracked environment file at `DEPLOY_ENV_FILE`
- network access to `ghcr.io`

Recommended bootstrap shape:

```bash
git clone https://github.com/Jairogelpi/odoo19_sh_imitation.git /srv/odoo/odoo19_sh_imitation
cp /srv/odoo/odoo19_sh_imitation/.env.prod.example /srv/odoo/env/prod.env
```

The deploy workflow does not write secrets into the repository. It expects the real env file to already exist on the server.

## Addon promotion model

- `addons/` and `addons_custom/` are promoted through Git with the rest of the repository
- the remote host receives addon changes through `git pull` during deploy
- no manual addon copy step should happen on the VPS host
- once deployed, Odoo sees both mounted addon trees automatically

## Remote deploy script

The server-side entrypoint is:

- `ops/deploy/remote-deploy.sh`

It performs:

1. required variable checks
2. branch fetch and fast-forward pull
3. GHCR login
4. `docker compose config`
5. `docker compose pull`
6. `docker compose up -d --remove-orphans`
7. `docker compose ps`

## Manual remote deploy example

If you need to run the same flow manually on a server:

```bash
TARGET_ENV=prod \
DEPLOY_BRANCH=main \
APP_DIR=/srv/odoo/odoo19_sh_imitation \
ENV_FILE=/srv/odoo/env/prod.env \
GHCR_PULL_USERNAME=your-ghcr-user \
GHCR_PULL_TOKEN=your-ghcr-token \
POSTGRES_IMAGE=ghcr.io/owner/odoo19-db:<sha> \
PGBACKREST_IMAGE=ghcr.io/owner/odoo19-pgbackrest:<sha> \
ODOO_IMAGE=ghcr.io/owner/odoo19-odoo:<sha> \
bash /srv/odoo/odoo19_sh_imitation/ops/deploy/remote-deploy.sh
```

## Current verification status

The workflow and remote deploy wrapper are syntax-checked in CI, and the workflow continues to validate compose plus image builds on every run.

Reference validation scope:

- `docs/runbooks/runtime-validation.md`

What is still missing:

- live deploy to a real target host is still pending
- post-deploy verification against a real environment is still pending
