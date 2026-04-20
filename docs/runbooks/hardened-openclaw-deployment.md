# Hardened OpenClaw Deployment Guide

**Status**: Production-ready  
**Validated**: 2026-04-17  
**Architecture**: 3 dockerized local MCP services + FastAPI control-plane bridge

---

## Overview

This guide covers deploying OpenClaw with mandatory authentication tokens on all internal MCP connectors (Obsidian, Memory, Context7). All three MCP services run as internal Docker services with zero external port exposure.

## Pre-Deployment Checklist

1. **Environment Variables**: Copy and customize environment file
   ```powershell
   Copy-Item .env.prod.example .env.prod  # or .env.staging.example, .env.dev.example
   ```

2. **Token Rotation** (CRITICAL):
   ```powershell
   # Replace all three placeholders with secure random tokens (32+ chars)
   # Using PowerShell:
   $token1 = -join ((48..57) + (97..122) | Get-Random -Count 32 | % {[char]$_})
   $token2 = -join ((48..57) + (97..122) | Get-Random -Count 32 | % {[char]$_})
   $token3 = -join ((48..57) + (97..122) | Get-Random -Count 32 | % {[char]$_})
   
   # Then edit .env.prod (or whichever environment file):
   # OPENCLAW_OBSIDIAN_MCP_TOKEN=$token1
   # OPENCLAW_MEMORY_MCP_TOKEN=$token2
   # OPENCLAW_CONTEXT7_MCP_TOKEN=$token3
   ```

3. **Store Tokens Securely**: Use your secret management system (HashiCorp Vault, AWS Secrets Manager, etc.)

## Deployment Commands

### Local Development (with temporary tokens)
```powershell
# Set temporary tokens for local testing:
$env:OPENCLAW_OBSIDIAN_MCP_TOKEN='tmp_obsidian_token_dev'
$env:OPENCLAW_MEMORY_MCP_TOKEN='tmp_memory_token_dev'
$env:OPENCLAW_CONTEXT7_MCP_TOKEN='tmp_context7_token_dev'

# Start all services:
docker compose -f compose.yaml -f compose.admin.yaml up -d --build
```

### Production Deployment
```powershell
# Load tokens from environment (or .env.prod):
docker compose -f compose.yaml -f compose.prod.yaml up -d --build

# Verify deployment:
powershell -ExecutionPolicy Bypass -File .\ops\health\check-openclaw-connectors.ps1
```

## Architecture

### Services & Ports

| Service | Container | Port | Exposure | Auth |
|---------|-----------|------|----------|------|
| **control-plane** | odoo19-control-plane | 8082 | Host (user-facing) | OpenRouter API key |
| **obsidian-mcp** | odoo19-obsidian-mcp | 8090 | Internal only | HMAC Bearer token |
| **memory-mcp** | odoo19-memory-mcp | 8091 | Internal only | HMAC Bearer token |
| **context7-mcp** | odoo19-context7-mcp | 8092 | Internal only | HMAC Bearer token |
| Odoo | odoo19-odoo | 8069 | Host (user-facing) | Odoo session |
| PostgreSQL | odoo19-db | 5432 | Internal only | psql password |
| Redis | odoo19-redis | 6379 | Internal only | redis password |

### MCP Service Features

#### Obsidian MCP (`services/obsidian-mcp/`)
- **Tools**: `obsidian.list_notes`, `obsidian.read_note`, `obsidian.write_note`, `obsidian.search_notes`
- **Mount**: `/docs` → `/vault`
- **Auth**: Mandatory `OPENCLAW_OBSIDIAN_MCP_TOKEN` (fail-fast if missing)

#### Memory MCP (`services/memory-mcp/`)
- **Tools**: `memory.get`, `memory.set`, `memory.delete`, `memory.list`
- **Storage**: Persistent JSON file at `/data/memory_store.json` (volume: `memory-mcp-data`)
- **Auth**: Mandatory `OPENCLAW_MEMORY_MCP_TOKEN` (fail-fast if missing)

#### Context7 MCP (`services/context7-mcp/`)
- **Tools**: `resolve-library-id`, `query-docs`
- **Libraries**: 
  - `odoo/odoo-19` (queries `/docs/odoo19_schema/`, `/docs/brain/`, `/docs/runbooks/`)
  - `openclaw/platform` (same doc mount)
- **Auth**: Mandatory `OPENCLAW_CONTEXT7_MCP_TOKEN` (fail-fast if missing)

### Authentication Flow

1. **At Startup**:
   - Each MCP service checks: `if not AUTH_TOKEN: raise RuntimeError("MCP_AUTH_TOKEN is required")`
   - Docker compose enforces token presence via `${VAR:?required}` syntax
   - Deployment fails immediately if token not set

2. **At Request Time**:
   - Client sends: `Authorization: Bearer <TOKEN>`
   - Server validates HMAC SHA256 signature
   - Token mismatch → 401 Unauthorized

3. **Gateway Bridging**:
   - control-plane stores MCP tokens in its own environment
   - Gateway signs outbound requests with stored token
   - Transparent to Odoo/client layer

## Validation

### Health Check Script
```powershell
powershell -ExecutionPolicy Bypass -File .\ops\health\check-openclaw-connectors.ps1
```

**Expected Output**:
```
[1/6] Checking MCP gateway reachability at http://localhost:8082/mcp
Gateway is reachable. Tools reported: 26

[2/6] Verifying required bridge tools are registered
Required bridge tools are registered.

[3/6] Calling obsidian.mcp_tools_list and memory.mcp_tools_list
Obsidian list response:
{
  "kind": "completed",
  "summary": "Remote MCP request completed.",
  "endpoint": "http://obsidian-mcp:8090/mcp",
  "tools": [4 tools listed]
}
Memory list response:
{
  "kind": "completed",
  "summary": "Remote MCP request completed.",
  "endpoint": "http://memory-mcp:8091/mcp",
  "tools": [4 tools listed]
}

[4/6] Calling Context7 resolve + query through gateway
Context7 resolve response:
{
  "kind": "completed",
  "summary": "Resolved 2 candidate library id(s).",
  "result": [
    {"libraryId": "odoo/odoo-19", "score": 46},
    {"libraryId": "openclaw/platform", "score": 12}
  ]
}
```

**Exit Code**: `0` (success)

## Troubleshooting

### MCP service fails to start
**Error**: `RuntimeError: MCP_AUTH_TOKEN is required for <service-name>`

**Solution**: Verify token is set in environment or `.env` file:
```powershell
# Check what compose sees:
docker compose config | grep -A 3 "OPENCLAW_.*MCP_TOKEN"
```

### Gateway can't reach MCP service
**Error**: `Connection refused at http://obsidian-mcp:8090/mcp`

**Solution**: Verify Docker network:
```powershell
docker network ls  # Should see odoo_net
docker inspect odoo_net  # Should list obsidian-mcp, memory-mcp, context7-mcp as connected
```

### Token validation fails
**Error**: `401 Unauthorized` on MCP calls

**Solution**: Verify token stored in control-plane matches MCP service token:
```powershell
docker exec odoo19-control-plane-1 env | grep OPENCLAW_
docker exec odoo19-obsidian-mcp-1 env | grep MCP_AUTH_TOKEN
# Should match
```

## Environment File Reference

### `.env.prod` (Production)
```bash
# OpenClaw MCP Authentication (rotate before deploy)
OPENCLAW_OBSIDIAN_MCP_TOKEN=<secure-random-token-32-chars>
OPENCLAW_MEMORY_MCP_TOKEN=<secure-random-token-32-chars>
OPENCLAW_CONTEXT7_MCP_TOKEN=<secure-random-token-32-chars>

# Internal service URLs (do not change)
OPENCLAW_OBSIDIAN_MCP_URL=http://obsidian-mcp:8090/mcp
OPENCLAW_MEMORY_MCP_URL=http://memory-mcp:8091/mcp
OPENCLAW_CONTEXT7_MCP_URL=http://context7-mcp:8092/mcp
```

## Security Considerations

1. **Token Scope**: Each MCP service has its own token; compromise of one does not affect others
2. **Rotation**: Recommended quarterly or after team changes
3. **Legacy Tokens**: Set to invalid value to force new generation: `OPENCLAW_OBSIDIAN_MCP_TOKEN=ROTATED_OUT_DATE_YYYY-MM-DD`
4. **Monitoring**: Log failed auth attempts from compose logs:
   ```powershell
   docker logs odoo19-obsidian-mcp-1 --tail 50 | Select-String "401\|Unauthorized"
   ```

## Rollback

If MCP services are not responding, fallback to previous compose without MCP:
```powershell
# Stop only MCP services:
docker compose stop obsidian-mcp memory-mcp context7-mcp

# Restart control-plane (will retry MCP connections):
docker compose restart control-plane

# Check logs:
docker logs odoo19-control-plane-1 --tail 20
```

---

**Last Updated**: 2026-04-17  
**Validated By**: Automated health check script  
**Next Review**: 2026-04-17 (quarterly recommended)
