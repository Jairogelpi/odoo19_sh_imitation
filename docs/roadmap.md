# Roadmap

## R0 — Clean foundation

- Minimal Odoo 19 addon.
- Stable framework-independent event envelope.
- Privacy-first redaction.
- Repository hygiene and CI.

## R1 — One proven causal trace

- Request correlation context.
- Instrument one explicit sale-order flow without global monkey-patching.
- Ordered method and ORM events.
- Source module and Git revision attribution.
- Odoo integration tests.

## R2 — Incident bundle

- Versioned `.odoo-incident` manifest.
- Canonical hashes and offline verification.
- Configurable field allowlists.
- Minimal, anonymized fixtures.
- GitHub issue attachment workflow.

## R3 — Safe replay

- Disposable Odoo environment.
- Denied email, payment, cron, and external HTTP effects.
- Bundle import and deterministic replay.
- Original-versus-replay event comparison.

## R4 — Regression generation

- Generate a reviewable `TransactionCase` draft.
- Run it against the faulty revision and proposed fix.
- Attach evidence to pull requests.

## R5 — Golden business flows

- Community-maintained flow format.
- Behavior comparison between Odoo revisions.
- Performance and compatibility benchmarks.

