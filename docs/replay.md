# Safe replay

R3 replays a verified `.odoo-incident` in a disposable Odoo 19 environment and
compares the original causal signature with the observed signature.

```bash
python tools/replay_incident.py incident.odoo-incident \
  --output replay-report.json
```

## Safety boundary

The runner creates a unique Docker Compose project for every invocation:

- PostgreSQL and Odoo use fresh named volumes;
- the project network is `internal`, so containers have no internet egress;
- Odoo starts with `--max-cron-threads 0`;
- the replay service requires `FLIGHT_RECORDER_REPLAY_ISOLATED=1`;
- the database name must start with `flight_recorder_replay_`;
- Compose containers, networks, and volumes are removed in `finally` cleanup.

This denies external HTTP, email delivery, and payment-provider calls at the
network boundary. Internal records created during replay are discarded with the
database. The runner never connects to an existing Odoo database.

## Current adapter

R3 supports incidents whose root action is
`sale.order.action_confirm()`. It creates deterministic synthetic customer,
product, and quotation records; it does not restore production values.

Comparison includes:

- event sequence and parent sequence;
- event kind;
- model and operation;
- changed field names.

It intentionally ignores record IDs, archive-local references, timestamps,
hashes, and generated correlation IDs. A mismatch produces exit code `2` and a
position-by-position difference list. Invalid evidence or worker failure returns
exit code `1`.

## Limitations

- R3 proves behavioral shape, not equality of undisclosed business values.
- Only the sale-confirmation adapter exists today.
- Docker isolation is required; direct replay inside an ordinary Odoo process is
  rejected.
- OS-level sandboxing beyond Docker remains the operator's responsibility.
