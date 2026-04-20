#!/bin/bash

################################################################################
# Vault Health Monitoring Script
# Purpose: Monitor Vault health, service status, and token validity
# Usage: ./check-vault-health.sh [--detailed] [--slack-webhook URL]
# Recommended: Run every 15 minutes via cron
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-}"
DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_FILE:-compose.yaml}"
DETAILED_MODE=false
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="logs/vault-health-$(date +%Y%m%d).log"

# Health check result counters
PASSED=0
FAILED=0
WARNINGS=0

################################################################################
# Logging Functions
################################################################################

log_info() {
    echo -e "${BLUE}ℹ️  $@${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✅ $@${NC}" | tee -a "$LOG_FILE"
    ((PASSED++))
}

log_warning() {
    echo -e "${YELLOW}⚠️  $@${NC}" | tee -a "$LOG_FILE"
    ((WARNINGS++))
}

log_error() {
    echo -e "${RED}❌ $@${NC}" | tee -a "$LOG_FILE"
    ((FAILED++))
}

log_detail() {
    if [ "$DETAILED_MODE" = true ]; then
        echo -e "${CYAN}   ➜ $@${NC}" | tee -a "$LOG_FILE"
    fi
}

ensure_log_dir() {
    mkdir -p logs
}

################################################################################
# Health Check Functions
################################################################################

check_vault_connectivity() {
    log_info "[1/5] Checking Vault connectivity..."
    
    if curl -s -m 5 -f "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; then
        log_success "Vault is reachable at $VAULT_ADDR"
    elif curl -s -m 5 "$VAULT_ADDR/v1/sys/health" > /dev/null 2>&1; then
        # Vault might be sealed, which still counts as reachable
        log_success "Vault is reachable (may be sealed)"
    else
        log_error "Cannot reach Vault at $VAULT_ADDR"
        log_detail "Check: docker-compose ps vault"
        log_detail "Fix: docker-compose up -d vault"
        return 1
    fi
    
    echo ""
}

check_vault_status() {
    log_info "[2/5] Checking Vault status..."
    
    local status_response=$(curl -s -m 5 "$VAULT_ADDR/v1/sys/health" 2>/dev/null || echo "{}")
    local sealed=$(echo "$status_response" | jq -r '.sealed // "unknown"' 2>/dev/null || echo "unknown")
    local initialized=$(echo "$status_response" | jq -r '.initialized // "unknown"' 2>/dev/null || echo "unknown")
    
    case "$sealed" in
        true)
            log_warning "Vault is SEALED"
            log_detail "Action: Unseal with: docker exec vault vault operator unseal <KEY>"
            return 1
            ;;
        false)
            log_success "Vault is unsealed"
            log_detail "Initialized: $initialized"
            ;;
        *)
            log_warning "Could not determine Vault seal status"
            return 1
            ;;
    esac
    
    echo ""
}

check_stored_tokens() {
    log_info "[3/5] Checking stored tokens..."
    
    if [ -z "$VAULT_TOKEN" ]; then
        log_warning "VAULT_TOKEN not set - skipping token verification"
        log_detail "Set token: export VAULT_TOKEN='...'"
        return 0
    fi
    
    local staging_obsidian=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        "$VAULT_ADDR/v1/secret/data/staging/obsidian" 2>/dev/null | jq -r '.data.data.token // "NOT_FOUND"')
    
    local prod_context7=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        "$VAULT_ADDR/v1/secret/data/production/context7" 2>/dev/null | jq -r '.data.data.token // "NOT_FOUND"')
    
    if [ "$staging_obsidian" != "NOT_FOUND" ] && [ ${#staging_obsidian} -gt 0 ]; then
        log_success "Staging tokens exist"
        log_detail "Obsidian: ${staging_obsidian:0:8}...${staging_obsidian: -8}"
    else
        log_warning "Could not verify staging tokens"
    fi
    
    if [ "$prod_context7" != "NOT_FOUND" ] && [ ${#prod_context7} -gt 0 ]; then
        log_success "Production tokens exist"
        log_detail "Context7: ${prod_context7:0:8}...${prod_context7: -8}"
    else
        log_warning "Could not verify production tokens"
    fi
    
    echo ""
}

check_mcp_services() {
    log_info "[4/5] Checking MCP services..."
    
    local services=("obsidian-mcp" "memory-mcp" "context7-mcp" "control-plane")
    local service_count=0
    local error_count=0
    
    for service in "${services[@]}"; do
        local container_name="odoo19_${service}"
        
        # Try to find container (alternating naming patterns)
        if docker ps --format "table {{.Names}}" | grep -q "$service"; then
            container_name=$(docker ps --format "table {{.Names}}" | grep "$service" | head -n1)
        fi
        
        if docker ps --filter "name=$service" | grep -q "Up"; then
            log_detail "   ✅ $service: running"
            ((service_count++))
        elif docker ps -a --filter "name=$service" | grep -q "$service"; then
            log_detail "   ⚠️  $service: not running"
            ((error_count++))
        else
            log_detail "   ❓ $service: not found"
        fi
    done
    
    if [ $error_count -eq 0 ]; then
        log_success "All MCP services are up ($service_count/${#services[@]})"
    else
        log_warning "Some MCP services down ($service_count running, $error_count down)"
        log_detail "Restart: docker-compose restart $(echo \"${services[@]}\" | tr ' ' ',')"
    fi
    
    echo ""
}

check_token_authentication() {
    log_info "[5/5] Checking token authentication..."
    
    if [ -z "$VAULT_TOKEN" ]; then
        log_warning "VAULT_TOKEN not set - skipping authentication test"
        return 0
    fi
    
    local auth_result=$(curl -s -H "X-Vault-Token: $VAULT_TOKEN" \
        "$VAULT_ADDR/v1/auth/token/lookup-self" 2>/dev/null | jq -r '.data.id // "NOT_FOUND"' 2>/dev/null || echo "NOT_FOUND")
    
    if [ "$auth_result" != "NOT_FOUND" ] && [ ${#auth_result} -gt 0 ]; then
        log_success "Token authentication working"
        log_detail "Token ID: ${auth_result:0:8}...${auth_result: -8}"
    else
        log_error "Token authentication failed"
        log_detail "The stored VAULT_TOKEN appears to be invalid or expired"
        log_detail "Action: Generate new token with emergency-revoke-token.sh"
        return 1
    fi
    
    echo ""
}

################################################################################
# Summary & Alerting
################################################################################

print_summary() {
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${PURPLE}📊 VAULT HEALTH SUMMARY${NC}"
    echo -e "${PURPLE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    local total=$((PASSED + FAILED + WARNINGS))
    
    echo -e "${GREEN}✅ Passed: $PASSED${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Warnings: $WARNINGS${NC}"
    fi
    if [ $FAILED -gt 0 ]; then
        echo -e "${RED}❌ Failed: $FAILED${NC}"
    fi
    
    echo ""
    
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}🟢 SYSTEM STATUS: HEALTHY${NC}"
    elif [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}🟡 SYSTEM STATUS: DEGRADED (warnings)${NC}"
    else
        echo -e "${RED}🔴 SYSTEM STATUS: UNHEALTHY${NC}"
    fi
    
    echo ""
    echo -e "${CYAN}Timestamp: $TIMESTAMP${NC}"
    echo -e "${CYAN}Log file: $LOG_FILE${NC}"
    
    echo ""
}

send_slack_alert() {
    if [ -z "$SLACK_WEBHOOK" ]; then
        return
    fi
    
    log_info "Sending Slack alert..."
    
    local status_icon="🟢"
    local status_text="HEALTHY"
    local status_color="good"
    
    if [ $FAILED -gt 0 ]; then
        status_icon="🔴"
        status_text="UNHEALTHY"
        status_color="danger"
    elif [ $WARNINGS -gt 0 ]; then
        status_icon="🟡"
        status_text="DEGRADED"
        status_color="warning"
    fi
    
    local payload=$(cat <<EOF
{
    "attachments": [{
        "color": "$status_color",
        "title": "$status_icon Vault Health Check - $status_text",
        "text": "Vault health check completed",
        "fields": [
            {"title": "Status", "value": "$status_text", "short": true},
            {"title": "Passed", "value": "$PASSED", "short": true},
            {"title": "Warnings", "value": "$WARNINGS", "short": true},
            {"title": "Failed", "value": "$FAILED", "short": true},
            {"title": "Timestamp", "value": "$TIMESTAMP", "short": false}
        ]
    }]
}
EOF
)
    
    curl -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK" > /dev/null 2>&1 || log_warning "Could not send Slack alert"
}

################################################################################
# Main Execution
################################################################################

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --detailed)
                DETAILED_MODE=true
                shift
                ;;
            --slack-webhook)
                SLACK_WEBHOOK="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    ensure_log_dir
    
    echo ""
    log_info "Vault Health Check Started"
    log_info "Vault Address: $VAULT_ADDR"
    echo ""
    
    # Run health checks
    check_vault_connectivity || true
    check_vault_status || true
    check_stored_tokens
    check_mcp_services
    check_token_authentication || true
    
    # Print summary and alert
    print_summary
    send_slack_alert
    
    # Exit code
    if [ $FAILED -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

# Run main function
main "$@"
