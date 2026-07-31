# `.odoo-incident` format

An `.odoo-incident` file is a deterministic ZIP archive that can be verified
without an Odoo server. Format version 1 contains exactly three canonical JSON
documents:

```text
manifest.json
events.json
fixtures.json
```

## Trust model

`manifest.json` declares the schema version, incident identifier, counts, exact
byte sizes, and SHA-256 digest of the events and fixtures documents. Every event
also contains an `evidence_hash` over its canonical representation.

Verification fails closed when:

- an archive member is missing, duplicated, additional, compressed, or too large;
- JSON is not canonical UTF-8;
- a file size or digest differs from the manifest;
- event sequences are not contiguous;
- a parent event does not precede its child;
- an event references a fixture that does not exist;
- an individual event seal has changed.

The archive proves integrity after export. It does not provide authenticity or
non-repudiation yet; signed manifests belong to a future format version.

## Anonymization

Database record IDs are never exported. Each `(model, record ID)` pair becomes
a deterministic archive-local reference such as `record-0001`. Version 1
fixtures contain the model and an empty field mapping. Business values remain
absent unless a future capture mode explicitly allows and sanitizes them.

User identities are reduced to `actor_type: odoo_user`; user IDs, names, emails,
sessions, credentials, and tokens are not exported.

## Offline verification

```bash
python tools/verify_incident.py path/to/trace.odoo-incident
```

Success prints:

```text
VERIFIED incident=<id> events=<count> fixtures=<count> schema=1
```

Any structural, causal, or hash failure returns exit code 1 and starts its
message with `INVALID`.

## Creating an archive in Odoo

1. Sign in as a system administrator.
2. Open **Flight Recorder → Traces**.
3. Open a completed trace.
4. Select **Export Incident**.
5. Verify the downloaded file before sharing it.

Exports are stored as Odoo attachments linked to the trace so administrators
can audit when evidence was produced.

## Sharing through GitHub

Only attach sanitized bundles to GitHub. Verify locally, inspect the incident
scope, and use the repository's **Sanitized Odoo incident** issue template.
Never upload a production database, filestore, raw log, credentials, personal
data, payment information, or a bundle that has not passed organizational
review.
