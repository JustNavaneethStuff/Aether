#!/usr/bin/env bash
# Demo 3: Knowledge acquisition — ingest, search, crawl trigger, dataset retrieval
set -euo pipefail

GATEWAY_URL="${API_GATEWAY_URL:-http://localhost:8000}"
KNOWLEDGE_URL="${KNOWLEDGE_SERVICE_URL:-http://localhost:8004}"

echo "==> Ingest a document"
curl -s -X POST "$GATEWAY_URL/v1/knowledge/documents" \
  -H "Content-Type: application/json" \
  -d '{"content": "Aether is a multi-agent orchestration platform with replaceable agents and RAG support.", "metadata": {"source": "demo"}}' \
  | python -m json.tool

echo ""
echo "==> Search knowledge base"
curl -s -X POST "$GATEWAY_URL/v1/knowledge/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "multi-agent orchestration", "top_k": 3}' \
  | python -m json.tool

echo ""
echo "==> Trigger crawl acquisition (local backend — accepted, no external crawl)"
ACQUIRE=$(curl -s -X POST "$KNOWLEDGE_URL/v1/acquire" \
  -H "Content-Type: application/json" \
  -d '{"seed_urls": ["https://example.com"], "max_depth": 1}')
echo "$ACQUIRE" | python -m json.tool
CRAWL_ID=$(echo "$ACQUIRE" | python -c "import sys,json; print(json.load(sys.stdin)['crawl_id'])")

echo ""
echo "==> Retrieve dataset by crawl ID"
curl -s "$KNOWLEDGE_URL/v1/datasets/$CRAWL_ID?q=orchestration&top_k=5" | python -m json.tool
