# Corrige CORS en el backend: añade el origen del frontend a ALLOWED_ORIGINS_STR
# Ejecutar: .\scripts\fix-cors.ps1
# Si abres la app desde Azure Portal (embebida): .\scripts\fix-cors.ps1 -IncludeSandbox
# Usa Az PowerShell (no az CLI). Si CORS falla, el frontend no puede llamar al backend.

param(
    [string]$ResourceGroup = "rg-summit-dspm-ai-resources-app",
    [string]$BackendApp = "api-customerchatbotasmzl",
    [string]$FrontendOrigin = "https://app-customerchatbotasmzl.azurewebsites.net",
    [switch]$IncludeSandbox  # Añade orígenes sandbox de Azure Portal (app embebida)
)

$ErrorActionPreference = "Stop"

$modules = @("Az.Accounts", "Az.Websites")
foreach ($m in $modules) {
    if (-not (Get-Module -ListAvailable -Name $m)) {
        Write-Host "Instalando $m..." -ForegroundColor Yellow
        Install-Module -Name $m -Scope CurrentUser -Force -AllowClobber
    }
}
Import-Module Az.Accounts, Az.Websites -ErrorAction Stop

Connect-AzAccount -ErrorAction Stop | Out-Null

Write-Host "=== Corregir CORS en backend ===" -ForegroundColor Cyan
Write-Host "Backend: $BackendApp | Origen: $FrontendOrigin" -ForegroundColor Gray

$webApp = Get-AzWebApp -ResourceGroupName $ResourceGroup -Name $BackendApp -ErrorAction Stop

# Preservar todas las variables existentes
$hash = @{}
foreach ($setting in $webApp.SiteConfig.AppSettings) {
    $hash[$setting.Name] = $setting.Value
}

# Añadir/actualizar ALLOWED_ORIGINS_STR
$currentValue = if ($hash["ALLOWED_ORIGINS_STR"]) { $hash["ALLOWED_ORIGINS_STR"] } else { "" }
$origins = @($currentValue -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($FrontendOrigin -notin $origins) { $origins += $FrontendOrigin }
if ($IncludeSandbox) {
    $sandboxUrls = @(
        "https://sandbox-1.reactblade.portal.azure.net",
        "https://sandbox-2.reactblade.portal.azure.net",
        "https://sandbox-4.reactblade.portal.azure.net"
    )
    foreach ($s in $sandboxUrls) {
        if ($s -notin $origins) { $origins += $s }
    }
}
$hash["ALLOWED_ORIGINS_STR"] = ($origins -join ",")

Write-Host "`nALLOWED_ORIGINS_STR = $($hash['ALLOWED_ORIGINS_STR'])" -ForegroundColor Yellow
Set-AzWebApp -ResourceGroupName $ResourceGroup -Name $BackendApp -AppSettings $hash | Out-Null

Write-Host "Reiniciando backend..." -ForegroundColor Yellow
Restart-AzWebApp -ResourceGroupName $ResourceGroup -Name $BackendApp

Write-Host "`nCompletado. Espera 1-2 min y recarga la app: $FrontendOrigin" -ForegroundColor Green
