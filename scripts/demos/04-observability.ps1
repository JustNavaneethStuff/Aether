# Demo 4: Observability endpoints and Grafana
$ErrorActionPreference = "Stop"
$OrchestratorUrl = if ($env:ORCHESTRATOR_URL) { $env:ORCHESTRATOR_URL } else { "http://localhost:8001" }
$PrometheusUrl = if ($env:PROMETHEUS_URL) { $env:PROMETHEUS_URL } else { "http://localhost:9090" }
$GrafanaUrl = if ($env:GRAFANA_URL) { $env:GRAFANA_URL } else { "http://localhost:3000" }

Write-Host "==> Service health"
(Invoke-RestMethod "$OrchestratorUrl/health") | ConvertTo-Json
(Invoke-RestMethod "$OrchestratorUrl/ready") | ConvertTo-Json

Write-Host "`n==> Prometheus metrics sample (orchestrator)"
(Invoke-WebRequest "$OrchestratorUrl/metrics").Content.Split("`n") | Select-Object -First 15

Write-Host "`n==> Observability stack URLs (start with: make up-obs)"
Write-Host "    Prometheus: $PrometheusUrl"
Write-Host "    Grafana:    $GrafanaUrl (admin / admin)"

try {
    Invoke-RestMethod "$PrometheusUrl/-/healthy" | Out-Null
    Write-Host "`n==> Prometheus is up"
} catch {
    Write-Host "`nPrometheus not running. Start observability profile: make up-obs"
}
