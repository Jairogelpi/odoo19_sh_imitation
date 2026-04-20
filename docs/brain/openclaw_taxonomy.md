# OpenClaw Skill Taxonomy

## Official Hierarchy

1. `openclaw-core`
2. `openclaw-router`
3. Domain skills
   - `openclaw-crm-contacts`
   - `openclaw-crm-opportunities`
   - `openclaw-sales`
   - `openclaw-inventory`
   - `openclaw-invoicing`
   - `openclaw-purchase`
   - `openclaw-hr`
   - `openclaw-reporting`
   - `openclaw-odoo`

## Auxiliary process skills

These do not participate in business-domain routing, but they are part of the local OpenClaw skill catalog:

- `skill-vetter` for reviewing third-party skills before import
- `self-improvement` for durable learning/error capture through the vendored repo-local copy; optional hooks remain opt-in
- `ontology` for optional local knowledge graphs; it remains non-authoritative and outside the main Odoo/OpenClaw memory path

## Auxiliary advisory skills

These are low-risk judgment aids, not execution routes:

- `postgresql-advisor` for PostgreSQL query/index/plan/tuning review; it does not replace `openclaw-db`
- `grafana-advisor` for dashboard, templating, alerting, and provisioning review; it does not turn Grafana into an automated write surface

## Design Rules

- `openclaw-core` owns policy, permissions, and routing conventions.
- `openclaw-router` classifies user intent and selects the domain skill.
- Domain skills contain only domain-specific business logic.
- `openclaw-odoo` is the fallback for generic Odoo operations.
- `openclaw-odoo` is also the only preferred operational path for Odoo execution in this repo; third-party Odoo skills are reference material unless they are explicitly curated into the request/policy flow.
- Chat should always route through the taxonomy before falling back to the general LLM reply.

## Why This Matters

This keeps OpenClaw predictable:
- one skill per domain
- simpler policy allowlists
- clearer approvals
- lower coupling in the chat flow
- safer execution paths

## Chat Routing

When the user writes a message in OpenClaw Chat:

1. The router classifies the intent.
2. The router selects the skill family.
3. The skill returns suggested actions or a clarification request.
4. The request is approved and executed through the policy layer.

## Related Files

- [OpenClaw Chat](openclaw.md)
- [OpenClaw Advisory Skills](openclaw_advisory_skills.md)
- [Third-Party Odoo Skills](openclaw_third_party_odoo_skills.md)
- [OpenClaw Request Cycle](openclaw_request_cycle.md)
- [OpenClaw Tool Catalog](openclaw_tools.md)
- [OpenClaw Core Skill](../../.github/skills/openclaw-core/SKILL.md)
- [OpenClaw Router Skill](../../.github/skills/openclaw-router/SKILL.md)
