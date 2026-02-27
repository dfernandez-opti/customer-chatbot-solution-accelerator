# Ver logs del backend (api-customerchatbotasmzl)
# Como az CLI falla por purview, usa Azure Portal o este script con Az PowerShell

param(
    [string]$ResourceGroup = "rg-summit-dspm-ai-resources-app",
    [string]$BackendApp = "api-customerchatbotasmzl",
    [switch]$OpenPortal  # Abre el portal en el navegador
)

$SubscriptionId = "e52da50f-bfae-4cbf-9188-68d2e5833dd4"

Write-Host "=== Ver logs del backend ===" -ForegroundColor Cyan
Write-Host ""

# URL al recurso en Azure Portal (desde ahí: Monitoring -> Log stream)
$logStreamUrl = "https://portal.azure.com/#@/resource/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.Web/sites/$BackendApp/overview"
Write-Host "Log Stream (tiempo real):" -ForegroundColor Yellow
Write-Host "  $logStreamUrl"
Write-Host ""

# URL a Application Insights (si está configurado)
$appInsightsUrl = "https://portal.azure.com/#@/resource/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.Web/sites/$BackendApp/monitor"
Write-Host "Monitoring / Application Insights:" -ForegroundColor Yellow
Write-Host "  $appInsightsUrl"
Write-Host ""

Write-Host "Pasos manuales:" -ForegroundColor Green
Write-Host "  1. Azure Portal -> api-customerchatbotasmzl"
Write-Host "  2. Monitoring -> Log stream (para ver logs en vivo)"
Write-Host "  3. O Monitoring -> App Service logs -> Application Logging (habilitar si no está)"
Write-Host ""

# Probar health del backend
Write-Host "Estado del backend:" -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "https://$BackendApp.azurewebsites.net/health" -ErrorAction Stop
    $health | ConvertTo-Json -Depth 2
} catch {
    Write-Host "  Error al conectar: $_" -ForegroundColor Red
}

if ($OpenPortal) {
    Start-Process $logStreamUrl
}
