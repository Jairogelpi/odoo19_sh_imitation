# OpenClaw MCP Token Reference Card

**Generated**: 2026-04-17 18:16:08  
**Status**: ✅ **ACTIVE & VALIDATED**  
**Security Level**: Production-Grade (32-char cryptographic tokens)

---

## Quick Reference

### Token Values

```
OPENCLAW_OBSIDIAN_MCP_TOKEN
├─ Value: MGM0ZWM0YzYtM2U0OS00Zjg5LThjZWYt
├─ Service: Obsidian vault connector (read/write/search notes)
├─ Port: 8090 (internal Docker network only)
└─ Status: ✅ Running

OPENCLAW_MEMORY_MCP_TOKEN
├─ Value: NDYzZTI4NzEtNmRkNy00OGZkLWE2N2Et
├─ Service: Persistent key-value memory store
├─ Port: 8091 (internal Docker network only)
└─ Status: ✅ Running

OPENCLAW_CONTEXT7_MCP_TOKEN
├─ Value: YmI0N2E0MDMtMGE5Yi00OGZmLWFjOTUt
├─ Service: Library resolver & documentation querying
├─ Port: 8092 (internal Docker network only)
└─ Status: ✅ Running
```

### Environment File Locations

| File | Purpose | Location |
|------|---------|----------|
| `.env.prod` | Production tokens (NEW) | `./` |
| `.env.prod.example` | Token template | `./` |
| `generate-tokens.ps1` | Token generation script | `./` |

### Shell Export (Quick Start)

```powershell
# Export all 3 tokens to current shell
$env:OPENCLAW_OBSIDIAN_MCP_TOKEN='MGM0ZWM0YzYtM2U0OS00Zjg5LThjZWYt'
$env:OPENCLAW_MEMORY_MCP_TOKEN='NDYzZTI4NzEtNmRkNy00OGZkLWE2N2Et'
$env:OPENCLAW_CONTEXT7_MCP_TOKEN='YmI0N2E0MDMtMGE5Yi00OGZmLWFjOTUt'
```

---

## Deployment Quick Command

**Local Testing**:
```bash
# Export tokens
$env:OPENCLAW_OBSIDIAN_MCP_TOKEN='MGM0ZWM0YzYtM2U0OS00Zjg5LThjZWYt'
$env:OPENCLAW_MEMORY_MCP_TOKEN='NDYzZTI4NzEtNmRkNy00OGZkLWE2N2Et'
$env:OPENCLAW_CONTEXT7_MCP_TOKEN='YmI0N2E0MDMtMGE5Yi00OGZmLWFjOTUt'

# Deploy
docker compose -f compose.yaml -f compose.admin.yaml up -d --build

# Validate
powershell -ExecutionPolicy Bypass -File .\ops\health\check-openclaw-connectors.ps1
```

---

## Health Check Command

```bash
powershell -ExecutionPolicy Bypass -File .\ops\health\check-openclaw-connectors.ps1
```

**Expected Result**:
- ✅ [1/6] Gateway 26 tools registered
- ✅ [2/6] Bridge tools verified
- ✅ [3/6] Obsidian 4 tools listed
- ✅ [3/6] Memory 4 tools listed  
- ✅ [4/6] Context7 2 libraries resolved
- ✅ [4/6] Context7 20 docs returned

---

## Vault Integration (Production)

### HashiCorp Vault

```bash
# Store tokens in Vault
vault kv put secret/openclaw/mcp-tokens \
  obsidian=MGM0ZWM0YzYtM2U0OS00Zjg5LThjZWYt \
  memory=NDYzZTI4NzEtNmRkNy00OGZkLWE2N2Et \
  context7=YmI0N2E0MDMtMGE5Yi00OGZmLWFjOTUt

# Retrieve during deployment
export OPENCLAW_OBSIDIAN_MCP_TOKEN=$(vault kv get -field=obsidian secret/openclaw/mcp-tokens)
export OPENCLAW_MEMORY_MCP_TOKEN=$(vault kv get -field=memory secret/openclaw/mcp-tokens)
export OPENCLAW_CONTEXT7_MCP_TOKEN=$(vault kv get -field=context7 secret/openclaw/mcp-tokens)

# Deploy
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

### AWS Secrets Manager

```bash
# Store tokens
aws secretsmanager create-secret \
  --name openclaw/mcp-tokens \
  --secret-string '{"obsidian":"MGM0ZWM0YzYtM2U0OS00Zjg5LThjZWYt","memory":"NDYzZTI4NzEtNmRkNy00OGZkLWE2N2Et","context7":"YmI0N2E0MDMtMGE5Yi00OGZmLWFjOTUt"}'

# Retrieve during deployment
TOKEN_JSON=$(aws secretsmanager get-secret-value --secret-id openclaw/mcp-tokens --query SecretString --output text)
export OPENCLAW_OBSIDIAN_MCP_TOKEN=$(echo $TOKEN_JSON | jq -r .obsidian)
export OPENCLAW_MEMORY_MCP_TOKEN=$(echo $TOKEN_JSON | jq -r .memory)
export OPENCLAW_CONTEXT7_MCP_TOKEN=$(echo $TOKEN_JSON | jq -r .context7)

# Deploy
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

---

## Security Checklist

- [x] Tokens generated with cryptographic randomness
- [x] 32 characters each (strong entropy)
- [x] Each service has isolated token (no shared secrets)
- [x] Fail-fast validation at compose level (`:?required`)
- [x] Fail-fast validation at service level (Python startup check)
- [x] Bearer token authentication on all MCP endpoints
- [x] Internal network isolation (no exposed MCP ports)
- [x] All 6 health checks passing
- [x] Token rejection confirmed (security test passed)
- [ ] Tokens stored in production secret manager (next step)
- [ ] Quarterly rotation schedule created (next step)
- [ ] Team access policies configured (next step)

---

## Troubleshooting Shortcuts

### Service won't start
```bash
docker logs odoo19-obsidian-mcp-1 | grep "RuntimeError\|required"
docker logs odoo19-memory-mcp-1 | grep "RuntimeError\|required"
docker logs odoo19-context7-mcp-1 | grep "RuntimeError\|required"
```

### 401 Auth failures
```bash
# Check control-plane has same tokens as services
docker exec odoo19-control-plane-1 env | grep OPENCLAW_
docker exec odoo19-obsidian-mcp-1 env | grep MCP_AUTH_TOKEN
```

### Network issues
```bash
docker network inspect odoo_net
docker exec odoo19-control-plane-1 curl -v http://obsidian-mcp:8090/mcp 2>&1 | grep "Connected\|refused"
```

---

## Files & Locations

| File | Purpose | Status |
|------|---------|--------|
| `./.env.prod` | Production tokens | ✅ Created |
| `./generate-tokens.ps1` | Token generator | ✅ Created |
| `./DEPLOYMENT_LOG_2026-04-17.md` | Full deployment log | ✅ Created |
| `./docs/runbooks/hardened-openclaw-deployment.md` | Runbook | ✅ Created |
| `./ops/health/check-openclaw-connectors.ps1` | Health check | ✅ Running |

---

**Reference Card Version**: 1.0  
**Last Updated**: 2026-04-17 18:18:09  
**Status**: ✅ All systems operational with rotated tokens
