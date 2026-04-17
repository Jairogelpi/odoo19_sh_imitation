---
name: openclaw-workspace
description: "Use when a task reads, writes, lists, or searches workspace files and should be routed through OpenClaw instead of direct low-level edits."
---

# OpenClaw Workspace

Use this skill for repository file operations that should remain inside the OpenClaw workflow.

## Use for

- Reading files under the permitted workspace roots.
- Writing files under `docs/` or `addons_custom/` when allowed.
- Listing trees and searching workspace content.
- Drafting code changes that still need approval before writing.

## Preferred route

1. Inspect with `workspace.list_tree` or `workspace.search`.
2. Read with `workspace.read_file`.
3. Draft with `code.generate` when helpful.
4. Write only through `workspace.write_file` and only when permitted.

## Examples

- "List the OpenClaw addon tree."
- "Search the workspace for gateway usage."
- "Write a new docs note after approval."