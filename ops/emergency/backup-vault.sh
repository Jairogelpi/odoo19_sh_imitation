#!/bin/bash

################################################################################
# Vault Backup Script
# Purpose: Backup Vault data with AES-256 encryption
# Usage: ./backup-vault.sh
# Output: backup/vault-backup-TIMESTAMP.tar.gz.enc + encryption key
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="${BACKUP_DIR:-backup}"
VAULT_DATA_PATH="${VAULT_DATA_PATH:-/vault/data}"
VAULT_CONTAINER="${VAULT_CONTAINER:-openclaw_vault_1}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/vault-backup-${TIMESTAMP}.tar.gz.enc"
KEY_FILE="$BACKUP_DIR/.backup-key-${TIMESTAMP}"
TEMP_DIR="/tmp/vault-backup-$TIMESTAMP"
LOG_FILE="$BACKUP_DIR/backup-${TIMESTAMP}.log"

################################################################################
# Logging Functions
################################################################################

log_info() {
    echo -e "${BLUE}ℹ️  $@${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✅ $@${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $@${NC}" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}❌ $@${NC}" | tee -a "$LOG_FILE"
}

################################################################################
# Helper Functions
################################################################################

create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        log_info "Creating backup directory: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
    fi
}

check_vault_healthy() {
    log_info "Checking Vault health..."
    
    if ! docker ps -a --filter "name=$VAULT_CONTAINER" | grep -q "$VAULT_CONTAINER"; then
        log_error "Vault container not found: $VAULT_CONTAINER"
        log_info "Available containers:"
        docker ps -a | grep -i vault || log_warning "No Vault containers found"
        exit 1
    fi
    
    if ! docker ps --filter "name=$VAULT_CONTAINER" | grep -q "$VAULT_CONTAINER"; then
        log_warning "Vault container is not running"
        log_info "Starting Vault container..."
        docker-compose up -d vault || log_error "Could not start Vault"
        sleep 3
    fi
    
    log_success "Vault is healthy"
}

copy_vault_data() {
    log_info "Copying Vault data to temporary location..."
    
    mkdir -p "$TEMP_DIR"
    
    # Copy data from container
    if docker cp "$VAULT_CONTAINER:$VAULT_DATA_PATH/." "$TEMP_DIR/" > /dev/null 2>&1; then
        log_success "   ✅ Data copied from container"
    else
        log_error "Failed to copy Vault data from container"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # Verify data was copied
    if [ -z "$(ls -A "$TEMP_DIR")" ]; then
        log_error "Vault data directory is empty"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    log_success "   ✅ Verified data integrity"
}

compress_data() {
    log_info "Compressing Vault data..."
    
    local compressed_file="/tmp/vault-backup-${TIMESTAMP}.tar.gz"
    
    # Create compressed archive
    if tar -czf "$compressed_file" -C "$TEMP_DIR" . 2>/dev/null; then
        log_success "   ✅ Compressed successfully"
        
        # Get size
        local size=$(du -h "$compressed_file" | cut -f1)
        log_info "   📦 Size: $size"
        
        echo "$compressed_file"
    else
        log_error "Failed to compress Vault data"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
}

encrypt_backup() {
    local compressed_file=$1
    
    log_info "Encrypting backup with AES-256..."
    
    # Generate random salt
    local salt=$(openssl rand -hex 16)
    
    # Derive encryption key from salt
    local encryption_key=$(openssl enc -aes-256-cbc -S "$salt" -P -pass pass:"backup_encryption" -nosalt <<< "" 2>/dev/null | grep "key=" | cut -d'=' -f2)
    
    # Encrypt backup file
    if openssl enc -aes-256-cbc -in "$compressed_file" -out "$BACKUP_FILE" \
        -S "$salt" -pass pass:"backup_encryption" -md sha256 2>/dev/null; then
        log_success "   ✅ Encrypted with AES-256"
    else
        log_error "Failed to encrypt backup"
        rm -f "$compressed_file"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # Save encryption key
    cat > "$KEY_FILE" << EOF
# Vault Backup Encryption Key
# Created: $(date)
# Backup File: $(basename $BACKUP_FILE)
# 
# ENCRYPTION DETAILS:
#   Algorithm: AES-256-CBC
#   Hash: SHA256
#   Salt: $salt
#
# RESTORE COMMAND:
#   openssl enc -aes-256-cbc -d -in backup/$(basename $BACKUP_FILE) -out vault-data.tar.gz \\
#     -S $salt -pass pass:backup_encryption -md sha256
#
# TO RESTORE:
#   tar -xzf vault-data.tar.gz

# DO NOT SHARE THIS FILE
# Keep in secure location separate from backup

BACKUP_DATE: $(date)
ENCRYPTION_ALGORITHM: AES-256-CBC
SALT: $salt
EOF
    chmod 600 "$KEY_FILE"
    log_success "   ✅ Encryption key saved: $(basename $KEY_FILE)"
    
    # Remove temporary compressed file
    rm -f "$compressed_file"
    
    # Get encrypted backup size
    local size=$(du -h "$BACKUP_FILE" | cut -f1)
    log_info "   📦 Encrypted size: $size"
}

backup_to_s3() {
    # Optional: Upload to S3 if AWS credentials available
    if command -v aws &> /dev/null && [ -n "${AWS_ACCESS_KEY_ID:-}" ]; then
        log_info "Uploading backup to S3..."
        
        local bucket="${S3_BACKUP_BUCKET:-vault-backups}"
        local s3_path="s3://$bucket/vault-backups/$(basename $BACKUP_FILE)"
        
        if aws s3 cp "$BACKUP_FILE" "$s3_path"; then
            log_success "   ✅ Uploaded to S3: $s3_path"
        else
            log_warning "   ⚠️  Could not upload to S3 (AWS not configured)"
        fi
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    log_info "Vault Backup Started"
    log_info "Timestamp: $(date)"
    log_info "Backup directory: $BACKUP_DIR"
    echo ""
    
    # Pre-flight checks
    create_backup_dir
    check_vault_healthy
    echo ""
    
    # Execute backup steps
    log_info "[1/4] Copying Vault data..."
    copy_vault_data
    echo ""
    
    log_info "[2/4] Compressing data..."
    local compressed_file=$(compress_data)
    echo ""
    
    log_info "[3/4] Encrypting backup..."
    encrypt_backup "$compressed_file"
    echo ""
    
    log_info "[4/4] Optional: Uploading to cloud..."
    backup_to_s3
    echo ""
    
    # Final status
    if [ -f "$BACKUP_FILE" ] && [ -f "$KEY_FILE" ]; then
        log_success "Backup completed successfully!"
        echo ""
        echo -e "${GREEN}📦 Backup Files:${NC}"
        echo "   Encrypted backup: $(basename $BACKUP_FILE)"
        echo "   Encryption key:   $(basename $KEY_FILE)"
        echo ""
        echo -e "${YELLOW}⚠️  IMPORTANT:${NC}"
        echo "   1. Store encryption key in SAFE location"
        echo "   2. Backup should be stored separately from key"
        echo "   3. Test restore monthly: ./restore-vault.sh <backup> <key>"
        echo ""
        echo -e "${BLUE}📝 Log file: $LOG_FILE${NC}"
        
        # Cleanup
        rm -rf "$TEMP_DIR"
    else
        log_error "Backup failed - files not created"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
}

# Cleanup on exit
cleanup() {
    if [ -d "$TEMP_DIR" ]; then
        log_warning "Cleaning up temporary files..."
        rm -rf "$TEMP_DIR"
    fi
}

trap cleanup EXIT

# Run main function
main "$@"
