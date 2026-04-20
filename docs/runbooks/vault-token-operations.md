# Vault Token Operations

## Goal

Document the actual Vault-related surfaces that exist in this repository today for MCP token storage, deployment, backup, restore, and emergency rotation.

This note is the operational map for the Vault side of OpenClaw. It does not replace the broader architecture note in [Cost-effective token management](COST-EFFECTIVE-TOKEN-MANAGEMENT.md); it grounds that design in the files that are actually present in the repo.

## Canonical flow today

- `compose.vault.yaml` defines a standalone Vault service with container name `openclaw-vault` and host port `8200`.
- `vault/config.hcl` enables the Vault UI, uses the file backend at `/vault/data`, and currently leaves TLS disabled.
- `.github/workflows/deploy-openclaw.yml` and `.github/workflows/quarterly-token-rotation.yml` are the canonical automation path for token retrieval and rotation.
- Those workflows read and write `secret/openclaw/mcp-tokens-staging` and `secret/openclaw/mcp-tokens-production`.
- If you run manual helpers, treat that secret schema as canonical unless you intentionally realign every dependent script.

## Repo surfaces

### Bootstrap and day-1 helpers

- `setup-vault.sh`
  - brings up `compose.vault.yaml`
  - initializes Vault, unseals it, enables the `secret` KV engine, and seeds `secret/openclaw/mcp-tokens-staging` plus `secret/openclaw/mcp-tokens-production`
  - current caveat: this script still contains placeholder-style credential save lines rather than a hardened persistence flow, so verify manually before trusting it to persist `vault/.unseal_key` and `vault/.root_token`
- `generate-tokens.ps1`
  - generates three 32-character MCP tokens on Windows
  - writes local secret-bearing files `.\env.prod` and `.\tokens_context.ps1`
  - practical rule: treat both outputs as transient secrets and keep them out of Git
- `deploy-with-vault.sh`
  - local simulation of a Vault-backed deployment
  - reads `secret/openclaw/mcp-tokens-<environment>` and exports them into the shell before `docker compose up`
  - aligns with the same secret layout used by the GitHub workflows

### Root-level operator helpers

- `backup-vault.sh`
- `restore-vault.sh`
- `check-vault-health.sh`
- `emergency-revoke-token.sh`

These four root-level scripts form the lightweight local helper family.

What they assume:

- container name `openclaw-vault`
- Vault address `http://localhost:8200`
- secret layout `secret/openclaw/mcp-tokens-staging` and `secret/openclaw/mcp-tokens-production`

That makes them closer to the current workflow contract than the older `ops/emergency` family below.

### `ops/emergency` script family

- `ops/emergency/backup-vault.sh`
- `ops/emergency/check-vault-health.sh`
- `ops/emergency/emergency-revoke-token.sh`
- `ops/emergency/README.md`

These scripts are more elaborate and include logging, cron examples, and extra operator guidance. They are still worth reading, but they are not the clean canonical path for the current repo state.

Important caveat:

- this folder currently uses different secret path conventions and different container assumptions than the canonical workflow
- `ops/emergency/emergency-revoke-token.sh` references `openclaw_vault_1`
- that same script writes to `secret/data/staging/<token_type>` and `secret/data/production/<token_type>`
- the GitHub workflows and the root-level helpers use `secret/openclaw/mcp-tokens-*` instead

Operational rule:

- until those families are aligned, treat `ops/emergency/*` as reference material and review each command before using it on a real environment

## Quick commands

Start the standalone Vault service:

```powershell
docker compose -f compose.vault.yaml up -d
```

Check Vault status:

```powershell
docker exec openclaw-vault vault status
```

Generate Windows tokens locally:

```powershell
powershell -ExecutionPolicy Bypass -File .\generate-tokens.ps1
```

Run a local Vault-backed deploy simulation:

```bash
export VAULT_TOKEN=<token>
./deploy-with-vault.sh staging
```

Create encrypted backup with the root helper:

```bash
./backup-vault.sh
```

Restore with the root helper:

```bash
./restore-vault.sh vault-backups/vault-backup-<timestamp>.tar.gz.enc vault-backups/.backup-key-<timestamp>
```

Run the lightweight health check:

```bash
./check-vault-health.sh
```

Emergency token rotation with the root helper:

```bash
export VAULT_TOKEN=<token>
./emergency-revoke-token.sh all
```

## Current limitations

- `compose.vault.yaml` is a separate compose variant; it is not part of the default `compose.yaml` plus `compose.dev.yaml` startup path.
- `vault/config.hcl` currently disables TLS, so this shape is local or lab-friendly, not a hardened public Vault deployment by itself.
- `setup-vault.sh` should be treated as a bootstrap reference helper, not as a fully hardened unattended init script.
- `generate-tokens.ps1` creates local secret files and therefore needs cleanup discipline after use.
- the root helper family and the `ops/emergency` family currently use different secret path conventions.
- if a manual step disagrees with `.github/workflows/deploy-openclaw.yml` or `.github/workflows/quarterly-token-rotation.yml`, trust the workflow schema first and fix the helper before using it.

## Related notes

- [Cost-effective token management](COST-EFFECTIVE-TOKEN-MANAGEMENT.md)
- [Admin and observability tooling](admin-observability-tooling.md)
- [Backup and restore](backup-and-restore.md)
- [Services](../brain/services.md)
