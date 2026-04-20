# Generate Secure Random Tokens for OpenClaw MCP Services
# Usage: powershell -ExecutionPolicy Bypass -File .\generate-tokens.ps1

function New-SecureRandomToken {
    param([int]$Length = 32)
    
    # Use RNGCryptoServiceProvider for cryptographically secure randomness
    $rng = New-Object System.Security.Cryptography.RNGCryptoServiceProvider
    $bytes = New-Object 'System.Byte[]' $Length
    $rng.GetBytes($bytes)
    
    # Convert bytes to base64-like string (alphanumeric + punctuation)
    $token = [System.Convert]::ToBase64String($bytes) -replace '[^a-zA-Z0-9_-]', ''
    $token = $token.Substring(0, [Math]::Min($Length, $token.Length))
    
    # If too short, regenerate
    if ($token.Length -lt $Length) {
        return New-SecureRandomToken -Length $Length
    }
    
    return $token
}

Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  OpenClaw MCP Token Generator - 2026-04-17 ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Generate three tokens
$token_obsidian = New-SecureRandomToken 32
$token_memory = New-SecureRandomToken 32
$token_context7 = New-SecureRandomToken 32

Write-Host "✓ Generated 3 secure random tokens (32 chars each, cryptographically random)" -ForegroundColor Green
Write-Host ""

# Display tokens
Write-Host "┌─ OBSIDIAN MCP TOKEN ─────────────────────────┐" -ForegroundColor Yellow
Write-Host "│ $token_obsidian │" -ForegroundColor White
Write-Host "└──────────────────────────────────────────────┘" -ForegroundColor Yellow
Write-Host ""

Write-Host "┌─ MEMORY MCP TOKEN ───────────────────────────┐" -ForegroundColor Yellow
Write-Host "│ $token_memory │" -ForegroundColor White
Write-Host "└──────────────────────────────────────────────┘" -ForegroundColor Yellow
Write-Host ""

Write-Host "┌─ CONTEXT7 MCP TOKEN ─────────────────────────┐" -ForegroundColor Yellow
Write-Host "│ $token_context7 │" -ForegroundColor White
Write-Host "└──────────────────────────────────────────────┘" -ForegroundColor Yellow
Write-Host ""

# Create .env.prod with these tokens
$env_content = @"
# OpenClaw Production Environment
# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
# IMPORTANT: These tokens are SENSITIVE. Treat as secrets.

# MCP Service Authentication Tokens (REQUIRED - change before deploying)
OPENCLAW_OBSIDIAN_MCP_TOKEN=$token_obsidian
OPENCLAW_MEMORY_MCP_TOKEN=$token_memory
OPENCLAW_CONTEXT7_MCP_TOKEN=$token_context7

# Internal MCP Service URLs (do not change)
OPENCLAW_OBSIDIAN_MCP_URL=http://obsidian-mcp:8090/mcp
OPENCLAW_MEMORY_MCP_URL=http://memory-mcp:8091/mcp
OPENCLAW_CONTEXT7_MCP_URL=http://context7-mcp:8092/mcp

# Odoo Configuration
ODOO_DB_NAME=odoo19
ODOO_DB_USER=odoo
ODOO_POSTGRES_PASSWORD=odoo

# Redis Configuration
REDIS_PASSWORD=redis

# Control-Plane / OpenRouter
OPENROUTER_API_KEY=<insert-your-openrouter-key-here>
"@

# Save to .env.prod
$env_prod_path = ".\env.prod"
if (Test-Path $env_prod_path) {
    $backup_path = ".\env.prod.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Copy-Item $env_prod_path $backup_path
    Write-Host "⚠ Backed up existing .env.prod to $backup_path" -ForegroundColor Magenta
}

$env_content | Out-File -FilePath $env_prod_path -Encoding UTF8 -Force
Write-Host "✓ Created .env.prod with rotated tokens" -ForegroundColor Green
Write-Host ""

# Create context file for later use
$context_file = ".\tokens_context.ps1"
@"
# Token values for Docker deployment (generated $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
`$env:OPENCLAW_OBSIDIAN_MCP_TOKEN='$token_obsidian'
`$env:OPENCLAW_MEMORY_MCP_TOKEN='$token_memory'
`$env:OPENCLAW_CONTEXT7_MCP_TOKEN='$token_context7'
"@ | Out-File -FilePath $context_file -Encoding UTF8 -Force
Write-Host "✓ Saved token context to tokens_context.ps1 (for deployment use)" -ForegroundColor Green
Write-Host ""

# Display next steps
Write-Host "╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           NEXT STEPS                       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. STORE TOKENS SECURELY (required before production deploy):"
Write-Host "   - HashiCorp Vault, AWS Secrets Manager, or similar secure vault"
Write-Host "   - DO NOT commit .env.prod to Git repository"
Write-Host ""
Write-Host "2. LOCAL TESTING (optional - validate tokens work):"
Write-Host "   .\& '.\tokens_context.ps1'; docker compose -f compose.yaml -f compose.admin.yaml up -d --build"
Write-Host ""
Write-Host "3. RUN HEALTH CHECK (post-deployment validation):"
Write-Host "   .\& '.\tokens_context.ps1'; powershell -ExecutionPolicy Bypass -File '.\ops\health\check-openclaw-connectors.ps1'"
Write-Host ""
Write-Host "4. PRODUCTION DEPLOYMENT:"
Write-Host "   - Load .env.prod variables from your secret store"
Write-Host "   - Run: docker compose -f compose.yaml -f compose.prod.yaml up -d --build"
Write-Host ""

Write-Host "⚠ SECURITY REMINDER:" -ForegroundColor Red
Write-Host "  • Never commit .env.prod to version control"
Write-Host "  • Rotate tokens quarterly or after team changes"
Write-Host "  • Delete tokens_context.ps1 from repo after final deployment"
Write-Host ""
