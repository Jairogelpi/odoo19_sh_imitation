#!/bin/bash
# deploy-with-vault.sh - Deploy OpenClaw with tokens from Vault (Cost-effective CI/CD simulation)
# Usage: ./deploy-with-vault.sh staging
# Cost: FREE (no external services)

set -e

ENVIRONMENT=${1:-staging}
VAULT_ADDR=${VAULT_ADDR:-"http://localhost:8200"}
VAULT_TOKEN=${VAULT_TOKEN:-""}

if [ -z "$VAULT_TOKEN" ]; then
    echo "❌ VAULT_TOKEN not set"
    echo "Usage: export VAULT_TOKEN=<token> && ./deploy-with-vault.sh staging"
    exit 1
fi

echo "╔════════════════════════════════════════════╗"
echo "║  Deploy OpenClaw - Cost-Effective Pipeline ║"
echo "║  Environment: $ENVIRONMENT"
echo "║  Vault: $VAULT_ADDR"
echo "╚════════════════════════════════════════════╝"
echo ""

# Step 1: Retrieve tokens from Vault
echo "[1/4] Retrieving MCP tokens from Vault..."
TOKENS=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
    "$VAULT_ADDR/v1/secret/data/openclaw/mcp-tokens-$ENVIRONMENT")

if [ $? -ne 0 ] || echo "$TOKENS" | grep -q "errors"; then
    echo "❌ Failed to retrieve tokens from Vault"
    echo "Error: $TOKENS"
    exit 1
fi

OBSIDIAN_TOKEN=$(echo "$TOKENS" | jq -r '.data.data.obsidian')
MEMORY_TOKEN=$(echo "$TOKENS" | jq -r '.data.data.memory')
CONTEXT7_TOKEN=$(echo "$TOKENS" | jq -r '.data.data.context7')

echo "✅ Retrieved tokens from Vault"
echo "   Obsidian: $(echo $OBSIDIAN_TOKEN | cut -c1-10)..."
echo "   Memory:   $(echo $MEMORY_TOKEN | cut -c1-10)..."
echo "   Context7: $(echo $CONTEXT7_TOKEN | cut -c1-10)..."
echo ""

# Step 2: Export tokens to environment
echo "[2/4] Exporting tokens to environment..."
export OPENCLAW_OBSIDIAN_MCP_TOKEN="$OBSIDIAN_TOKEN"
export OPENCLAW_MEMORY_MCP_TOKEN="$MEMORY_TOKEN"
export OPENCLAW_CONTEXT7_MCP_TOKEN="$CONTEXT7_TOKEN"
echo "✅ Tokens exported"
echo ""

# Step 3: Deploy services
echo "[3/4] Deploying services..."
if [ "$ENVIRONMENT" = "production" ]; then
    docker compose -f compose.yaml -f compose.prod.yaml up -d --build
else
    docker compose -f compose.yaml -f compose.admin.yaml up -d --build
fi
echo "✅ Services deployed"
echo ""

# Step 4: Run health check
echo "[4/4] Running health check..."
sleep 10

if command -v powershell &> /dev/null; then
    powershell -ExecutionPolicy Bypass -File ./ops/health/check-openclaw-connectors.ps1
else
    # Fallback: curl-based health check
    echo "Checking gateway..." 
    curl -s http://localhost:8082/mcp -H "Authorization: Bearer $CONTEXT7_TOKEN" | jq '.result.tools | length' || echo "❌ Gateway not responding"
fi

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║  ✅ Deployment Complete!                    ║"
echo "║  Cost: $0 (FREE - self-hosted Vault)       ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo "Services:"
echo "  • control-plane: http://localhost:8082"
echo "  • Odoo 19:       http://localhost:8069"
echo "  • Vault:         http://localhost:8200"
echo ""
