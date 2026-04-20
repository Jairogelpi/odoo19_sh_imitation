# OpenClaw Advisory Skills

## Scope

This note records the low-risk advisory skills that were curated into this repository from ClawHub on 2026-04-18.

These skills are intentionally different from the repo's operational OpenClaw routes:

- they are instruction-only
- they do not request credentials
- they do not install software
- they do not create a second execution path around local approvals and runbooks

## Current curated advisory skills

### `postgresql-advisor`

Curated from the ClawHub skill `pg` by `@ivangdavila`.

Use it for:

- query review
- indexing patterns
- `EXPLAIN (ANALYZE, BUFFERS)` interpretation
- vacuum and bloat discussions
- timeout and pooling guidance

Do not use it to bypass [openclaw-db](../../.github/skills/openclaw-db/SKILL.md).

### `grafana-advisor`

Curated from the ClawHub skill `grafana` by `@ivangdavila`.

Use it for:

- dashboard review
- variable templating
- alert quality
- provisioning sanity checks

Do not treat it as an authenticated Grafana client or an auto-provisioning tool.

## Why these two fit

They fit this repository better than most third-party skills because:

- the platform already relies on PostgreSQL, `pgbackrest`, `prometheus`, and `grafana`
- both upstream skills are instruction-only and low-risk
- both add judgment and review value without expanding execution privileges

## Why they are not primary routes

The operational OpenClaw routes still come first:

- database execution: [openclaw-db](../../.github/skills/openclaw-db/SKILL.md)
- Odoo execution: [openclaw-odoo](../../.github/skills/openclaw-odoo/SKILL.md)
- docs/workspace/code actions: the corresponding local OpenClaw skills

These skills do not replace `openclaw-db` or any other primary local OpenClaw route.
The advisory skills should shape reviewed work, not replace the approved route.

## Provenance

- `postgresql-advisor` <= ClawHub `pg`: `https://clawhub.ai/ivangdavila/pg`
- `grafana-advisor` <= ClawHub `grafana`: `https://clawhub.ai/skills/grafana`
