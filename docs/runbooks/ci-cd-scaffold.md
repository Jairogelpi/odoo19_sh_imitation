# CI/CD Pipeline

## Current state

The repository now includes an active workflow in:

- `.github/workflows/platform-ci.yml`

## What it does now

On push to `develop`, `staging`, or `main`, and on pull requests:

- checks out the repository
- validates `compose.yaml` with `dev`, `staging`, and `prod` overrides
- syntax-checks critical shell and PowerShell scripts
- runs scaffold contract tests for docs and configuration alignment
- builds the custom PostgreSQL, pgBackRest, and Odoo images

On push events it also:

- publishes the custom images to GHCR
- maps branches to deployment environments
- deploys over SSH using GitHub Environment secrets

Branch mapping:

- `develop` -> `dev`
- `staging` -> `staging`
- `main` -> `prod`

## Workflow shape

The pipeline is now split into:

1. `validate`
2. `publish_images`
3. `deploy`

The deploy job uses:

- pinned GitHub Environments per target
- GHCR image tags based on commit SHA
- an SSH key and pinned `known_hosts`
- `ops/deploy/remote-deploy.sh` on the target server
- an optional post-deploy HTTP health check

## Required companion runbook

The operational details live in:

- `docs/runbooks/deployment-over-ssh.md`
- `docs/runbooks/runtime-validation.md`

## Remaining gaps

- automated end-to-end staging restore drills against a real backup set
- live deploy verification against a real remote target
- environment bootstrap automation for first-time server provisioning

## Documentation alignment

When the workflow changes, update:

- `README.md`
- `docs/architecture/platform-bootstrap.md`
- `docs/brain/platform_bootstrap_status.md`
- `docs/brain/delivery.md`
- this runbook
