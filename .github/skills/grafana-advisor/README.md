# grafana-advisor

Curated repo-local adaptation of the ClawHub `grafana` skill for this repository.

## Why it exists here

This repo already ships a local observability stack with `prometheus` and `grafana`.

`grafana-advisor` exists to help with:

- dashboard review
- variable templating
- alert design
- provisioning sanity checks

without introducing a second authenticated automation path to Grafana.

## Local contract

- Advisory only
- No credentials required by the skill itself
- No installs
- No automatic writes to Grafana

## Good fit in this stack

The local admin layer exposes Grafana as an operator-facing dashboard UI, so low-risk advice is useful before changing:

- dashboards
- alert rules
- provisioning files
- panel/variable design

## Provenance

- ClawHub slug: `grafana`
- ClawHub page: `https://clawhub.ai/skills/grafana`
- Upstream version reviewed for this curation: `1.0.0`

## Local rule

Use this skill for judgment and review.
Keep actual observability edits explicit in the repository and aligned with the local runbooks.
