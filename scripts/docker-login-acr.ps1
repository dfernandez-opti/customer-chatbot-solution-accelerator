# Login a ACR con Az PowerShell (sin az CLI - evita error Purview)
# Ejecutar: .\scripts\docker-login-acr.ps1

param(
    [string]$AcrName = "optisummitacr",
    [string]$ResourceGroup = "rg-summit-dspm-ai-resources-app"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Docker login a ACR (sin az CLI) ===" -ForegroundColor Cyan

$mod = Get-Module -ListAvailable -Name Az.ContainerRegistry
if (-not $mod) {
    Write-Host "Instalando Az.ContainerRegistry..." -ForegroundColor Yellow
    Install-Module -Name Az.ContainerRegistry -Scope CurrentUser -Force -AllowClobber
}
Import-Module Az.ContainerRegistry -ErrorAction Stop

Write-Host "Conectando a Azure..." -ForegroundColor Yellow
Connect-AzAccount -ErrorAction Stop | Out-Null

# Habilitar admin en ACR si no está (necesario para credenciales)
Write-Host "Verificando ACR $AcrName..." -ForegroundColor Yellow
$acr = Get-AzContainerRegistry -ResourceGroupName $ResourceGroup -Name $AcrName -ErrorAction Stop
if (-not $acr.AdminUserEnabled) {
    Write-Host "Habilitando admin en ACR..." -ForegroundColor Yellow
    Update-AzContainerRegistry -ResourceGroupName $ResourceGroup -Name $AcrName -AdminUserEnabled $true | Out-Null
}

$creds = Get-AzContainerRegistryCredential -ResourceGroupName $ResourceGroup -Name $AcrName -ErrorAction Stop
if (-not $creds -or -not $creds.Password) {
    Write-Host "Error: No se pudieron obtener credenciales del ACR. Verifica que Admin esté habilitado en el portal." -ForegroundColor Red
    exit 1
}

$server = "$AcrName.azurecr.io"
Write-Host "Haciendo docker login a $server..." -ForegroundColor Yellow

# En Windows/PowerShell el pipe puede añadir caracteres; usar -p (menos seguro pero más fiable)
$result = & docker login $server -u $creds.Username -p $creds.Password 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "Login exitoso." -ForegroundColor Green
    Write-Host "Prueba: docker pull $server/frontend:opti-summit-v8" -ForegroundColor Gray
} else {
    Write-Host "Error en docker login: $result" -ForegroundColor Red
    exit 1
}
