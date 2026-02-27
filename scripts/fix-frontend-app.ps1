# Corrige configuración del frontend (app-customerchatbotasmzl) - Application Error
# Usa Az PowerShell (no az CLI). Ejecutar: .\scripts\fix-frontend-app.ps1

param(
    [string]$ResourceGroup = "rg-summit-dspm-ai-resources-app",
    [string]$FrontendApp = "app-customerchatbotasmzl",
    [string]$BackendUrl = "https://api-customerchatbotasmzl.azurewebsites.net"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Corrigiendo frontend (Application Error) ===" -ForegroundColor Cyan
Write-Host "App: $FrontendApp | API: $BackendUrl" -ForegroundColor Gray

# Az PowerShell
$modules = @("Az.Accounts", "Az.Websites")
foreach ($m in $modules) {
    if (-not (Get-Module -ListAvailable -Name $m)) {
        Write-Host "Instalando $m..." -ForegroundColor Yellow
        Install-Module -Name $m -Scope CurrentUser -Force -AllowClobber
    }
}
Import-Module Az.Websites -ErrorAction Stop

Connect-AzAccount -ErrorAction Stop | Out-Null

# Obtener settings actuales
$webApp = Get-AzWebApp -ResourceGroupName $ResourceGroup -Name $FrontendApp -ErrorAction Stop
$settings = @{}
if ($webApp.SiteConfig.AppSettings) {
    foreach ($s in $webApp.SiteConfig.AppSettings) {
        $settings[$s.Name] = $s.Value
    }
}

# Variables requeridas para el contenedor frontend
$settings["VITE_API_BASE_URL"] = $BackendUrl
$settings["WEBSITES_PORT"] = "80"

Write-Host "  VITE_API_BASE_URL = $BackendUrl" -ForegroundColor Gray
Write-Host "  WEBSITES_PORT = 80" -ForegroundColor Gray
Set-AzWebApp -ResourceGroupName $ResourceGroup -Name $FrontendApp -AppSettings $settings | Out-Null
Write-Host "Settings actualizados." -ForegroundColor Green

Write-Host "`nReiniciando frontend..." -ForegroundColor Yellow
Restart-AzWebApp -ResourceGroupName $ResourceGroup -Name $FrontendApp
Write-Host "Reinicio iniciado." -ForegroundColor Green

Write-Host "`nEspera 2-3 minutos y prueba: https://$FrontendApp.azurewebsites.net" -ForegroundColor Cyan
Write-Host "Si sigue fallando: Azure Portal -> $FrontendApp -> Deployment Center -> Logs" -ForegroundColor Gray
Write-Host ""
