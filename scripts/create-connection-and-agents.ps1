# 1. Crear conexion AI Search en proj-default
# 2. Crear agentes
# Ejecutar desde la raiz del proyecto

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
if (Test-Path (Join-Path $projectRoot "infra")) { Set-Location $projectRoot }
$rg = "rg-summit-dspm-ai-resources-app"
$sub = "e52da50f-bfae-4cbf-9188-68d2e5833dd4"
$searchResourceId = "/subscriptions/$sub/resourceGroups/$rg/providers/Microsoft.Search/searchServices/srch-customerchatbotasmzl"

Write-Host "Paso 1: Creando conexion AI Search en proj-default..." -ForegroundColor Cyan
az deployment group create `
  --resource-group $rg `
  --template-file scripts/create-ai-search-connection.bicep `
  --parameters searchServiceResourceId=$searchResourceId `
  --parameters searchServiceLocation="westus" `
  -o none

Write-Host "Conexion creada. Esperando 10 segundos..." -ForegroundColor Green
Start-Sleep -Seconds 10

Write-Host "`nPaso 2: Creando agentes..." -ForegroundColor Cyan
& (Join-Path $PSScriptRoot "create-agents-simple.ps1")
