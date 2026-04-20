# Third-Party Odoo Skills for OpenClaw

## Scope

This note records the repository-specific stance taken on 2026-04-18 for third-party Odoo skills discovered on ClawHub.

It answers a narrower question than "is this skill useful in general?":

- Does it fit the OpenClaw execution model used in this repository?
- Does it respect the request, policy, approval, and gateway flow?
- Can it be trusted as an operational path, or only mined for ideas?

## Current stance

For this repository, the preferred operational path for Odoo actions remains [openclaw-odoo](../../.github/skills/openclaw-odoo/SKILL.md).

Third-party Odoo skills may still be useful, but only under these rules:

- Read-only or reporting patterns can be reused as ideas and later curated into repo-local skills.
- Skills that perform direct XML-RPC `create`, `write`, `unlink`, or auto-create dependencies should not become the primary execution path here.
- Anything that bypasses OpenClaw requests, policy allowlists, or approval checks does not fit the current addon contract.

## Repository contract behind this decision

The local OpenClaw addon is not just a generic Odoo helper. It is the permissioned execution layer for the platform.

- [openclaw.md](openclaw.md) defines OpenClaw as the layer between user intent and risky actions.
- [openclaw.md](openclaw.md) also documents that approved requests are executed through the gateway.
- [OpenClaw Request Cycle](openclaw_request_cycle.md) describes the request lifecycle.
- [openclaw-odoo](../../.github/skills/openclaw-odoo/SKILL.md) says Odoo ORM work should become an `openclaw.execute_request` payload.

That means "works with Odoo" is not enough. A skill must also fit the local control model.

## Evaluated skills

| Skill | Repo fit | Notes |
| --- | --- | --- |
| `Odoo Reporting` by `@ashrf-in` | Partial, reference only | The read-only reporting direction is useful, but the package metadata, credential declaration, and invocation policy are inconsistent enough that it should not be trusted as-is with production credentials. |
| `Openclaw Skill for Odoo` by `@nullnaveen` | No direct fit | It is a duplicate of the `odoo-erp-connector` family and exposes a broad direct XML-RPC write path, smart auto-create flows, a webhook server, and a poller. That conflicts with the local request and approval flow. |
| `Clawhub Package Full` by `@nullnaveen` | No direct fit | This appears to be the same package family as `odoo-erp-connector`, so it has the same mismatch with the local OpenClaw model. |
| `Odoo Manager` by `@willykinfoussia` | No direct fit | Generic CRUD over any model through XML-RPC is powerful but too direct for this repository, especially with dynamic URL and database switching. |
| `Odoo` by `@ivangdavila` | Limited, reference only | The instruction-only workflow is safer and pushes read-before-write habits, but it still sits outside the OpenClaw policy layer and persists its own memory under `~/odoo/`. |

## What stays true inside this repo

- `.github/skills/odoo-erp-connector/` remains in the repository as imported third-party material for inspection, comparison, and possible selective reuse.
- Its presence in the tree does not make it the preferred production route.
- The production route for Odoo execution remains the request-based path documented in [openclaw.md](openclaw.md).

## Practical rule

When evaluating future Odoo skills, use this filter:

1. If the skill bypasses `openclaw.execute_request`, it is not the preferred operational path.
2. If the skill performs direct writes or auto-creates records outside the request/approval flow, treat it as a mismatch.
3. If the skill is read-only and genuinely valuable, curate the useful parts into a repo-local note or skill instead of installing it verbatim.
