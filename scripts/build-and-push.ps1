# Build and Push Docker images to ACR - OPTI Summit
# Ejecuta desde la raíz del proyecto: .\scripts\build-and-push.ps1
# Requiere: Docker, Azure CLI, estar logueado en Azure

param(
    [string]$AcrName = "",
    [string]$ResourceGroup = "rg-summit-dspm-ai-resources-app",
    [string]$ImageTag = "opti-summit",
    [switch]$CreateAcr,
    [switch]$BuildOnly  # Solo construir, no hacer login ni push (útil si ACR no está disponible)
)

$ErrorActionPreference = "Stop"
$projectRoot = if ($PSScriptRoot) { (Resolve-Path (Split-Path -Parent $PSScriptRoot)).Path } else { (Get-Location).Path }
Set-Location $projectRoot

# Obtener ACR: parámetro, o azd env (si existe y es válido), o default OPTI Summit
if (-not $AcrName) {
    try {
        $azdAcr = (azd env get-value ACR_NAME 2>$null) | Out-String
        $azdAcr = ($azdAcr -replace "`r`n", "").Trim()
        if ($azdAcr -and $azdAcr.Length -ge 5 -and $azdAcr.Length -le 50 -and $azdAcr -notmatch 'ERROR|no project| ') {
            # Ignorar ccbcontainerreg (deployment antiguo); usar optisummitacr que es el ACR real
            if ($azdAcr -ne "ccbcontainerreg") {
                $AcrName = $azdAcr
            }
        }
    } catch { }
}
if (-not $AcrName -or $AcrName -match 'ERROR|no project') {
    $AcrName = "optisummitacr"  # ACR que existe y funciona (optisummitacr.azurecr.io)
}

# Crear ACR si no existe (solo si no es BuildOnly)
if ($CreateAcr -and -not $BuildOnly) {
    Write-Host "Comprobando ACR $AcrName en $ResourceGroup..." -ForegroundColor Yellow
    $acr = az acr show --name $AcrName --resource-group $ResourceGroup 2>$null
    if (-not $acr) {
        Write-Host "Creando ACR $AcrName..." -ForegroundColor Yellow
        az acr create --name $AcrName --resource-group $ResourceGroup --sku Basic
    }
}

$acrLogin = "$AcrName.azurecr.io"
$contextPath = $projectRoot  # Rutas con espacios requieren path explícito

Write-Host "=== Build de imágenes OPTI Summit ===" -ForegroundColor Cyan
Write-Host "Proyecto: $projectRoot" -ForegroundColor DarkGray
Write-Host "ACR: $AcrName | Tag: $ImageTag" -ForegroundColor Gray

# Login ACR (omitir si BuildOnly)
$acrLoginOk = $false
if (-not $BuildOnly) {
    Write-Host "`n1. Login en ACR..." -ForegroundColor Yellow
    az acr login --name $AcrName 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $acrLoginOk = $true
    } else {
        Write-Host "   az acr login falló (ej. Purview), intentando con Az PowerShell..." -ForegroundColor Yellow
        try {
            Import-Module Az.ContainerRegistry -ErrorAction Stop
            Connect-AzAccount -ErrorAction Stop | Out-Null
            $acrObj = Get-AzContainerRegistry -ResourceGroupName $ResourceGroup -Name $AcrName -ErrorAction Stop
            if (-not $acrObj.AdminUserEnabled) {
                Update-AzContainerRegistry -ResourceGroupName $ResourceGroup -Name $AcrName -AdminUserEnabled $true | Out-Null
            }
            $creds = Get-AzContainerRegistryCredential -ResourceGroupName $ResourceGroup -Name $AcrName -ErrorAction Stop
            if ($creds -and $creds.Password) {
                & docker login $acrLogin -u $creds.Username -p $creds.Password 2>&1 | Out-Null
                if ($LASTEXITCODE -eq 0) { $acrLoginOk = $true }
            }
        } catch { }
        if (-not $acrLoginOk) {
            Write-Host "AVISO: No se pudo conectar a ACR. Ejecuta: .\scripts\docker-login-acr.ps1" -ForegroundColor Yellow
            Write-Host "Luego vuelve a ejecutar este script (o usa -BuildOnly y push manual)." -ForegroundColor Yellow
        }
    }
}

# Build Frontend (contexto = raíz, path explícito por si hay espacios)
Write-Host "`n2. Construyendo frontend (puede tardar varios minutos)..." -ForegroundColor Yellow
docker build --no-cache -f "$contextPath/src/App/Dockerfile" -t "${acrLogin}/frontend:${ImageTag}" "$contextPath"
if ($LASTEXITCODE -ne 0) { throw "Error construyendo frontend" }

# Build Backend
Write-Host "`n3. Construyendo backend..." -ForegroundColor Yellow
docker build --no-cache -f "$contextPath/src/api/Dockerfile" -t "${acrLogin}/backend:${ImageTag}" "$contextPath/src/api"
if ($LASTEXITCODE -ne 0) { throw "Error construyendo backend" }

# Push (solo si login OK)
if ($acrLoginOk) {
    Write-Host "`n4. Subiendo imágenes a ACR..." -ForegroundColor Yellow
    docker push "${acrLogin}/frontend:${ImageTag}"
    docker push "${acrLogin}/backend:${ImageTag}"
}

Write-Host "`n=== Completado ===" -ForegroundColor Green
if ($BuildOnly) {
    Write-Host "Imágenes construidas localmente. Para subir a ACR, ejecuta sin -BuildOnly."
} else {
    Write-Host "Imágenes subidas: frontend:$ImageTag, backend:$ImageTag"
    Write-Host "`nPara que App Service use las nuevas imágenes:"
    Write-Host "  az webapp restart --name <app-name> --resource-group $ResourceGroup"
}
