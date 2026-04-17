---
name: openclaw-code
description: "Use when a task drafts code changes, refactors, or generates implementation notes and should be routed through OpenClaw."
---

# OpenClaw Code

Use this skill for code planning and generation that should remain inside the OpenClaw workflow.

## Use for

- Drafting code changes.
- Refactoring implementation plans.
- Generating patch guidance before writing files.
- Turning a task into a controlled code change request.

## Preferred route

1. Describe the change with `code.generate`.
2. Review the draft against policy and scope.
3. Apply workspace writes only when allowed.
4. Keep generated changes limited to the requested target.

## Preferred tools

- `code.generate`
- `workspace.read_file`
- `workspace.search`
- `workspace.write_file` when explicitly permitted

## Examples

- "Draft the code changes for a new Odoo model."
- "Generate a safe refactor plan for this controller."
- "Prepare a patch proposal before writing files."