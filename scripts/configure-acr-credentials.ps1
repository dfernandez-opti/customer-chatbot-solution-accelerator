# Configura credenciales ACR en los App Services (frontend y backend)
# Ejecutar desde la raíz del proyecto: .\scripts\configure-acr-credentials.ps1

param(
    [string]$AcrName = "optisummitacr",
    [string]$ResourceGroup = "rg-summit-dspm-ai-resources-app",
    [string]$FrontendApp = "app-customerchatbotasmzl",
    [string]$BackendApp = "api-customerchatbotasmzl",
    [string]$ImageTag = "opti-summit"
)

$ErrorActionPreference = "Stop"

Write-Host "=== Configurar credenciales ACR en App Services ===" -ForegroundColor Cyan
Write-Host "ACR: $AcrName | RG: $ResourceGroup" -ForegroundColor Gray

# Habilitar admin en ACR
Write-Host "`n1. Habilitando admin en ACR..." -ForegroundColor Yellow
az acr update -n $AcrName --resource-group $ResourceGroup --admin-enabled true | Out-Null

# Obtener credenciales
Write-Host "2. Obteniendo credenciales..." -ForegroundColor Yellow
$creds = az acr credential show -n $AcrName -g $ResourceGroup -o json | ConvertFrom-Json
$user = $creds.username
$pass = $creds.passwords[0].value
$serverUrl = "https://${AcrName}.azurecr.io"

# Configurar frontend
Write-Host "3. Configurando frontend ($FrontendApp)..." -ForegroundColor Yellow
az webapp config container set `
  --name $FrontendApp `
  --resource-group $ResourceGroup `
  --docker-custom-image-name "${AcrName}.azurecr.io/frontend:${ImageTag}" `
  --docker-registry-server-url $serverUrl `
  --docker-registry-server-user $user `
  --docker-registry-server-password $pass

# Configurar backend
Write-Host "4. Configurando backend ($BackendApp)..." -ForegroundColor Yellow
az webapp config container set `
  --name $BackendApp `
  --resource-group $ResourceGroup `
  --docker-custom-image-name "${AcrName}.azurecr.io/backend:${ImageTag}" `
  --docker-registry-server-url $serverUrl `
  --docker-registry-server-user $user `
  --docker-registry-server-password $pass

# Reiniciar ambos
Write-Host "`n5. Reiniciando App Services..." -ForegroundColor Yellow
az webapp restart --name $FrontendApp --resource-group $ResourceGroup
az webapp restart --name $BackendApp --resource-group $ResourceGroup

Write-Host "`n=== Completado ===" -ForegroundColor Green
Write-Host "Espera 2-3 minutos y prueba: https://$FrontendApp.azurewebsites.net"
