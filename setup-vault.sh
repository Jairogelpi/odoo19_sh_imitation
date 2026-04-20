#!/bin/bash
# setup-vault.sh - Initialize HashiCorp Vault for OpenClaw token management
# Cost-effective, self-hosted token storage (FREE)
# Usage: ./setup-vault.sh

set -e

echo "╔════════════════════════════════════════════╗"
echo "║  OpenClaw Vault Setup - Cost-Effective     ║"
echo "║  (Self-hosted, FREE, within Docker)        ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Step 1: Start Vault
echo "[1/5] Starting Vault container..."
docker compose -f compose.vault.yaml up -d
sleep 5

# Step 2: Initialize Vault (first-time only)
echo "[2/5] Initializing Vault..."
INIT_OUTPUT=$(docker exec openclaw-vault vault operator init -key-shares=1 -key-threshold=1 2>&1 || echo "Already initialized")

if echo "$INIT_OUTPUT" | grep -q "Unseal Key"; then
    echo "✅ Vault initialized"
    UNSEAL_KEY=$(echo "$INIT_OUTPUT" | grep "Unseal Key 1:" | awk '{print $NF}')
    ROOT_TOKEN=$(echo "$INIT_OUTPUT" | grep "Initial Root Token:" | awk '{print $NF}')
    
    # Save for documentation (never commit to Git!)
    cat > vault/.unseal_key (chmod 600)
    cat > vault/.root_token (chmod 600)
    
    echo "⚠️  IMPORTANT - Save these credentials securely (not in Git):"
    echo "   Unseal Key: $UNSEAL_KEY"
    echo "   Root Token: $ROOT_TOKEN"
else
    echo "✅ Vault already initialized"
fi

# Step 3: Unseal Vault
echo "[3/5] Unsealing Vault..."
UNSEAL_KEY=$(cat vault/.unseal_key 2>/dev/null || read -sp "Enter unseal key: " key; echo $key)
docker exec openclaw-vault vault operator unseal "$UNSEAL_KEY" 2>/dev/null || echo "Already unsealed"

# Step 4: Enable KV secrets engine
echo "[4/5] Configuring Vault secrets engine..."
ROOT_TOKEN=$(cat vault/.root_token 2>/dev/null || read -sp "Enter root token: " token; echo $token)

docker exec -e VAULT_TOKEN=$ROOT_TOKEN openclaw-vault vault secrets enable -path=secret kv-v2 2>/dev/null || echo "KV v2 already enabled"

# Create secrets for staging and production
echo "[5/5] Storing MCP tokens in Vault..."

docker exec -e VAULT_TOKEN=$ROOT_TOKEN openclaw-vault vault kv put secret/openclaw/mcp-tokens-staging \
    obsidian='PLACEHOLDER_OBSIDIAN_TOKEN_STAGING' \
    memory='PLACEHOLDER_MEMORY_TOKEN_STAGING' \
    context7='PLACEHOLDER_CONTEXT7_TOKEN_STAGING'

docker exec -e VAULT_TOKEN=$ROOT_TOKEN openclaw-vault vault kv put secret/openclaw/mcp-tokens-production \
    obsidian='PLACEHOLDER_OBSIDIAN_TOKEN_PRODUCTION' \
    memory='PLACEHOLDER_MEMORY_TOKEN_PRODUCTION' \
    context7='PLACEHOLDER_CONTEXT7_TOKEN_PRODUCTION'

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║  ✅ Vault Setup Complete!                   ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo "📍 Vault UI: http://localhost:8200"
echo "🔑 Root Token: $ROOT_TOKEN (save securely!)"
echo ""
echo "Next steps:"
echo "1. Update tokens in Vault with actual values:"
echo "   vault kv put secret/openclaw/mcp-tokens-staging obsidian='<token>' ..."
echo "2. Configure GitHub Actions secrets (see docs/VAULT_SETUP.md)"
echo "3. Test with: ./deploy-with-vault.sh staging"
echo ""
