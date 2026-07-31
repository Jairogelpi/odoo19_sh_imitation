<div align="center">

# Flight Recorder for Odoo

### See why Odoo did it. Reproduce it. Prevent it.

**An evidence-first flight recorder for Odoo incidents: causal traces, privacy-safe incident bundles, deterministic replay, and regression-test generation.**

[![CI](https://github.com/Jairogelpi/odoo_flight_recorder/actions/workflows/ci.yml/badge.svg)](https://github.com/Jairogelpi/odoo_flight_recorder/actions/workflows/ci.yml)
[![Odoo](https://img.shields.io/badge/Odoo-19.0-714B67)](https://www.odoo.com/)
[![License](https://img.shields.io/badge/license-AGPL--3.0--or--later-blue)](LICENSE)
[![Status](https://img.shields.io/badge/status-foundation-orange)](#project-status)

[Quick start](#quick-start) · [Why this exists](#why-this-exists) · [Architecture](#architecture) · [Roadmap](docs/roadmap.md) · [Contributing](CONTRIBUTING.md)

</div>

---

> [!IMPORTANT]
> Flight Recorder is under active development. The Odoo 19 sale-confirmation trace and verifiable incident export are real and tested. Generalized instrumentation, replay, and test generation remain roadmap work and are not presented as finished features.

## Why this exists

An Odoo record is rarely changed by just one line of code. A user click can trigger inherited methods, automated actions, computed fields, cron jobs, integrations, and dozens of ORM mutations. When the final business result is wrong, ordinary logs often tell you **that** something happened—not the complete, provable chain of **why**.

Today, investigating a difficult incident often looks like this:

```text
unexpected invoice / price / stock move
        ↓
search application logs
        ↓
inspect automated actions and custom addons
        ↓
compare database records
        ↓
ask who clicked what
        ↓
attempt to reproduce it manually
        ↓
hope the proposed fix covers the real cause
```

Flight Recorder is designed to turn that investigation into an evidence pipeline:

```text
business action
    → correlated causal trace
    → ordered ORM and method events
    → privacy-reviewed incident bundle
    → isolated deterministic replay
    → reviewable regression test
```

The goal is not “more logging.” The goal is to make an Odoo incident **explainable, reproducible, and preventable**.

## The four-question product contract

For every captured incident, Flight Recorder aims to answer:

1. **What changed?** Models, records, fields, timing, and transaction outcome.
2. **Why did it change?** Initiating actor, trigger, method chain, automation, job, or integration.
3. **Can it be reproduced safely?** In an isolated environment with external side effects denied.
4. **Can it become a regression test?** As reviewable Odoo test code tied to the evidence.

AI may summarize the evidence or propose a fix. It is never the source of truth for event order, causality, hashes, or replay results.

## A concrete example

Imagine that confirming a quotation unexpectedly replaces a negotiated line price.

A completed Flight Recorder investigation will be able to show evidence like:

```text
Trace 01J...
└── HTTP: confirm quotation SO042
    └── sale.order.action_confirm()
        └── custom_pricing.sale_order._apply_contract_price()
            └── ORM write
                ├── model: sale.order.line
                ├── record: 731
                ├── fields: [price_unit]
                ├── values: redacted
                └── source: custom_pricing/models/sale_order.py:84
```

The exported incident can then be replayed against the faulty revision and a proposed fix. Only a matching causal outcome counts as reproduction.

## Quick start

### Requirements

- Git
- Docker with Compose v2
- Approximately 2 GB of free memory for the local Odoo/PostgreSQL stack

### 1. Clone and configure

```bash
git clone https://github.com/Jairogelpi/odoo_flight_recorder.git
cd odoo_flight_recorder
cp .env.example .env
```

PowerShell:

```powershell
git clone https://github.com/Jairogelpi/odoo_flight_recorder.git
Set-Location odoo_flight_recorder
Copy-Item .env.example .env
```

### 2. Install the addon into a clean Odoo 19 database

```bash
docker compose up -d --wait db
docker compose run --rm odoo odoo \
  --database flight_recorder \
  --init flight_recorder \
  --stop-after-init \
  --no-http \
  --without-demo all
```

### 3. Start Odoo

```bash
docker compose up -d
```

Open <http://127.0.0.1:8069>.

The stack uses the official `odoo:19.0` image and PostgreSQL 16. It binds Odoo only to localhost and is intended for development—not production.

For Odoo.sh, an existing source installation, upgrades, troubleshooting, and cleanup, read the complete **[installation guide](docs/installation.md)**.

### Export and verify an incident

Confirm a quotation, then open **Flight Recorder → Traces** as a system
administrator. Open the completed trace and select **Export Incident**.

```bash
python tools/verify_incident.py path/to/downloaded.odoo-incident
```

The verifier runs without Odoo and fails closed if the archive, causal ordering,
or any sealed event has changed. See the [incident format](docs/incident-format.md).

Replay it inside a disposable, network-isolated Odoo 19 stack:

```bash
python tools/replay_incident.py path/to/downloaded.odoo-incident \
  --output replay-report.json
```

See the [safe replay contract](docs/replay.md).

## What is available today?

| Capability | Status | Evidence |
|---|---:|---|
| Installable Odoo 19 addon | ✅ Ready | Installed in a clean official Odoo 19 container in CI |
| Admin-only trace and event models | ✅ Ready | ACLs restrict access to system administrators |
| Deterministic event envelope | ✅ Ready | Canonical JSON and SHA-256 content hashing |
| Recursive privacy redaction | ✅ Ready | Secret denylist plus metadata-first policy |
| Repository hygiene guard | ✅ Ready | Rejects caches, environments, archives, weights, and oversized files |
| Explicit sale-confirmation causal trace | ✅ Ready | R1 |
| Generalized request/ORM instrumentation | 🧭 Planned | Future vertical slices |
| Versioned `.odoo-incident` bundles | ✅ Ready | R2 |
| Offline integrity and causality verification | ✅ Ready | R2 |
| Anonymized minimal fixtures | ✅ Ready | R2 |
| Side-effect-safe isolated replay | ✅ Ready | R3 sale-confirmation adapter |
| Odoo regression-test generation | 🧭 Planned | R4 |
| Cross-version behavior comparison | 🧭 Planned | R5 |

This explicit status table is part of the project contract: claims must be backed by executable evidence.

## Architecture

```text
┌──────────────────────────── Odoo ────────────────────────────┐
│ user action · RPC · cron · automation · integration          │
│                           │                                   │
│                 correlation + capture                         │
└───────────────────────────┬───────────────────────────────────┘
                            ▼
                 versioned event envelope
                 canonical JSON · hashes
                            │
                            ▼
                  privacy policy + redaction
                            │
                            ▼
                    .odoo-incident bundle
                            │
                            ▼
              isolated replay worker (side effects denied)
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
          behavior comparison    regression-test draft
```

The repository deliberately separates Odoo-aware capture from framework-independent evidence primitives:

```text
addons/flight_recorder/        Odoo 19 integration and security
src/odoo_flight_recorder/      schemas, canonicalization, hashing, redaction
tests/                         unit and repository-contract tests
docs/                          product, architecture, installation, roadmap
tools/                         development and hygiene checks
compose.yaml                   disposable Odoo 19 development environment
```

Read the deeper [architecture notes](docs/architecture.md) and [product specification](docs/product.md).

## Safety by design

Flight Recorder may observe highly sensitive business operations, so data minimization is not an optional feature.

- Metadata-only capture is the default.
- Known secrets are denied even when value capture is enabled.
- Business values require explicit model/field allowlists.
- Ordinary users cannot rewrite or delete trace events.
- Replay must never target a production database.
- Email, payment, cron, and external HTTP effects are denied during replay unless an explicit test double exists.
- Recorder failure must not corrupt or roll back the business transaction.
- Incident bundles are treated as sensitive artifacts and verify their own content hashes.

See [SECURITY.md](SECURITY.md) before using real business data.

## Compatibility

| Target | Current position |
|---|---|
| Odoo 19 Community | Primary tested target |
| Odoo 19 Enterprise | Designed to be compatible; integration coverage will expand |
| Odoo.sh | Addon layout supported; validate first on a staging branch |
| On-premise / Docker | Supported development path |
| Odoo 18 and earlier | Not currently supported |
| Production capture | Not ready yet |

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
python tools/check_repository_hygiene.py
```

The CI pipeline runs those checks and installs the addon into a new Odoo 19 database. A change that only compiles locally is not considered verified.

## Design principles

- **Evidence before interpretation.** Causal links are recorded, not guessed.
- **Privacy before convenience.** Capture the minimum needed to reproduce behavior.
- **Odoo-native boundaries.** Prefer supported extension points over global monkey-patching.
- **Determinism before spectacle.** Reproduction must be comparable and hashable.
- **Failure isolation.** Observability must not break the business transaction.
- **Measurable overhead.** Metadata mode targets less than 5% p95 request-latency overhead; this is a target until benchmarked.
- **No mandatory cloud or LLM.** Core evidence remains locally verifiable.
- **No untested claims.** Product status is tied to tests, installation, or benchmarks.

## Roadmap

The project advances through vertical slices instead of broad, unverified instrumentation:

- **R0 — Foundation:** addon, event envelope, redaction, CI. ✅
- **R1 — One proven causal trace:** explicit sale-order flow, correlation, source attribution. ✅
- **R2 — Incident bundle:** portable schema, hashes, anonymized fixtures, offline verification. ✅
- **R3 — Safe replay:** disposable Odoo, denied external effects, deterministic comparison. ✅
- **R4 — Regression generation:** produce and execute a reviewable `TransactionCase`.
- **R5 — Golden business flows:** community-owned behavior contracts across revisions.

See the detailed [roadmap](docs/roadmap.md).

## Contributing

The most valuable contributions are real, sanitized Odoo failure scenarios that can become reproducible fixtures.

Before opening a pull request:

1. Describe the business incident and observable wrong outcome.
2. Define the privacy boundary and expected failure behavior.
3. Add the failing test first.
4. Keep instrumentation scoped to a supported Odoo series.
5. Run the full quality suite and clean-database installation.

Read [CONTRIBUTING.md](CONTRIBUTING.md). Security problems should be reported privately as described in [SECURITY.md](SECURITY.md).

## Project status

Flight Recorder is currently an **installable technical preview**, not a production observability product. R1 traces sale-order confirmation, R2 exports independently verifiable evidence, and R3 replays that evidence in an isolated Odoo environment. The next milestone is generating a reviewable regression test.

If that problem matters to you, star the repository, open a scenario discussion, or contribute a sanitized incident contract.

## License

GNU Affero General Public License v3.0 or later. See [LICENSE](LICENSE).

---

<div align="center">

Built to make the hardest Odoo incidents explainable—not merely logged.

</div>
