#!/usr/bin/env bash
# Demo 4: Observability endpoints and Grafana
set -euo pipefail

ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:8001}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"

echo "==> Service health"
curl -s "$ORCHESTRATOR_URL/health" | python -m json.tool
curl -s "$ORCHESTRATOR_URL/ready" | python -m json.tool

echo ""
echo "==> Prometheus metrics sample (orchestrator)"
curl -s "$ORCHESTRATOR_URL/metrics" | head -n 15

echo ""
echo "==> Observability stack URLs (start with: make up-obs)"
echo "    Prometheus: $PROMETHEUS_URL"
echo "    Grafana:    $GRAFANA_URL (admin / admin)"
echo "    Dashboard:  Aether Phase 3 — agent latency, LLM cost, evaluations, approvals"

if curl -sf "$PROMETHEUS_URL/-/healthy" >/dev/null 2>&1; then
  echo ""
  echo "==> Prometheus is up"
  curl -s "$PROMETHEUS_URL/api/v1/label/__name__/values" | python -m json.tool | head -n 20
else
  echo ""
  echo "Prometheus not running. Start observability profile: make up-obs"
fi
