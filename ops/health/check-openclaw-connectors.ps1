param(
    [string]$GatewayUrl = "http://localhost:8082/mcp",
    [string]$ObsidianToolName = "",
    [string]$ObsidianToolArgumentsJson = "{}",
    [string]$MemoryToolName = "",
    [string]$MemoryToolArgumentsJson = "{}",
    [string]$Context7LibraryName = "odoo",
    [string]$Context7Query = "How do I create a crm.lead opportunity in Odoo 19?"
)

$ErrorActionPreference = "Stop"

function Invoke-Mcp {
    param(
        [Parameter(Mandatory = $true)] [string]$Method,
        [Parameter(Mandatory = $false)] [hashtable]$Params = @{},
        [Parameter(Mandatory = $false)] [int]$Id = 1
    )

    $payloadObject = @{
        jsonrpc = "2.0"
        id = $Id
        method = $Method
        params = $Params
    }

    $payload = $payloadObject | ConvertTo-Json -Depth 20 -Compress
    return Invoke-RestMethod -Method Post -Uri $GatewayUrl -ContentType "application/json" -Body $payload
}

function Assert-ToolPresent {
    param(
        [Parameter(Mandatory = $true)] [array]$ToolList,
        [Parameter(Mandatory = $true)] [string]$ToolName
    )

    $found = $ToolList | Where-Object { $_.name -eq $ToolName }
    if (-not $found) {
        throw "Missing MCP tool in gateway: $ToolName"
    }
}

Write-Host "[1/6] Checking MCP gateway reachability at $GatewayUrl"
$toolsResponse = Invoke-Mcp -Method "tools/list" -Params @{} -Id 1
if (-not $toolsResponse.result -or -not $toolsResponse.result.tools) {
    throw "Gateway response did not include tools/list result."
}

$toolList = $toolsResponse.result.tools
Write-Host "Gateway is reachable. Tools reported: $($toolList.Count)"

Write-Host "[2/6] Verifying required bridge tools are registered"
$requiredTools = @(
    "obsidian.mcp_tools_list",
    "obsidian.mcp_call",
    "memory.mcp_tools_list",
    "memory.mcp_call",
    "context7.resolve_library_id",
    "context7.query_docs"
)

foreach ($toolName in $requiredTools) {
    Assert-ToolPresent -ToolList $toolList -ToolName $toolName
}
Write-Host "Required bridge tools are registered."

Write-Host "[3/6] Calling obsidian.mcp_tools_list and memory.mcp_tools_list"
$obsidianList = Invoke-Mcp -Method "tools/call" -Params @{ name = "obsidian.mcp_tools_list"; arguments = @{} } -Id 2
$memoryList = Invoke-Mcp -Method "tools/call" -Params @{ name = "memory.mcp_tools_list"; arguments = @{} } -Id 3

$obsidianText = $obsidianList.result.content[0].text
$memoryText = $memoryList.result.content[0].text
Write-Host "Obsidian list response:"
Write-Host $obsidianText
Write-Host "Memory list response:"
Write-Host $memoryText

Write-Host "[4/6] Calling Context7 resolve + query through gateway"
$resolve = Invoke-Mcp -Method "tools/call" -Params @{ name = "context7.resolve_library_id"; arguments = @{ library_name = $Context7LibraryName; query = $Context7Query } } -Id 4
$resolveText = $resolve.result.content[0].text
Write-Host "Context7 resolve response:"
Write-Host $resolveText

$resolvedLibraryId = $null
try {
    $resolveJson = $resolveText | ConvertFrom-Json
    if ($resolveJson.result -and $resolveJson.result[0] -and $resolveJson.result[0].libraryId) {
        $resolvedLibraryId = $resolveJson.result[0].libraryId
    }
} catch {
    $resolvedLibraryId = $null
}

if ($resolvedLibraryId) {
    $query = Invoke-Mcp -Method "tools/call" -Params @{ name = "context7.query_docs"; arguments = @{ library_id = $resolvedLibraryId; query = $Context7Query } } -Id 5
    Write-Host "Context7 query response:"
    Write-Host $query.result.content[0].text
} else {
    Write-Warning "Could not parse a library_id from resolve result. Skipping context7.query_docs smoke call."
}

Write-Host "[5/6] Optional concrete tool call: Obsidian"
if ($ObsidianToolName -ne "") {
    $obsArgs = $ObsidianToolArgumentsJson | ConvertFrom-Json -AsHashtable
    $obsCall = Invoke-Mcp -Method "tools/call" -Params @{ name = "obsidian.mcp_call"; arguments = @{ tool_name = $ObsidianToolName; arguments = $obsArgs } } -Id 6
    Write-Host "Obsidian concrete call response:"
    Write-Host $obsCall.result.content[0].text
} else {
    Write-Host "Skipped Obsidian concrete tool call. Provide -ObsidianToolName to enable it."
}

Write-Host "[6/6] Optional concrete tool call: Memory"
if ($MemoryToolName -ne "") {
    $memArgs = $MemoryToolArgumentsJson | ConvertFrom-Json -AsHashtable
    $memCall = Invoke-Mcp -Method "tools/call" -Params @{ name = "memory.mcp_call"; arguments = @{ tool_name = $MemoryToolName; arguments = $memArgs } } -Id 7
    Write-Host "Memory concrete call response:"
    Write-Host $memCall.result.content[0].text
} else {
    Write-Host "Skipped Memory concrete tool call. Provide -MemoryToolName to enable it."
}

Write-Host "OpenClaw connector checks completed."
