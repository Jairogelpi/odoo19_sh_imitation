#!/bin/bash
# emergency-revoke-token.sh - Revoke compromised token and generate new one
# Usage: ./emergency-revoke-token.sh obsidian
# Cost: FREE

set -e

SERVICE=${1:-""}
if [ -z "$SERVICE" ]; then
    echo "❌ Service not specified"
    echo "Usage: $0 [obsidian|memory|context7|all]"
    exit 1
fi

VAULT_TOKEN=${VAULT_TOKEN:-""}
if [ -z "$VAULT_TOKEN" ]; then
    echo "❌ VAULT_TOKEN not set"
    echo "Usage: export VAULT_TOKEN=<token> && $0 obsidian"
    exit 1
fi

VAULT_ADDR=${VAULT_ADDR:-"http://localhost:8200"}

echo "╔════════════════════════════════════════════╗"
echo "║  Emergency Token Revocation & Regeneration ║"
echo "║  Service: $SERVICE"
echo "╚════════════════════════════════════════════╝"
echo ""

# Function to revoke and regenerate token
revoke_token() {
    local svc=$1
    echo "[1/4] Generating new token for $svc..."
    
    # Generate new token
    NEW_TOKEN=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-32)
    
    echo "[2/4] Updating Vault with new token..."
    for env in staging production; do
        TOKEN_FIELD="${svc}"
        curl -s -X POST \
            -H "X-Vault-Token: $VAULT_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{\"data\": {\"$TOKEN_FIELD\": \"$NEW_TOKEN\"}}" \
            "$VAULT_ADDR/v1/secret/data/openclaw/mcp-tokens-$env" > /dev/null
        echo "   ✅ Updated $env"
    done
    
    echo "[3/4] Exporting new token to environment..."
    export OPENCLAW_${svc^^}_MCP_TOKEN="$NEW_TOKEN"
    
    echo "[4/4] Restarting service..."
    docker compose restart "openclaw-${svc}-mcp" 2>/dev/null || echo "   ⚠️  Service not running locally"
    
    echo ""
    echo "✅ Emergency revocation complete!"
    echo "🔑 New token: $(echo $NEW_TOKEN | cut -c1-10)..."
    echo "📋 Next steps:"
    echo "   1. Update GitHub Actions secrets"
    echo "   2. Push code to trigger new deployment"
    echo "   3. Verify health checks pass"
}

# Handle all services or specific service
if [ "$SERVICE" = "all" ]; then
    revoke_token "obsidian"
    sleep 2
    revoke_token "memory"
    sleep 2
    revoke_token "context7"
else
    revoke_token "$SERVICE"
fi

echo ""
echo "⚠️  SECURITY NOTE:"
echo "   • Delete this script after use"
echo "   • Never log tokens in plain text"
echo "   • Audit who has access to Vault"
echo ""
