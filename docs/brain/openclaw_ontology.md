# OpenClaw Ontology Skill

## Purpose

This note records why the local `ontology` skill exists in this repository and why it was imported conservatively.

## Current local status

- The skill is vendored at [`.github/skills/ontology/`](../../.github/skills/ontology/).
- It is an audited repo-local fork of the upstream ClawHub skill `ontology`.
- It is optional and repo-local.
- It is not wired into Odoo, Obsidian, or the persistent OpenClaw memory connectors.
- It now includes a vendored local helper script for graph file maintenance.

## Why it was not imported unchanged

The upstream skill is conceptually useful, but this repo already has multiple authoritative state paths:

- Odoo for live application and business data
- `docs/` as the operator-facing vault
- OpenClaw memory connectors for persistent memory workflows

Importing the upstream ontology skill as if it were another official memory layer would blur those boundaries and create avoidable state duplication.

## Accepted scope

The local fork is acceptable only as:

- an optional typed graph model for local analysis
- a structured scratchpad for explicit entities and relationships
- a non-authoritative support layer when graph queries are genuinely useful

## Rejected scope

The local fork is not approved for:

- mirroring Odoo records as a second database
- acting as official chat/session memory
- automatic synchronization with Obsidian or external MCP memory
- storing secrets or raw credentials

## Storage model

If ontology data is intentionally used, the expected local path is:

- `memory/ontology/graph.jsonl`

Optional schema guidance may live in:

- `memory/ontology/schema.yaml`

These files are workspace-local, not platform-authoritative.

## Audit decision

The upstream skill was reviewed as a candidate and accepted only in a reduced form.

What was kept:

- the concept
- the upstream slug/version traceability
- the local contract and storage guidance

What was kept after the line-by-line audit:

- the upstream helper concept in `scripts/ontology.py`

Why it passed:

- no network calls were found
- no subprocess execution was found
- file operations are local and path-bounded
- the helper is still optional and non-authoritative

## Provenance

- ClawHub page: https://clawhub.ai/oswalpalash/ontology
- Archived upstream bundle: https://github.com/openclaw/skills/tree/main/skills/oswalpalash/ontology
- Reviewed upstream version: `1.0.4`

## Future upgrade path

Only expand this skill beyond documentation-first scope if all of the following happen:

1. The use case clearly needs graph-native local modeling.
2. We define how ontology data relates to Odoo and vault state.
3. Any executable helper imported from upstream is audited line-by-line before vendoring.
4. The new behavior is documented in this vault and covered by tests.
