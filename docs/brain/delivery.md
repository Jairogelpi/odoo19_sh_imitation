# Delivery

## Purpose

This note tracks how code is expected to move from local work to production.

## Main references

- [Environments and promotions](../runbooks/environments-and-promotions.md)
- [Secrets and configuration](../runbooks/secrets-and-config.md)
- [CI/CD scaffold](../runbooks/ci-cd-scaffold.md)
- [Deployment over SSH](../runbooks/deployment-over-ssh.md)
- [Platform bootstrap status](platform_bootstrap_status.md)

## Current delivery shape

- `feature/*` for isolated work
- `develop` for dev promotion
- `staging` for preproduction validation
- `main` for production

## Current reality

- validation, GHCR publish, and SSH deploy are now wired in the GitHub Actions workflow
- the remote host is expected to keep a checked-out copy of this repository plus a server-side env file
- deploys use immutable GHCR image tags based on the commit SHA
- documentation now reflects the implemented branch-to-environment model
- staging restore is now part of the delivery story because preproduction should be rebuilt as a neutralized production copy when needed
