#!/bin/bash
# backup-vault.sh - Backup Vault data with encryption
# Usage: ./backup-vault.sh
# Cost: FREE (uses local storage + optional S3)

set -e

echo "╔════════════════════════════════════════╗"
echo "║  Vault Backup - Encrypted & Secure     ║"
echo "╚════════════════════════════════════════╝"
echo ""

BACKUP_DIR="./vault-backups"
BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/vault-backup-$BACKUP_TIMESTAMP.tar.gz.enc"

# Step 1: Create backup directory
echo "[1/4] Creating backup directory..."
mkdir -p "$BACKUP_DIR"
echo "    ✅ Directory: $BACKUP_DIR"

# Step 2: Stop Vault (optional but recommended for consistency)
echo "[2/4] Backing up Vault data..."
docker exec openclaw-vault tar czf - /vault/data 2>/dev/null > "$BACKUP_DIR/vault-backup-$BACKUP_TIMESTAMP.tar.gz"
echo "    ✅ Created: vault-backup-$BACKUP_TIMESTAMP.tar.gz"

# Step 3: Encrypt backup
echo "[3/4] Encrypting backup with openssl AES-256..."
ENCRYPTION_PASSWORD=$(openssl rand -base64 32)
openssl enc -aes-256-cbc -salt -in "$BACKUP_DIR/vault-backup-$BACKUP_TIMESTAMP.tar.gz" \
    -out "$BACKUP_FILE" \
    -k "$ENCRYPTION_PASSWORD" 2>/dev/null
rm "$BACKUP_DIR/vault-backup-$BACKUP_TIMESTAMP.tar.gz"
echo "    ✅ Encrypted: $BACKUP_FILE"

# Step 4: Save encryption key (securely)
KEYFILE="$BACKUP_DIR/.backup-key-$BACKUP_TIMESTAMP"
echo "$ENCRYPTION_PASSWORD" > "$KEYFILE"
chmod 600 "$KEYFILE"
echo "    ✅ Key saved (secure): $KEYFILE"

echo ""
echo "╔════════════════════════════════════════╗"
echo "║  Backup Complete & Encrypted           ║"
echo "╚════════════════════════════════════════╝"
echo ""

# Show backup info
ls -lh "$BACKUP_FILE"
echo ""

# Optional: Upload to S3 (commented, can be enabled)
echo "Optional: Upload to S3"
echo "  aws s3 cp $BACKUP_FILE s3://your-bucket/vault-backups/"
echo "  aws s3 cp $KEYFILE s3://your-bucket/vault-backups/"
echo ""

# Show restore instructions
echo "🔍 To restore later:"
echo "  ./restore-vault.sh $BACKUP_FILE $KEYFILE"
echo ""

echo "✅ Backup stored at: $BACKUP_FILE"
echo "⚠️  Keep encryption key safe: $KEYFILE"
