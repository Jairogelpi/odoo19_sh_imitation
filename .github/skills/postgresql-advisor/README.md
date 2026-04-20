# postgresql-advisor

Curated repo-local adaptation of the ClawHub `pg` skill for this repository.

## Why it exists here

This repo already has an operational database route: [openclaw-db](../openclaw-db/SKILL.md).

`postgresql-advisor` exists to improve technical judgment around PostgreSQL work without creating a second execution path.

- It is advisory only.
- It does not ask for credentials.
- It does not install software.
- It does not replace `openclaw-db`.

## Good fit in this stack

The local platform depends on PostgreSQL, `pgbackrest`, and Odoo reporting/query behavior, so low-risk database guidance is useful for:

- query review
- index design
- `EXPLAIN` interpretation
- timeout and pooling defaults
- vacuum and bloat discussions

## Runtime assumptions

- Optional local binaries: `psql`, `pgcli`
- No bundled code
- No automatic network access
- No automatic writes outside the repository

## Provenance

- ClawHub slug: `pg`
- ClawHub page: `https://clawhub.ai/ivangdavila/pg`
- Upstream version reviewed for this curation: `1.0.0`

## Local rule

If the task is advice, this skill fits.
If the task is execution, route it through [openclaw-db](../openclaw-db/SKILL.md) and keep risky actions reviewed.
