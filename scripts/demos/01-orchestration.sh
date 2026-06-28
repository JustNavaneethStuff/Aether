#!/usr/bin/env bash
# Demo 1: End-to-end orchestration via API Gateway (SSE streaming)
set -euo pipefail

GATEWAY_URL="${API_GATEWAY_URL:-http://localhost:8000}"

echo "==> Health check"
curl -s "$GATEWAY_URL/health" | python -m json.tool

echo ""
echo "==> Create conversation"
CONV=$(curl -s -X POST "$GATEWAY_URL/v1/conversations" -H "Content-Type: application/json" -d '{}')
CONV_ID=$(echo "$CONV" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "$CONV" | python -m json.tool
echo "Conversation ID: $CONV_ID"

echo ""
echo "==> List registered agents"
curl -s "$GATEWAY_URL/v1/agents" | python -m json.tool

echo ""
echo "==> Send message (SSE stream; first 20 lines)"
curl -sN -X POST "$GATEWAY_URL/v1/conversations/$CONV_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{"content": "Analyze the tradeoffs between microservices and modular monoliths"}' | head -n 20

echo ""
echo "==> Conversation messages"
curl -s "$GATEWAY_URL/v1/conversations/$CONV_ID/messages" | python -m json.tool
