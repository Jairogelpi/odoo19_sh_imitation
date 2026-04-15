# Staging Neutralization

## Goal

Define the operational guardrails that make staging a safe copy of production instead of a second production environment.

## What the neutralization script does

The script at `ops/restore/staging-neutralize.sql` is applied automatically by `ops/restore/restore-to-staging.sh` after the database and filestore are restored.

It performs these actions:

- deactivates all existing outgoing mail servers
- reuses the highest-priority outgoing mail server, when present, and points it to `Mailpit`
- deactivates all inbound `fetchmail` servers
- deactivates all scheduled actions in `ir_cron`
- cancels queued outgoing rows in `mail_mail`
- marks queued SMS rows as errored on a best-effort basis when `sms_sms` exists
- writes `platform.staging_neutralized = true` into `ir_config_parameter`
- updates `web.base.url` to the staging URL when `STAGING_WEB_BASE_URL` is set

## What it does not try to do

This slice is intentionally limited to operational neutralization.

It does not yet:

- anonymize customer or employee data
- scrub API credentials stored in arbitrary module tables
- rewrite every custom webhook or external token across all addons

Those belong to a later data-sanitization slice.

## Supporting staging service

`compose.staging.yaml` now includes:

- `mailpit`

Operational access pattern:

- SMTP sink stays internal at `mailpit:1025`
- Mailpit UI is published only on `127.0.0.1:${STAGING_MAILPIT_UI_PORT:-8025}` on the staging host
- recommended access is via SSH tunnel rather than public exposure

Example:

```bash
ssh -L 8025:127.0.0.1:8025 user@staging-host
```

Then open:

```text
http://127.0.0.1:8025
```

## Required staging variables

- `STAGING_WEB_BASE_URL`
- `STAGING_MAILPIT_SMTP_HOST`
- `STAGING_MAILPIT_SMTP_PORT`
- `STAGING_MAILPIT_UI_PORT`
- `STAGING_ENV_FILE` when running the restore wrapper

## Operator checklist after restore

1. Confirm the expected staging database restored successfully.
2. Confirm `ir_cron` has no active rows.
3. Confirm `fetchmail_server` has no active rows.
4. Confirm the active outgoing mail server points to `mailpit:1025`.
5. Open the Mailpit UI through SSH tunnel and verify no real messages can leave the environment.
6. Only then reopen staging access.
