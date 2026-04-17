$ErrorActionPreference = "Stop"

function Assert-StatusCode {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [Parameter(Mandatory = $true)]
        [int]$ExpectedStatus,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 20
        $statusCode = [int]$response.StatusCode
    } catch {
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode.value__
        } else {
            throw "[$Label] Request failed: $($_.Exception.Message)"
        }
    }

    if ($statusCode -ne $ExpectedStatus) {
        throw "[$Label] Expected HTTP $ExpectedStatus but got $statusCode"
    }

    Write-Host "[$Label] OK ($statusCode)"
}

function Assert-CommandOutputContains {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [Parameter(Mandatory = $true)]
        [string]$ExpectedText,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    $output = Invoke-Expression $Command | Out-String
    if ($LASTEXITCODE -ne 0 -or $output -notmatch [regex]::Escape($ExpectedText)) {
        throw "[$Label] Expected output to contain '$ExpectedText' but got: $output"
    }

    Write-Host "[$Label] OK ($ExpectedText)"
}

Assert-StatusCode -Url "http://localhost:8088/web/login" -ExpectedStatus 200 -Label "Nginx -> Odoo"
Assert-StatusCode -Url "http://localhost:8069/web/login" -ExpectedStatus 200 -Label "Odoo direct"

Assert-CommandOutputContains `
    -Command "docker compose -f compose.yaml -f compose.dev.yaml exec -T redis redis-cli ping" `
    -ExpectedText "PONG" `
    -Label "Redis"

Assert-CommandOutputContains `
    -Command "docker compose -f compose.yaml -f compose.dev.yaml exec -T pgbackrest pgbackrest version" `
    -ExpectedText "pgBackRest" `
    -Label "pgBackRest binary"

Write-Host "Local stack checks completed successfully."
