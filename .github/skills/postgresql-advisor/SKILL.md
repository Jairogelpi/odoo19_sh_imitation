---
name: postgresql-advisor
description: "Use when you need PostgreSQL query, indexing, EXPLAIN, vacuum, or schema advice without bypassing OpenClaw DB workflows."
---

# PostgreSQL Advisor

Curated repo-local adaptation of the ClawHub skill `pg` for this repository.

Repo-local note for `odoo19_sh_imitation`:

- This vendored copy is advisory only.
- In this repository it is not the preferred operational path for database execution.
- The preferred operational route for database actions here is `openclaw-db`, with OpenClaw requests and approvals for risky work.
- Use this skill to improve the quality of reviewed PostgreSQL work, not to bypass `openclaw-db` or perform autonomous destructive DB changes.

## Use for

- Reviewing indexes before adding or dropping them.
- Interpreting `EXPLAIN (ANALYZE, BUFFERS)` output.
- Choosing query patterns such as `DISTINCT ON`, `IS NOT DISTINCT FROM`, or `FOR UPDATE SKIP LOCKED`.
- Checking connection-management defaults, timeouts, and pooling assumptions.
- Reasoning about vacuum, bloat, statistics freshness, and full-text search patterns.

## Do not use for

- Creating, duplicating, or dropping databases directly.
- Treating ad-hoc shell or `psql` access as pre-approved.
- Changing PostgreSQL config, extensions, or privileges without review.
- Replacing `openclaw-db` in the local OpenClaw routing model.

## Practical guidance

- Foreign-key columns are not auto-indexed in PostgreSQL; check join and cascade paths explicitly.
- Expression indexes such as `lower(email)` only help if the query matches the expression.
- Partial indexes can be much smaller when most rows are inactive or filtered out by a stable predicate.
- `EXPLAIN (ANALYZE, BUFFERS)` is the baseline for real diagnosis; estimate-only plans are often misleading.
- `TIMESTAMPTZ` is usually the correct timestamp type for application data.
- `SERIAL` is legacy; prefer identity columns on new schema work.
- Use `statement_timeout` and `idle_in_transaction_session_timeout` deliberately for safety.
- `VACUUM ANALYZE` matters after bulk loads because the planner depends on fresh statistics.

## Local workflow fit

1. If the task is operational, route it through `openclaw-db`.
2. If the task needs query or schema advice first, use this skill to shape the reviewed approach.
3. If a command must be run with `psql` or `pgcli`, keep it explicit, least-privileged, and reviewable.

## Optional local tools

- `psql`
- `pgcli`

These are optional operator tools, not part of the skill itself.

## Examples

- "Review this `EXPLAIN` plan and tell me whether the index is wrong or the stats are stale."
- "Should this Odoo-side reporting query use `DISTINCT ON` or a window function?"
- "What timeout and pooling defaults should we revisit before opening more admin tooling?"

## Provenance

- Upstream ClawHub slug: `pg`
- Upstream title: `PostgreSQL`
- Upstream author: `@ivangdavila`
- Upstream page: `https://clawhub.ai/ivangdavila/pg`
- This repository keeps a curated, instruction-only adaptation under `.github/skills/postgresql-advisor/`.
