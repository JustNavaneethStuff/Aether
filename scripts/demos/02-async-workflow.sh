#!/usr/bin/env bash
# Demo 2: Async workflow submission (local task queue runs inline by default)
set -euo pipefail

GATEWAY_URL="${API_GATEWAY_URL:-http://localhost:8000}"
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:8001}"

echo "==> Create conversation"
CONV=$(curl -s -X POST "$GATEWAY_URL/v1/conversations" -H "Content-Type: application/json" -d '{}')
CONV_ID=$(echo "$CONV" | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Conversation ID: $CONV_ID"

echo ""
echo "==> Submit async workflow (TASK_QUEUE_BACKEND=local executes inline)"
curl -s -X POST "$ORCHESTRATOR_URL/v1/orchestrate/async" \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\": \"$CONV_ID\", \"message\": \"Summarize the benefits of event-driven architecture\"}" \
  | python -m json.tool

echo ""
echo "==> Job completion events are published on the aether:events Redis stream"
echo "    Event types: job.submitted, job.completed"
