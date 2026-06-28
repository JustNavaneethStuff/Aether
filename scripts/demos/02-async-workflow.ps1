# Demo 2: Async workflow submission (local task queue runs inline by default)
$ErrorActionPreference = "Stop"
$GatewayUrl = if ($env:API_GATEWAY_URL) { $env:API_GATEWAY_URL } else { "http://localhost:8000" }
$OrchestratorUrl = if ($env:ORCHESTRATOR_URL) { $env:ORCHESTRATOR_URL } else { "http://localhost:8001" }

Write-Host "==> Create conversation"
$conv = Invoke-RestMethod -Method Post -Uri "$GatewayUrl/v1/conversations" -ContentType "application/json" -Body "{}"
$convId = $conv.id
Write-Host "Conversation ID: $convId"

Write-Host "`n==> Submit async workflow (TASK_QUEUE_BACKEND=local executes inline)"
$body = @{ conversation_id = $convId; message = "Summarize the benefits of event-driven architecture" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "$OrchestratorUrl/v1/orchestrate/async" -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 6

Write-Host "`nJob completion events are published on the aether:events Redis stream (job.submitted, job.completed)"
