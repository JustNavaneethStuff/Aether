# Run all Aether demos (requires: make up)
$ErrorActionPreference = "Stop"
$Dir = Split-Path -Parent $MyInvocation.MyCommand.Path

@("01-orchestration", "02-async-workflow", "03-knowledge-acquisition", "04-observability") | ForEach-Object {
    Write-Host ""
    Write-Host "########################################################"
    Write-Host "# $_"
    Write-Host "########################################################"
    & "$Dir\$_.ps1"
}
