---
name: openclaw-docs
description: "Use when a task reads or writes docs, runbooks, markdown notes, or Obsidian vault content and should be routed through OpenClaw."
---

# OpenClaw Docs

Use this skill for documentation work that should pass through OpenClaw tools and policy.

## Use for

- Reading markdown files in `docs/`.
- Writing or updating runbooks and notes.
- Searching documentation in the Obsidian vault.
- Keeping docs changes inside the OpenClaw approval path when needed.

## Preferred route

1. Read with `docs.read_markdown`.
2. Search with `docs.search`.
3. Write with `docs.write_markdown`.
4. Keep edits scoped to docs and approved.

## Examples

- "Summarize the backup runbook from OpenClaw."
- "Update the control-plane documentation through the docs skill."
- "Search the Obsidian vault for OpenClaw policies."