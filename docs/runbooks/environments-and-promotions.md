# Environments and Promotions

## Environment model

This platform is designed around one Docker host per environment.

Target environments:

- `dev`
- `staging`
- `prod`

## Compose layer mapping

- `compose.yaml` + `compose.dev.yaml` -> local development
- `compose.yaml` + `compose.staging.yaml` -> staging
- `compose.yaml` + `compose.prod.yaml` -> production
- `compose.admin.yaml` -> optional admin and knowledge services where appropriate

## Branch model

- `develop` -> development deployment target
- `staging` -> staging deployment target
- `main` -> production deployment target
- `feature/*` -> short-lived feature branches

## Promotion model

Recommended path:

1. work on `feature/*`
2. merge into `develop`
3. validate in `dev`
4. merge into `staging`
5. validate in `staging`
6. merge into `main`
7. deploy to `prod`

## Runtime expectations by environment

### Development

- easiest local startup
- direct Odoo port exposed
- Nginx available for parity checks
- admin and knowledge layer allowed

### Staging

- production-like edge exposure
- production-like Odoo config
- must become a neutralized copy of production
- uses `Mailpit` as the default SMTP sink after restore neutralization
- should not depend on admin services to operate

### Production

- production-like edge exposure
- no optional admin/knowledge services in the critical path
- strict secrets and backup discipline
- offsite backup replication should be part of normal production operations

## Remaining gaps

- first-time server bootstrap automation
- automated restore drills from offsite copies
- data anonymization beyond operational neutralization
