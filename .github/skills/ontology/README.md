# ontology

Audited repo-local fork of the upstream `ontology` skill for this repository.

## Why this fork exists

The upstream skill is promising as an optional typed knowledge graph, but this repo already has authoritative state in Odoo plus documented memory and vault flows in OpenClaw. Importing it unchanged would blur those boundaries.

This local fork keeps the safe, high-signal contract:

- repo-local skill metadata
- optional storage path guidance
- explicit non-authoritative scope
- provenance back to the upstream ClawHub entry
- a vendored local helper script limited to workspace file operations

## Deliberate omissions

- No automatic sync with Odoo, Obsidian, or OpenClaw memory
- No claim that ontology data is part of the platform's source of truth
- No networked services, background daemons, or hidden sync layer

## Provenance

- ClawHub: `https://clawhub.ai/oswalpalash/ontology`
- Archived upstream path: `https://github.com/openclaw/skills/tree/main/skills/oswalpalash/ontology`

## Local stance

This is an audited repo-local fork. The vendored helper script was kept only because it stays inside workspace-local file operations. Any further expansion should go through the same audit discipline.
