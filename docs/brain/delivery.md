# Delivery

## Purpose

This note tracks how code is expected to move from local work to production.

It is the delivery layer of the platform, the piece that turns this stack into a repeatable Odoo.sh-style deployment flow.

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

## Delivery layers

### Source control
- Git is the source of truth for runtime config, compose files, docs, and scripts.
- Changes that matter should exist in the repository, not only in Portainer.

### CI/CD
- GitHub Actions validates compose.
- GitHub Actions builds and publishes the custom images.
- GitHub Actions deploys through SSH using immutable GHCR tags.

### Environments
- development is for local iteration and fast feedback
- staging is for neutralized production-like validation
- production is for the live runtime

### Promotion flow
- work starts on `feature/*`
- changes merge to `develop` for integration
- validated changes promote to `staging`
- approved changes reach `main` and production delivery

### Operational follow-up
- staging restore and neutralization are part of the delivery process
- offsite backup replication is the operational follow-up for production delivery

## Current reality

- validation, GHCR publish, and SSH deploy are now wired in the GitHub Actions workflow
- the remote host is expected to keep a checked-out copy of this repository plus a server-side env file
- deploys use immutable GHCR image tags based on the commit SHA
- documentation now reflects the implemented branch-to-environment model
- staging restore is now part of the delivery story because preproduction should be rebuilt as a neutralized production copy when needed
- production delivery now also includes offsite replication of backup artifacts as an operational follow-up step

## Related notes
- [Platform](platform.md)
- [Platform Bootstrap Status](platform_bootstrap_status.md)
- [Stack Topology](stack_topology.md)
- [Service Map](../architecture/service-map.md)
- [Environments and promotions](../runbooks/environments-and-promotions.md)
- [CI/CD scaffold](../runbooks/ci-cd-scaffold.md)
- [Deployment over SSH](../runbooks/deployment-over-ssh.md)
