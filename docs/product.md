# Product specification

## Problem

When Odoo produces an unexpected business result, teams must reconstruct the
cause manually from logs, database records, automations, custom modules, and
human memory. Existing audit logs normally describe isolated mutations; they do
not prove the causal chain or provide a safe reproduction.

## Product outcome

A support engineer can select an affected record or trace and obtain:

1. an ordered, tamper-evident causal graph;
2. the initiating actor and trigger;
3. the relevant Odoo methods, automations, jobs, and external calls;
4. the records and field names changed;
5. the responsible module, source location, and Git revision when known;
6. a privacy-reviewed incident bundle;
7. a deterministic replay result in an isolated environment;
8. a generated regression-test draft after successful reproduction.

## Non-goals

- General-purpose Odoo hosting.
- Replacing Odoo.sh, OCA tooling, Sentry, or infrastructure observability.
- Recording every database value by default.
- Allowing an LLM to invent causal links.
- Automatically modifying production data.

## Initial actors

- **System administrator:** configures capture and retention.
- **Support engineer:** investigates and exports incidents.
- **Developer:** reproduces incidents and converts them into tests.
- **Auditor:** verifies evidence without changing it.

## Safety invariants

- Secret keys are never recorded, even with value capture enabled.
- Metadata-only capture is the default.
- A replay never targets a production database.
- External effects are denied during replay unless a test double is explicit.
- Trace events are append-only to ordinary users.
- Exported bundles declare their schema and verify their content hashes.
- Failure of the recorder must not corrupt or roll back the business transaction.

## First vertical slice

Given an instrumented `sale.order.action_confirm()` call, when a custom method
changes `sale.order.line.price_unit`, then Flight Recorder must:

- keep one correlation ID across the call chain;
- record method and ORM mutation events in order;
- capture field names but no price values by default;
- identify the custom addon and source location;
- export a deterministic, redacted bundle;
- verify the bundle without a running Odoo instance.

