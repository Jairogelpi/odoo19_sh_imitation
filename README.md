# Flight Recorder for Odoo

**See why Odoo did it. Reproduce it. Prevent it.**

Flight Recorder for Odoo is an open-source observability and incident-reproduction
tool for Odoo. Its goal is to connect a business outcome to the complete causal
chain that produced it:

```text
user action
  -> Odoo method
  -> automation / cron / integration
  -> ORM mutations
  -> affected business documents
  -> module, source location, and Git revision
```

This repository is being rebuilt from an earlier self-hosted Odoo platform
experiment. The infrastructure is no longer the product. Disposable Odoo
environments will be used only to reproduce incidents and verify fixes.

## Product contract

Flight Recorder must eventually answer four questions with evidence:

1. **What changed?**
2. **Why did it change?**
3. **Can the same behavior be reproduced safely?**
4. **Can the incident become a regression test?**

The recorder is evidence-first. AI may summarize or propose a fix, but it is
never the source of truth for events, causality, hashes, or replay results.

## Current status

This is the clean foundation, not a production release.

Implemented:

- a minimal Odoo 19 addon with admin-only trace and event models;
- a framework-independent event envelope with deterministic hashing;
- privacy-first recursive redaction;
- a minimal local Odoo/PostgreSQL development stack;
- CI installation of the addon in a clean Odoo 19 database;
- repository-hygiene tests that reject caches, virtual environments, model
  weights, archives, and oversized files.

Not implemented yet:

- automatic ORM/request instrumentation;
- causal parent propagation;
- incident bundle export/import;
- sanitized sandbox replay;
- conversion of a reproduced incident into an Odoo test;
- comparison of behavior between Git revisions.

See [Product specification](docs/product.md), [Architecture](docs/architecture.md),
and [Roadmap](docs/roadmap.md).

## Repository layout

```text
addons/flight_recorder/        Odoo 19 addon
src/odoo_flight_recorder/      framework-independent recorder primitives
tests/                         fast unit and repository-contract tests
docs/                          product and architecture decisions
tools/                         development and hygiene checks
compose.yaml                   minimal local Odoo 19 environment
```

## Development

Python checks:

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

Local Odoo 19:

```bash
cp .env.example .env
docker compose up -d
```

Then open <http://127.0.0.1:8069>, create a development database, refresh the
Apps list, and install **Flight Recorder**.

The compose stack is development-only. Its example credentials and exposed port
must not be reused for production.

## Principles

- Odoo Community and Enterprise compatible.
- No mandatory LLM, SaaS, or external telemetry service.
- Metadata-only capture by default.
- Explicit allowlists before recording business values.
- Deterministic and tamper-evident incident artifacts.
- Measured overhead with a defined performance budget.
- No monkey-patching of Odoo core without a versioned compatibility contract.
- Every product claim backed by a reproducible test or benchmark.

## License

The project is licensed under the GNU Affero General Public License v3.0 or
later. See [LICENSE](LICENSE).
