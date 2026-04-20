#!/bin/bash

################################################################################
# Emergency Token Revocation Script
# Purpose: Immediately revoke and rotate tokens in case of compromise
# Usage: ./emergency-revoke-token.sh [obsidian|memory|context7|all]
# Time: ~30 seconds
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"
DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_FILE:-compose.yaml}"
TIMESTAMP=$(date +%s)
LOG_FILE="emergency-revocation-${TIMESTAMP}.log"

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

generate_token() {
    # Generate cryptographic 32-character token
    openssl rand -hex 16 | tr -d '\n'
}

check_vault_connection() {
    log_info "Checking Vault connectivity..."
    
    if ! curl -s -f "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; then
        log_error "Cannot connect to Vault at $VAULT_ADDR"
        log_error "Please ensure Vault is running: docker-compose up -d vault"
        exit 1
    fi
    
    log_success "Vault is reachable"
}

check_vault_token() {
    log_info "Checking Vault authentication..."
    
    if [ -z "$VAULT_TOKEN" ]; then
        log_error "VAULT_TOKEN environment variable not set"
        log_error "Export your Vault token: export VAULT_TOKEN='...'"
        exit 1
    fi
    
    # Verify token is valid
    if ! curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        "$VAULT_ADDR/v1/auth/token/lookup-self" > /dev/null 2>&1; then
        log_error "Vault token is invalid or expired"
        exit 1
    fi
    
    log_success "Vault authentication successful"
}

revoke_token() {
    local token_type=$1
    local service_name="$token_type-mcp"
    
    log_info "[1/4] Generating new token for $token_type..."
    local new_token=$(generate_token)
    log_success "Generated new token: ${new_token:0:8}...${new_token: -8}"
    
    log_info "[2/4] Updating Vault with new token..."
    
    # Update staging vault secret
    local staging_result=$(curl -s -X POST \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -d "{\"data\":{\"token\":\"$new_token\"}}" \
        "$VAULT_ADDR/v1/secret/data/staging/$token_type" | jq -r '.data.data.token')
    
    if [ "$staging_result" = "$new_token" ]; then
        log_success "   ✅ Updated staging Vault"
    else
        log_error "Failed to update staging Vault"
        return 1
    fi
    
    # Update production vault secret
    local prod_result=$(curl -s -X POST \
        -H "X-Vault-Token: $VAULT_TOKEN" \
        -d "{\"data\":{\"token\":\"$new_token\"}}" \
        "$VAULT_ADDR/v1/secret/data/production/$token_type" | jq -r '.data.data.token')
    
    if [ "$prod_result" = "$new_token" ]; then
        log_success "   ✅ Updated production Vault"
    else
        log_error "Failed to update production Vault"
        return 1
    fi
    
    log_info "[3/4] Exporting new token to environment..."
    export $(echo "$token_type" | tr '[:lower:]' '[:upper:]')_TOKEN="$new_token"
    log_success "   ✅ New token exported to environment"
    
    log_info "[4/4] Restarting $service_name service..."
    
    # Restart the affected service
    if docker-compose -f "$DOCKER_COMPOSE_FILE" restart "$service_name" > /dev/null 2>&1; then
        log_success "   ✅ Service restarted successfully"
    else
        log_warning "   ⚠️  Could not restart service (may not be running)"
    fi
    
    # Wait for service to stabilize
    sleep 2
    
    # Verify service is up
    if docker-compose -f "$DOCKER_COMPOSE_FILE" ps "$service_name" 2>/dev/null | grep -q "Up"; then
        log_success "   ✅ Service is running"
    else
        log_warning "   ⚠️  Service may not be running, check manually"
    fi
    
    # Output new token
    echo ""
    echo -e "${GREEN}✅ Emergency revocation complete!${NC}"
    echo -e "${BLUE}🔑 New token for $token_type:${NC}"
    echo "$new_token"
    echo ""
    echo -e "${YELLOW}📋 Next steps:${NC}"
    echo "   1. Update GitHub Actions secrets with new token"
    echo "   2. Push code to trigger new deployment"
    echo "   3. Verify health checks pass: ./ops/health/check-vault-health.sh"
    echo "   4. Document incident and communicate to team"
    echo ""
    echo -e "${BLUE}📝 Log file: $LOG_FILE${NC}"
}

################################################################################
# Main Execution
################################################################################

main() {
    local token_type=${1:-all}
    
    # Validate input
    case "$token_type" in
        obsidian|memory|context7|all)
            ;;
        *)
            log_error "Invalid token type: $token_type"
            echo ""
            echo "Usage: ./emergency-revoke-token.sh [obsidian|memory|context7|all]"
            echo ""
            echo "Examples:"
            echo "  ./emergency-revoke-token.sh obsidian   # Revoke obsidian token only"
            echo "  ./emergency-revoke-token.sh memory     # Revoke memory token only"
            echo "  ./emergency-revoke-token.sh context7   # Revoke context7 token only"
            echo "  ./emergency-revoke-token.sh all        # Revoke ALL tokens"
            exit 1
            ;;
    esac
    
    log_info "Emergency Token Revocation Started"
    log_info "Timestamp: $(date)"
    log_info "Vault Address: $VAULT_ADDR"
    echo ""
    
    # Pre-flight checks
    check_vault_connection
    check_vault_token
    echo ""
    
    # Confirm user intent
    if [ "$token_type" != "all" ]; then
        log_warning "You are about to revoke the $token_type token!"
    else
        log_warning "⚠️  YOU ARE ABOUT TO REVOKE ALL TOKENS!"
        log_warning "This will temporarily disrupt services."
    fi
    
    echo -e "${YELLOW}Are you sure? (yes/no):${NC}"
    read -r confirmation
    
    if [ "$confirmation" != "yes" ]; then
        log_info "Aborted - no changes made"
        exit 0
    fi
    
    # Revoke specified tokens
    if [ "$token_type" = "all" ]; then
        revoke_token "obsidian"
        echo ""
        revoke_token "memory"
        echo ""
        revoke_token "context7"
    else
        revoke_token "$token_type"
    fi
    
    log_info "Emergency revocation procedure complete"
}

# Run main function
main "$@"
