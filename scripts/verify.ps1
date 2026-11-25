<#
.SYNOPSIS
    Smoke-test script for DevOps Project 2 on Kind (dev-cluster).
#>
$ErrorActionPreference = 'Stop'

Write-Host '=== Cluster Nodes ===' -ForegroundColor Cyan
kubectl get nodes -o wide

Write-Host "`n=== Helm Releases ===" -ForegroundColor Cyan
helm list -A

Write-Host "`n=== ArgoCD Applications ===" -ForegroundColor Cyan
kubectl get applications -n argocd

Write-Host "`n=== Ingress HTTP Checks ===" -ForegroundColor Cyan
$hosts = @(
    'localhost',
    'demo.localtest.me',
    'task-api.localtest.me',
    'grafana.localtest.me',
    'argocd.localtest.me',
    'gitops-demo.localtest.me'
)

foreach ($h in $hosts) {
    $resp = Invoke-WebRequest -Uri 'http://localhost/' -Headers @{ Host = $h } -UseBasicParsing -TimeoutSec 10
    Write-Host ("{0,-28} -> HTTP {1}" -f $h, $resp.StatusCode) -ForegroundColor Green
}

Write-Host "`n=== Task API Health & Metrics ===" -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri 'http://localhost/healthz' -Headers @{ Host = 'task-api.localtest.me' } -TimeoutSec 10
Write-Host ("Healthz: {0} (DB: {1})" -f $health.status, $health.database) -ForegroundColor Green
