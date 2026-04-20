---
name: grafana-advisor
description: "Use when you need Grafana dashboard, templating, alerting, or provisioning advice without turning Grafana into a second automation surface."
---

# Grafana Advisor

Curated repo-local adaptation of the ClawHub skill `grafana` for this repository.

Repo-local note for `odoo19_sh_imitation`:

- This vendored copy is advisory only.
- It does not connect to Grafana automatically.
- It does not write dashboards, data sources, or alerts automatically.
- Use it to review dashboards, variables, alerts, and provisioning choices for the local admin stack.

## Use for

- Reviewing panel query pitfalls before changing dashboards.
- Checking variable templating patterns and common mistakes.
- Stress-testing alerting assumptions and noisy rule design.
- Reviewing provisioning gotchas before editing Grafana config.
- Improving dashboard readability and operator ergonomics.

## Do not use for

- Treating it as an authenticated Grafana client.
- Auto-provisioning dashboards or alert rules without review.
- Bypassing repo docs or local admin runbooks.
- Turning observability advice into autonomous infrastructure changes.

## Practical guidance

- Keep dashboard variables cheap and predictable; badly scoped variables make every panel slower and harder to reason about.
- Avoid hiding bad PromQL behind aggressive panel transforms.
- Alert rules should be specific enough to page usefully, not merely to look active.
- Provisioning is safer when data sources, folders, and dashboards are treated as explicit config, not ad-hoc UI state.
- Prefer dashboards that answer one operational question well instead of mixing unrelated metrics on one screen.

## Local workflow fit

1. Use this skill when shaping or reviewing Grafana changes.
2. Cross-check observability guidance against the local admin stack docs and `prometheus`/`grafana` service notes.
3. Keep actual file edits, container changes, or provisioning updates explicit and reviewed.

## Examples

- "Why is this Grafana dashboard slow even though Prometheus itself looks healthy?"
- "Are these variables going to explode panel cost or operator confusion?"
- "Is this alert design actionable, or is it going to flap all day?"

## Provenance

- Upstream ClawHub slug: `grafana`
- Upstream title: `Grafana`
- Upstream author: `@ivangdavila`
- Upstream page: `https://clawhub.ai/skills/grafana`
- This repository keeps a curated, instruction-only adaptation under `.github/skills/grafana-advisor/`.
