# Roadmap

## R0 — Clean foundation

- Minimal Odoo 19 addon.
- Stable framework-independent event envelope.
- Privacy-first redaction.
- Repository hygiene and CI.

## R1 — One proven causal trace

- [x] Request correlation context.
- [x] Instrument one explicit sale-order flow without global monkey-patching.
- [x] Ordered method and ORM events.
- [x] Source module and Git revision attribution.
- [x] Odoo integration tests.

R1 records the explicit `sale.order.action_confirm()` boundary. It compares the
order state and sale-line price in memory, then emits metadata-only mutation
events for fields that changed. It does not intercept global ORM methods.

## R2 — Incident bundle

- [x] Versioned `.odoo-incident` manifest.
- [x] Canonical hashes and offline verification.
- [x] Configurable field allowlists.
- [x] Minimal, anonymized fixtures.
- [x] GitHub issue attachment workflow.

R2 exports completed traces from the administrator interface. The deterministic
archive replaces database IDs with archive-local references, seals every event
and document, and can be verified without importing Odoo. Capture policies
reject unknown models, fields, and secret-like field names.

## R3 — Safe replay

- [x] Disposable Odoo environment.
- [x] Denied email, payment, cron, and external HTTP effects.
- [x] Bundle import and deterministic replay.
- [x] Original-versus-replay event comparison.

R3 runs each replay in a new Compose project and database. The Docker network is
internal, cron workers are disabled, and all volumes are destroyed afterward.
The first replay adapter creates synthetic sale data, confirms the order, and
compares causal signatures while ignoring database IDs, timestamps, and hashes.

## R4 — Regression generation

- Generate a reviewable `TransactionCase` draft.
- Run it against the faulty revision and proposed fix.
- Attach evidence to pull requests.

## R5 — Golden business flows

- Community-maintained flow format.
- Behavior comparison between Odoo revisions.
- Performance and compatibility benchmarks.
