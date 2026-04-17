$ErrorActionPreference = "Stop"

. "$PSScriptRoot\check-local-stack.ps1"

Assert-StatusCode -Url "http://localhost:8080" -ExpectedStatus 200 -Label "pgAdmin"
Assert-StatusCode -Url "http://localhost:3000" -ExpectedStatus 401 -Label "Obsidian auth gate"
Assert-StatusCode -Url "http://localhost:8081" -ExpectedStatus 200 -Label "Homepage lobby"

Write-Host "Admin stack checks completed successfully."
