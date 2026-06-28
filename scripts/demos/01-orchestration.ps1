# Demo 1: End-to-end orchestration via API Gateway (SSE streaming)
$ErrorActionPreference = "Stop"
$GatewayUrl = if ($env:API_GATEWAY_URL) { $env:API_GATEWAY_URL } else { "http://localhost:8000" }

Write-Host "==> Health check"
(Invoke-RestMethod "$GatewayUrl/health") | ConvertTo-Json

Write-Host "`n==> Create conversation"
$conv = Invoke-RestMethod -Method Post -Uri "$GatewayUrl/v1/conversations" -ContentType "application/json" -Body "{}"
$convId = $conv.id
$conv | ConvertTo-Json
Write-Host "Conversation ID: $convId"

Write-Host "`n==> List registered agents"
(Invoke-RestMethod "$GatewayUrl/v1/agents") | ConvertTo-Json -Depth 5

Write-Host "`n==> Send message (SSE stream; showing raw response)"
$body = '{"content": "Analyze the tradeoffs between microservices and modular monoliths"}'
curl.exe -sN -X POST "$GatewayUrl/v1/conversations/$convId/messages" -H "Content-Type: application/json" -d $body | Select-Object -First 20

Write-Host "`n==> Conversation messages"
(Invoke-RestMethod "$GatewayUrl/v1/conversations/$convId/messages") | ConvertTo-Json -Depth 5
