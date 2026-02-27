# Actualiza la imagen Docker del App Service SIN usar az CLI
# Usa el módulo Az de PowerShell (no az CLI). Si az falla por purview, usa este script.
# Ejecutar: .\scripts\update-app-container.ps1 -ImageTag "opti-summit-v7"

param(
    [string]$ResourceGroup = "rg-summit-dspm-ai-resources-app",
    [string]$BackendApp = "api-customerchatbotasmzl",
    [string]$FrontendApp = "app-customerchatbotasmzl",
    [string]$AcrName = "optisummitacr",
    [string]$ImageTag = "opti-summit-v7",
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$RestartOnly  # Solo reiniciar, no cambiar imagen
)

$ErrorActionPreference = "Stop"

$modules = @("Az.Accounts", "Az.Websites", "Az.ContainerRegistry")
foreach ($m in $modules) {
    if (-not (Get-Module -ListAvailable -Name $m)) {
        Write-Host "Instalando $m..." -ForegroundColor Yellow
        Install-Module -Name $m -Scope CurrentUser -Force -AllowClobber
    }
}
Import-Module Az.Websites, Az.ContainerRegistry -ErrorAction Stop

Connect-AzAccount -ErrorAction Stop | Out-Null

$acrImage = "$AcrName.azurecr.io"

if (-not $RestartOnly) {
    $creds = Get-AzContainerRegistryCredential -ResourceGroupName $ResourceGroup -Name $AcrName -ErrorAction SilentlyContinue
    if (-not $creds) {
        Write-Host "Error: No se pudo obtener credenciales de ACR. Verifica que $AcrName esté en $ResourceGroup y tenga admin habilitado." -ForegroundColor Red
        exit 1
    }
    $acrPassword = ConvertTo-SecureString -String $creds.Password -AsPlainText -Force

    if ($BackendOnly -or (-not $FrontendOnly)) {
        Write-Host "Actualizando backend ($BackendApp) a $acrImage/backend:$ImageTag..." -ForegroundColor Cyan
        Set-AzWebApp -ResourceGroupName $ResourceGroup -Name $BackendApp `
            -ContainerImageName "$acrImage/backend:$ImageTag" `
            -ContainerRegistryUrl "https://$AcrName.azurecr.io" `
            -ContainerRegistryUser $AcrName `
            -ContainerRegistryPassword $acrPassword
    }
    if ($FrontendOnly -or (-not $BackendOnly)) {
        Write-Host "Actualizando frontend ($FrontendApp) a $acrImage/frontend:$ImageTag..." -ForegroundColor Cyan
        Set-AzWebApp -ResourceGroupName $ResourceGroup -Name $FrontendApp `
            -ContainerImageName "$acrImage/frontend:$ImageTag" `
            -ContainerRegistryUrl "https://$AcrName.azurecr.io" `
            -ContainerRegistryUser $AcrName `
            -ContainerRegistryPassword $acrPassword
    }
}

Write-Host "Reiniciando App Services..." -ForegroundColor Yellow
if ($BackendOnly -or (-not $FrontendOnly)) {
    Restart-AzWebApp -ResourceGroupName $ResourceGroup -Name $BackendApp
    Write-Host "  Backend reiniciado" -ForegroundColor Green
}
if ($FrontendOnly -or (-not $BackendOnly)) {
    Restart-AzWebApp -ResourceGroupName $ResourceGroup -Name $FrontendApp
    Write-Host "  Frontend reiniciado" -ForegroundColor Green
}

Write-Host "`nCompletado. Espera 2-3 min y prueba: https://app-customerchatbotasmzl.azurewebsites.net" -ForegroundColor Green
