# Hook Setup Guide

Repo-local notes for the optional helper scripts shipped with the vendored `self-improvement` skill.

## What Exists Here

This repository keeps these scripts under `.github/skills/self-improvement/scripts/`:

- `activator.sh`
- `error-detector.sh`
- `extract-skill.sh`

They are not wired into OpenClaw, Docker, or any agent automatically.

## Repo-Local Paths

If an external hook-capable tool or agent should call them, use the repo-local paths rather than the original upstream examples:

- `./.github/skills/self-improvement/scripts/activator.sh`
- `./.github/skills/self-improvement/scripts/error-detector.sh`
- `./.github/skills/self-improvement/scripts/extract-skill.sh`

If your hook runner needs absolute paths, resolve those same files from this repository root.

## What The Scripts Do

- `activator.sh` prints a lightweight `<self-improvement-reminder>` block
- `error-detector.sh` prints `<error-detected>` when command output matches error patterns
- `extract-skill.sh` scaffolds a new skill from a learning when you intentionally run it

## Verification

You can dry-run the extraction helper with the repo-local path:

```bash
./.github/skills/self-improvement/scripts/extract-skill.sh test-skill --dry-run
```

## Security Notes

- These scripts are opt-in.
- `error-detector.sh` reads command output from the hook environment, so treat that input as sensitive.
- Do not log or forward raw tool output unless the user explicitly wants that detail preserved.
