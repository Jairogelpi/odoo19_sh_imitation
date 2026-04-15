# CI/CD Scaffold

## Current state

The repository already includes a starter workflow in:

- `.github/workflows/platform-ci.yml`

## What it does today

On push to `develop`, `staging`, or `main`, and on pull requests:

- checks out the repository
- validates `compose.yaml` + `compose.dev.yaml`
- builds the custom Odoo image

On push events it also logs the intended target environment based on branch:

- `develop` -> `dev`
- `staging` -> `staging`
- `main` -> `prod`

## What is still a scaffold

The deploy job currently documents intent but does not yet:

- build and publish images to GHCR
- inject environment secrets
- SSH into target hosts
- run `docker compose pull && docker compose up -d`

## Recommended next implementation slice

1. add GHCR login and image tagging by commit SHA
2. publish images for Odoo and PostgreSQL custom builds if needed
3. add GitHub environment secrets
4. add SSH deploy step per environment
5. add post-deploy health verification

## Documentation alignment

When the workflow changes, update:

- `README.md`
- `docs/architecture/platform-bootstrap.md`
- `docs/brain/platform_bootstrap_status.md`
- this runbook
