# Delivery

## Purpose

This note tracks how code is expected to move from local work to production.

## Main references

- [Environments and promotions](../runbooks/environments-and-promotions.md)
- [CI/CD scaffold](../runbooks/ci-cd-scaffold.md)
- [Platform bootstrap status](platform_bootstrap_status.md)

## Current delivery shape

- `feature/*` for isolated work
- `develop` for dev promotion
- `staging` for preproduction validation
- `main` for production

## Current reality

- validation workflow exists
- deploy workflow is still a scaffold
- documentation already reflects the intended branch-to-environment model
