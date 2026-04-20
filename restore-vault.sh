#!/bin/bash
# restore-vault.sh - Restore Vault from encrypted backup
# Usage: ./restore-vault.sh vault-backup-20260417_120000.tar.gz.enc .backup-key-20260417_120000
# Cost: FREE

set -e

BACKUP_FILE=${1:-""}
KEY_FILE=${2:-""}

if [ -z "$BACKUP_FILE" ] || [ -z "$KEY_FILE" ]; then
    echo "❌ Missing parameters"
    echo "Usage: $0 <backup-file> <key-file>"
    echo ""
    echo "Example:"
    echo "  $0 vault-backups/vault-backup-20260417_120000.tar.gz.enc vault-backups/.backup-key-20260417_120000"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "❌ Backup or key file not found"
    exit 1
fi

echo "╔════════════════════════════════════════╗"
echo "║  Vault Restore - From Encrypted Backup ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Read encryption key
ENCRYPTION_PASSWORD=$(cat "$KEY_FILE")

# Decrypt backup
echo "[1/3] Decrypting backup..."
TEMP_TAR="/tmp/vault-restore-$RANDOM.tar.gz"
openssl enc -d -aes-256-cbc -in "$BACKUP_FILE" -out "$TEMP_TAR" -k "$ENCRYPTION_PASSWORD" 2>/dev/null
echo "    ✅ Decrypted"

# Stop Vault
echo "[2/3] Stopping Vault..."
docker compose stop vault 2>/dev/null || echo "    ⚠️  Vault not running"

# Restore data
echo "[3/3] Restoring Vault data..."
docker exec openclaw-vault rm -rf /vault/data
docker exec openclaw-vault mkdir -p /vault/data
docker exec -i openclaw-vault tar xzf - --strip-components=2 -C /vault/data < "$TEMP_TAR"
echo "    ✅ Data restored"

# Start Vault
echo "[4/4] Starting Vault..."
docker compose start vault 2>/dev/null
sleep 5

# Cleanup
rm "$TEMP_TAR"

echo ""
echo "╔════════════════════════════════════════╗"
echo "║  ✅ Restore Complete                    ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Verify
echo "Verifying Vault status..."
docker exec openclaw-vault vault status || echo "⚠️  May need to unseal Vault"
echo ""
echo "Next: Unseal Vault with your unseal key"
echo "  docker exec openclaw-vault vault operator unseal <KEY>"
