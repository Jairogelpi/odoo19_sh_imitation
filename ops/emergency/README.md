# Emergency & Operations Scripts

This directory contains production-grade emergency and operational scripts for managing Vault and token security.

## Scripts Overview

### 1. `emergency-revoke-token.sh`
**Purpose**: Immediately revoke and rotate compromised tokens  
**Execution Time**: ~30 seconds per token  
**Risk Level**: Low (safe to run)

#### Usage
```bash
# Revoke obsidian token only
./emergency-revoke-token.sh obsidian

# Revoke memory token only
./emergency-revoke-token.sh memory

# Revoke context7 token only
./emergency-revoke-token.sh context7

# Revoke ALL tokens at once
./emergency-revoke-token.sh all
```

#### What it does
1. Generates new cryptographic 32-character token
2. Updates token in Vault (staging + production)
3. Exports new token to environment
4. Restarts affected service
5. Verifies service health

#### Requirements
- Docker & Docker Compose running
- `VAULT_TOKEN` environment variable set
- Vault must be unsealed

#### Output
```
✅ Emergency revocation complete!
🔑 New token for obsidian: MGN2ZWM0Yz...
📋 Next steps:
   1. Update GitHub Actions secrets
   2. Push code to trigger deployment
   3. Verify health checks pass
```

---

### 2. `backup-vault.sh`
**Purpose**: Backup Vault data with AES-256 encryption  
**Execution Time**: ~5-10 seconds  
**Backup Size**: ~100MB (compressed)

#### Usage
```bash
# Run backup (one time)
./backup-vault.sh

# Run as cron job (daily at 2 AM)
0 2 * * * /path/to/ops/emergency/backup-vault.sh >> /var/log/vault-backup.log
```

#### What it does
1. Creates compressed tar.gz of Vault data
2. Encrypts with AES-256-CBC + random salt
3. Saves encryption key separately
4. Optionally uploads to S3/GCS
5. Removes temporary unencrypted files

#### Output Files
```
backup/vault-backup-20260417_123000.tar.gz.enc    (encrypted backup)
backup/.backup-key-20260417_123000                (encryption key - keep safe!)
```

#### Security
- ✅ AES-256-CBC encryption
- ✅ SHA256 hashing
- ✅ Random salt per backup
- ✅ Separate key storage
- ✅ Secure file permissions (600)

#### Restore
```bash
# To restore from backup
openssl enc -aes-256-cbc -d -in backup/vault-backup-*.tar.gz.enc \
  -S <salt> -pass pass:backup_encryption -md sha256 | tar -xz
```

#### Environment Variables
- `BACKUP_DIR`: Where to store backups (default: `backup`)
- `S3_BUCKET`: S3 bucket for uploads (optional)
- `AWS_ACCESS_KEY_ID`: AWS credentials (optional)

---

### 3. `check-vault-health.sh`
**Purpose**: Monitor Vault health and token validity  
**Execution Time**: ~10 seconds  
**Recommended Frequency**: Every 15 minutes

#### Usage
```bash
# Basic health check
./check-vault-health.sh

# Detailed output with all info
./check-vault-health.sh --detailed

# Send alerts to Slack
./check-vault-health.sh --slack-webhook https://hooks.slack.com/...

# Run as cron job (every 15 minutes)
*/15 * * * * /path/to/ops/emergency/check-vault-health.sh >> /var/log/vault-health.log
```

#### What it checks
1. **Vault Connectivity** - Can reach Vault service
2. **Vault Status** - Is Vault sealed/unsealed
3. **Stored Tokens** - Tokens exist in Vault
4. **MCP Services** - All services running
5. **Token Authentication** - Token is valid/not expired

#### Output
```
✅ SYSTEM STATUS: HEALTHY

✅ Passed: 5
⚠️  Warnings: 0
❌ Failed: 0

Timestamp: 2026-04-17 15:30:00
Log file: logs/vault-health-20260417.log
```

#### Alert Thresholds
- 🟢 **Green**: All checks pass
- 🟡 **Yellow**: Warnings or minor issues
- 🔴 **Red**: Critical failures

#### Slack Integration
```bash
# Set webhook URL
export SLACK_WEBHOOK="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# Run with alerts
./check-vault-health.sh --slack-webhook "$SLACK_WEBHOOK"
```

---

## Installation

### Make scripts executable
```bash
chmod +x emergency-revoke-token.sh
chmod +x backup-vault.sh
chmod +x check-vault-health.sh
```

### Setup cron jobs (recommended)
```bash
# Add to crontab
crontab -e

# Daily Vault backup at 2 AM
0 2 * * * /path/to/ops/emergency/backup-vault.sh >> /var/log/vault-backup.log

# Health check every 15 minutes
*/15 * * * * /path/to/ops/emergency/check-vault-health.sh >> /var/log/vault-health.log

# Weekly test restore
0 3 * * 1 /path/to/ops/emergency/restore-vault.sh backup/vault-backup-*.tar.gz.enc backup/.backup-key-* >> /var/log/vault-restore-test.log
```

---

## Common Scenarios

### Scenario 1: Token Compromise 🚨
```bash
# 1. Revoke immediately
./emergency-revoke-token.sh all

# 2. Update GitHub Actions secrets
# (copy new tokens from script output)

# 3. Push code to trigger deployment
git commit --allow-empty -m "security: rotate tokens"
git push origin main

# 4. Verify with health check
./check-vault-health.sh
```

**Total time**: ~2 minutes

---

### Scenario 2: Monthly Disaster Recovery Test
```bash
# 1. Create backup
./backup-vault.sh

# 2. List backups
ls -lh backup/vault-backup-*.tar.gz.enc

# 3. Test restore in test environment
./restore-vault.sh \
  backup/vault-backup-20260417_123000.tar.gz.enc \
  backup/.backup-key-20260417_123000

# 4. Verify Vault service
./check-vault-health.sh
```

**Total time**: ~5 minutes

---

### Scenario 3: Quarterly Token Rotation
```bash
# 1. Schedule maintenance window
# (announce to team)

# 2. Revoke all tokens
./emergency-revoke-token.sh all

# 3. Update GitHub Actions
# (copy new tokens)

# 4. Deploy
git commit --allow-empty -m "chore: quarterly token rotation"
git push origin main

# 5. Monitor
watch -n 5 './check-vault-health.sh'
```

---

## Troubleshooting

### "Vault is unreachable"
```bash
# Check if Vault is running
docker ps | grep vault

# Start Vault
docker-compose up -d vault

# Check logs
docker logs openclaw_vault_1
```

### "Vault is sealed"
```bash
# Unseal with key
docker exec openclaw_vault_1 vault operator unseal <UNSEAL_KEY>

# Check status
docker exec openclaw_vault_1 vault status
```

### "Token authentication failed"
```bash
# Set VAULT_TOKEN
export VAULT_TOKEN="<your-vault-token>"

# Test
curl -H "X-Vault-Token: $VAULT_TOKEN" \
  http://localhost:8200/v1/auth/token/lookup-self
```

### "Service won't restart"
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs obsidian-mcp

# Restart manually
docker-compose restart obsidian-mcp
```

---

## Monitoring Integration

### Datadog
```bash
# Add to ops/emergency/check-vault-health.sh
# Sends metrics to Datadog
curl -X POST https://api.datadoghq.com/api/v1/series \
  -H "DD-API-KEY: $DATADOG_API_KEY" \
  -d "{\"series\":[{\"metric\":\"vault.health\",\"points\":[[$(date +%s),$passed]]}]}"
```

### Prometheus
```bash
# Scrape metrics endpoint
# Add to prometheus.yml
scrape_configs:
  - job_name: 'vault-health'
    static_configs:
      - targets: ['localhost:9090']
```

### CloudWatch
```bash
# Send metrics to AWS CloudWatch
aws cloudwatch put-metric-data \
  --metric-name VaultHealth \
  --value $passed \
  --namespace Vault
```

---

## Security Best Practices

### For `emergency-revoke-token.sh`
- ✅ Run only on secure, trusted machines
- ✅ Never commit token values to git
- ✅ Delete script after use (keep backup)
- ✅ Log all executions
- ✅ Require approval before running

### For `backup-vault.sh`
- ✅ Store backups in encrypted location
- ✅ Keep encryption keys separate from backups
- ✅ Test restore procedures regularly
- ✅ Rotate old backups quarterly
- ✅ Multiple copies in different locations

### For `check-vault-health.sh`
- ✅ Run as limited privilege user
- ✅ Send alerts to secure channels
- ✅ Track metrics in audit logs
- ✅ Review logs regularly
- ✅ Escalate failures promptly

---

## Documentation

Full documentation and runbooks available in:

- **Main Guide**: ../../EMERGENCY_OPERATIONS.md
- **Token Rotation**: ../../docs/runbooks/COST-EFFECTIVE-TOKEN-MANAGEMENT.md
- **Backup Strategy**: ../../docs/runbooks/backup-and-restore.md
- **Deployment**: ../../ops/deploy/remote-deploy.sh

---

## Support & Escalation

| Issue | Contacts | Response Time |
|-------|----------|-----------------|
| Token compromise | Security team | Immediate (< 5 min) |
| Service down | DevOps lead | 15 minutes |
| Backup failed | Backup admin | 1 hour |
| Health check warning | Monitoring team | 30 minutes |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-17 | Initial release |
| 1.1 | TBD | Add Kubernetes integration |
| 1.2 | TBD | Add Microsoft Teams alerts |

---

**Status**: ✅ PRODUCTION READY  
**Last Updated**: 2026-04-17  
**Maintained By**: DevOps Team
