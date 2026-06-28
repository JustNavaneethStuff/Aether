# Demo 3: Knowledge acquisition — ingest, search, crawl trigger, dataset retrieval
$ErrorActionPreference = "Stop"
$GatewayUrl = if ($env:API_GATEWAY_URL) { $env:API_GATEWAY_URL } else { "http://localhost:8000" }
$KnowledgeUrl = if ($env:KNOWLEDGE_SERVICE_URL) { $env:KNOWLEDGE_SERVICE_URL } else { "http://localhost:8004" }

Write-Host "==> Ingest a document"
$doc = '{"content": "Aether is a multi-agent orchestration platform with replaceable agents and RAG support.", "metadata": {"source": "demo"}}'
Invoke-RestMethod -Method Post -Uri "$GatewayUrl/v1/knowledge/documents" -ContentType "application/json" -Body $doc | ConvertTo-Json

Write-Host "`n==> Search knowledge base"
$search = '{"query": "multi-agent orchestration", "top_k": 3}'
Invoke-RestMethod -Method Post -Uri "$GatewayUrl/v1/knowledge/search" -ContentType "application/json" -Body $search | ConvertTo-Json -Depth 5

Write-Host "`n==> Trigger crawl acquisition (local backend)"
$acquire = Invoke-RestMethod -Method Post -Uri "$KnowledgeUrl/v1/acquire" -ContentType "application/json" -Body '{"seed_urls": ["https://example.com"], "max_depth": 1}'
$acquire | ConvertTo-Json
$crawlId = $acquire.crawl_id

Write-Host "`n==> Retrieve dataset by crawl ID"
Invoke-RestMethod -Uri "$KnowledgeUrl/v1/datasets/$crawlId?q=orchestration&top_k=5" | ConvertTo-Json -Depth 5
