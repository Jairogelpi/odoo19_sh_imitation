# OpenClaw Integration

Repo-local integration note for the vendored `self-improvement` skill.

## What Is True In This Repository

- The skill is already vendored under `.github/skills/self-improvement/`.
- The OpenClaw hook source lives under `.github/skills/self-improvement/hooks/openclaw`.
- The hook is not auto-installed and not auto-enabled.
- `.learnings/` should live in the repo root or the trusted OpenClaw workspace root you are actively using.

## Minimal OpenClaw Hook Flow

If your local OpenClaw home expects hooks under `~/.openclaw/hooks/`, install the vendored hook material from this repository:

```bash
cp -r .github/skills/self-improvement/hooks/openclaw ~/.openclaw/hooks/self-improvement
openclaw hooks enable self-improvement
```

If your OpenClaw home uses another directory, keep the same repo-local source path and change only the destination.

## Promotion Guidance

Use `.learnings/` for incident capture, then promote durable findings to the right target:

- `AGENTS.md` for workflow rules
- `TOOLS.md` for tool gotchas in an OpenClaw workspace
- `SOUL.md` for behavioral guidance in an OpenClaw workspace
- `docs/brain/` or `docs/runbooks/` when the learning changes this repository's documented operating model

## Security Reminder

Do not push raw transcripts, secrets, or full command output into `.learnings/`, `TOOLS.md`, or any promoted note unless the user explicitly wants that detail preserved.

## Verification

Check hook is registered:

```bash
openclaw hooks list
```

Check skill is loaded:

```bash
openclaw status
```

## Troubleshooting

### Hook not firing

1. Ensure hooks enabled in config
2. Restart gateway after config changes
3. Check gateway logs for errors

### Learnings not persisting

1. Verify `.learnings/` directory exists
2. Check file permissions
3. Ensure workspace path is configured correctly

### Skill not loading

1. Check skill is in skills directory
2. Verify SKILL.md has correct frontmatter
3. Run `openclaw status` to see loaded skills
