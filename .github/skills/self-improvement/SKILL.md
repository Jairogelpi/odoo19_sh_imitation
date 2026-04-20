---
name: self-improvement
description: Use when a task reveals a correction, recurring error, non-obvious workaround, or missing capability that should be captured in `.learnings/` or promoted into durable repo guidance.
---

# Self-Improvement

Use this skill to capture durable learnings without pretending they are already encoded elsewhere.

This copy is vendored in `.github/skills/self-improvement/`. In this repository you do not install it again with ClawHub, and you do not clone a second copy into the repo. The imported `hooks/`, `scripts/`, and `assets/` trees are kept on purpose, but they remain support material, not auto-enabled behavior.

## Local Contract

- Write learnings to a trusted `.learnings/` directory in the repo root or the workspace root you are actively using.
- Do not overwrite existing learning files just to match a template.
- Do not log secrets, tokens, private keys, environment variables, or full source/config files unless the user explicitly asks for that level of detail.
- When a learning changes operator behavior or platform expectations, promote it into durable docs such as `AGENTS.md`, `.github/copilot-instructions.md`, or the relevant note under `docs/brain/` or `docs/runbooks/`.

## What To Log

| Situation | Target |
|-----------|--------|
| User corrects you | `.learnings/LEARNINGS.md` with category `correction` |
| You discover a non-obvious workaround or rule | `.learnings/LEARNINGS.md` with category `best_practice` or `insight` |
| A command, integration, or tool fails unexpectedly | `.learnings/ERRORS.md` |
| The user requests a capability that does not exist yet | `.learnings/FEATURE_REQUESTS.md` |
| A pattern keeps recurring | Update the existing entry, add `See Also`, and raise priority if warranted |

## First Use

If `.learnings/` does not exist yet, create these files:

- `.learnings/LEARNINGS.md`
- `.learnings/ERRORS.md`
- `.learnings/FEATURE_REQUESTS.md`

Use the templates in `.github/skills/self-improvement/assets/` if you want a starting point, but do not replace existing project data with the asset copies.

## Logging Workflow

1. Capture only the specific lesson, correction, or failure that is likely to matter again.
2. Link related entries with `See Also` instead of duplicating the whole story.
3. Mark clear next action or promotion target when the learning should become durable repo guidance.
4. Resolve or promote entries once the fix lands, rather than letting `.learnings/` become a graveyard.

## ID Format

Use `TYPE-YYYYMMDD-XXX`:

- `LRN` for learnings
- `ERR` for errors
- `FEAT` for feature requests

Examples: `LRN-20260418-001`, `ERR-20260418-A3F`, `FEAT-20260418-002`

## Entry Templates

### Learning Entry

Append to `.learnings/LEARNINGS.md`:

```markdown
## [LRN-YYYYMMDD-XXX] category

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Summary
One-line description of what changed in your understanding

### Details
What was wrong, what is now known, and why it matters

### Suggested Action
Specific follow-up or promotion target

### Metadata
- Source: conversation | error | user_feedback
- Related Files: path/to/file.ext
- See Also: LRN-20260418-001
```

### Error Entry

Append to `.learnings/ERRORS.md`:

```markdown
## [ERR-YYYYMMDD-XXX] command_or_skill

**Logged**: ISO-8601 timestamp
**Priority**: high
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Summary
Short description of the failure

### Error
Redacted or minimal error output

### Context
- Command or operation attempted
- Relevant inputs
- Why the failure was non-obvious

### Suggested Fix
Most plausible repair or next check

### Metadata
- Reproducible: yes | no | unknown
- Related Files: path/to/file.ext
- See Also: ERR-20260418-001
```

### Feature Request Entry

Append to `.learnings/FEATURE_REQUESTS.md`:

```markdown
## [FEAT-YYYYMMDD-XXX] capability_name

**Logged**: ISO-8601 timestamp
**Priority**: medium
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Requested Capability
What the user wanted

### User Context
Why they needed it

### Suggested Implementation
What module, workflow, or doc would likely absorb it

### Metadata
- Frequency: first_time | recurring
- Related Files: path/to/file.ext
```

## Promotion Rules

Promote a learning when it stops being a one-off incident and starts acting like durable project knowledge.

Typical promotion targets in this repo:

- `AGENTS.md` for execution rules or workflow guardrails
- `.github/copilot-instructions.md` for persistent coding context
- `docs/brain/` for architecture, skill-catalog, or operator-facing platform notes
- `docs/runbooks/` for repeatable operational procedures

## OpenClaw Integration

This repository keeps the OpenClaw-specific hook material vendored under `.github/skills/self-improvement/hooks/openclaw`.

Important guardrails:

- The hook tree is retained for future use and traceability.
- It is not auto-installed by this repo.
- It is not auto-enabled by `docker compose up`.

If your OpenClaw home expects hooks under `~/.openclaw/hooks/`, copy the vendored source directory into that hook home as `self-improvement`, then enable it:

```bash
cp -r .github/skills/self-improvement/hooks/openclaw ~/.openclaw/hooks/self-improvement
openclaw hooks enable self-improvement
```

If your OpenClaw installation uses a different hooks directory, adjust only the destination path. The source of truth in this repo remains `.github/skills/self-improvement/hooks/openclaw`.

See `.github/skills/self-improvement/references/openclaw-integration.md` for the repo-local integration note.

## Optional Helper Scripts

This import also keeps helper scripts under `.github/skills/self-improvement/scripts/`:

- `activator.sh`
- `error-detector.sh`
- `extract-skill.sh`

They are useful only if you intentionally wire them into another tool or agent. This repository does not auto-configure them.

If you use a hook-capable agent outside OpenClaw, point it at the repo-local paths, for example:

- `./.github/skills/self-improvement/scripts/activator.sh`
- `./.github/skills/self-improvement/scripts/error-detector.sh`

See `.github/skills/self-improvement/references/hooks-setup.md` for the repo-local path notes.

## Extraction

When the same learning becomes broadly reusable, extract it into a separate skill instead of burying it in `.learnings/`.

Use the helper if you actually need a new skill artifact:

```bash
./.github/skills/self-improvement/scripts/extract-skill.sh skill-name --dry-run
./.github/skills/self-improvement/scripts/extract-skill.sh skill-name
```

Only extract once the pattern is verified, reusable, and not hardcoded to this repo's transient state.
