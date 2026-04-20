---
name: ontology
description: Use when you need an optional local knowledge graph for typed entities, explicit relationships, dependency queries, or structured memory that should stay separate from Odoo records and the authoritative OpenClaw memory flows.
---

# Ontology

Use this skill as an audited repo-local fork of the upstream `ontology` concept, not as a hidden second database for the platform.

This repo keeps `ontology` as an optional local knowledge model under `.github/skills/ontology/`. Its default storage, if you intentionally use it, is `memory/ontology/graph.jsonl`.

## Local Contract

- `ontology` is not a source of truth for Odoo records, approvals, policies, or chat/session state.
- `ontology` does not auto-sync with Odoo, Obsidian, or OpenClaw memory.
- Treat it as an optional scratchpad for structured local knowledge when a graph model is genuinely better than plain notes.
- Do not invent graph state that should really live in Odoo, a runbook, or the curated vault.
- Do not store raw secrets in ontology data. Use references or redacted labels only.

## Good Use Cases

Use `ontology` when you need one or more of these:

- typed entities such as `Project`, `Task`, `Document`, `Person`, or `Event`
- explicit relationships such as ownership, dependency, or linkage
- local dependency queries like "what depends on X?"
- a temporary structured model for planning or investigation before promoting facts elsewhere

## Bad Use Cases

Do not use `ontology` for:

- mirroring Odoo business data already owned by the database
- replacing the repo documentation in `docs/`
- storing operator secrets or session transcripts
- pretending there is official synchronization with any OpenClaw connector

## Suggested Storage

If you intentionally enable ontology data in a workspace, keep it local and explicit:

- graph log: `memory/ontology/graph.jsonl`
- optional schema: `memory/ontology/schema.yaml`

Append or merge changes instead of overwriting prior graph history.

## Minimal Data Model

Typical entity families from upstream that still make sense here:

- `Person`
- `Project`
- `Task`
- `Event`
- `Document`
- `Note`

Typical relationship examples:

- `has_owner`
- `has_task`
- `blocks`
- `references`

## Example Shape

```json
{
  "id": "proj_001",
  "type": "Project",
  "properties": {
    "name": "OpenClaw ontology evaluation",
    "status": "draft"
  }
}
```

```json
{
  "from": "proj_001",
  "rel": "has_task",
  "to": "task_001"
}
```

## Promotion Rule

If a fact becomes operationally important, move it to the right authoritative home:

- Odoo for live business/application state
- `docs/brain/` or `docs/runbooks/` for documented platform knowledge
- `.learnings/` plus promoted docs when it is a durable lesson rather than graph data

## Audit Boundary

This fork is intentionally conservative.

- the vendored helper script is limited to local file operations
- the helper script does not perform network calls or subprocess execution
- no automatic graph initialization is configured

The vendored helper lives at `.github/skills/ontology/scripts/ontology.py`.

Current local stance on that helper:

- path access is restricted to the current workspace root
- it is suitable for optional local graph maintenance
- it is still not an authoritative integration with Odoo or OpenClaw memory

## Provenance

- Upstream ClawHub slug: `ontology`
- Upstream author: `oswalpalash`
- Upstream version reviewed for this fork: `1.0.4`

See `README.md` in this folder for the local curation note.
