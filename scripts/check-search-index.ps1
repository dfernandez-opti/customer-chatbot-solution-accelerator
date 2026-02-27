# Verifica el índice products_index en Azure AI Search
# Ejecutar desde la raíz: .\scripts\check-search-index.ps1
#
# Si az falla (ej. extensión purview), usa el endpoint del backend:
#   Invoke-WebRequest -Uri "https://api-customerchatbotasmzl.azurewebsites.net/api/chat/debug-search-index" | Select-Object -ExpandProperty Content

param(
    [string]$ResourceGroup = "rg-summit-dspm-ai-resources-app",
    [string]$SearchService = "srch-customerchatbotasmzl",
    [string]$IndexName = "products_index",
    [string]$SearchKey = ""  # Opcional: si az falla (ej. purview), obtén la key en Portal -> Search -> Keys
)

$ErrorActionPreference = "Stop"

Write-Host "=== Verificar índice AI Search ===" -ForegroundColor Cyan
Write-Host "Servicio: $SearchService | Índice: $IndexName" -ForegroundColor Gray

# Obtener admin key (Az PowerShell primero; si falla, az CLI o manual)
$key = $SearchKey
if (-not $key) {
    # Cargar Az y asegurar sesión (como update-app-container.ps1)
    if (-not (Get-Module -ListAvailable -Name Az.Accounts)) {
        Install-Module -Name Az.Accounts -Scope CurrentUser -Force -AllowClobber
    }
    Import-Module Az.Accounts -ErrorAction SilentlyContinue
    $ctx = Get-AzContext -ErrorAction SilentlyContinue
    if (-not $ctx) {
        Write-Host "Iniciando sesión en Azure (Az)..." -ForegroundColor Gray
        Connect-AzAccount -ErrorAction Stop | Out-Null
        $ctx = Get-AzContext -ErrorAction Stop
    }
    # 1) Az.Search si está disponible
    try {
        if (Get-Module -ListAvailable -Name Az.Search) {
            Import-Module Az.Search -ErrorAction SilentlyContinue
            $pair = Get-AzSearchAdminKeyPair -ResourceGroupName $ResourceGroup -ServiceName $SearchService -ErrorAction Stop
            $key = $pair.Primary
        }
    } catch { $key = $null }
    # 2) Invoke-AzRestMethod (listAdminKeys)
    if (-not $key) {
        try {
            $subId = $ctx.Subscription.Id
            $path = "/subscriptions/$subId/resourceGroups/$ResourceGroup/providers/Microsoft.Search/searchServices/$SearchService/listAdminKeys?api-version=2023-11-01"
            $resp = Invoke-AzRestMethod -Path $path -Method Post -ErrorAction Stop
            $key = ($resp.Content | ConvertFrom-Json).primaryKey
        } catch {
            Write-Host "Az listAdminKeys falló: $($_.Exception.Message)" -ForegroundColor DarkGray
            $key = $null
        }
    }
    # 2) Fallback: az CLI
    if (-not $key) {
        $keys = az search admin-key show --resource-group $ResourceGroup --service-name $SearchService 2>$null
        if ($keys) { $key = ($keys | ConvertFrom-Json).primaryKey }
    }
    if (-not $key) {
        Write-Host "`nError: No se pudo obtener la key (Az ni az CLI)." -ForegroundColor Yellow
        Write-Host "Pasa la key manualmente: .\scripts\check-search-index.ps1 -SearchKey `"TU_ADMIN_KEY`"" -ForegroundColor Yellow
        Write-Host "  (Portal -> $SearchService -> Keys -> Primary admin key)" -ForegroundColor Gray
        exit 1
    }
}
$endpoint = "https://$SearchService.search.windows.net"
$url = "$endpoint/indexes/$IndexName/stats?api-version=2024-07-01"

$headers = @{
    "api-key" = $key
    "Content-Type" = "application/json"
}

try {
    $result = Invoke-RestMethod -Uri $url -Headers $headers -Method Get
    $docCount = $result.documentCount
    $storageSize = $result.storageSize
    Write-Host "`nDocumentos en $IndexName : $docCount" -ForegroundColor Green
    Write-Host "Tamaño almacenamiento: $storageSize bytes" -ForegroundColor Gray
    if ($docCount -eq 0) {
        Write-Host "`nADVERTENCIA: El índice está vacío. Ejecuta run_upload_data_scripts.ps1 para poblar productos." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Error al consultar: $_" -ForegroundColor Red
    Write-Host "`nSi az search admin-key falla por purview, ejecuta primero: az extension remove --name purview" -ForegroundColor Yellow
}
