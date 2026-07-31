# Architecture

## Boundary

The product has four components. R3 implements the first replay worker for the
sale-confirmation vertical slice.

```text
Odoo addon -> event envelope -> incident bundle -> isolated replay worker
```

### Odoo addon

Owns correlation context, Odoo-aware instrumentation, access control, retention,
and the trace/event records. It must not contain hosting or AI orchestration.

### Recorder core

Owns versioned event schemas, canonical serialization, hashes, and redaction.
It has no Odoo dependency so evidence can be verified independently.

### Incident bundle

Will own export/import, manifest hashes, minimal fixtures, reproduction steps,
and compatibility metadata. The proposed extension is `.odoo-incident`.

### Replay worker

Will create an isolated Odoo environment, restore sanitized minimal state,
disable side effects, execute the reproduction, and compare observed events.
The earlier platform code is intentionally not retained; replay infrastructure
will be rebuilt only when its contract is proven.

## Capture policy

Capture is tiered:

1. **Metadata:** event type, model, record ID, field names, source, duration.
2. **Hashed values:** equality/change evidence without exposing content.
3. **Allowlisted values:** explicit per-model and per-field configuration.

Known secrets are denied at every tier.

## Causality

Every event belongs to a trace and may reference one parent event. Sequence
numbers provide stable ordering within a trace. Causal propagation across
requests, jobs, and integrations will use an explicit context carrier rather
than inference from timestamps.

## Performance budget

The recorder will ship disabled. The initial target is:

- below 5% p95 request-latency overhead in metadata mode;
- bounded queue and storage growth;
- fail-open for capture infrastructure while preserving an explicit health
  signal that evidence is incomplete.

These are targets, not current claims.
