# Diagnóstico de roles y permisos - Customer Chatbot OPTI
# Ejecutar: .\scripts\diagnose-roles-and-permissions.ps1

$ErrorActionPreference = "Continue"

$SubscriptionId = "e52da50f-bfae-4cbf-9188-68d2e5833dd4"
$ResourceGroup = "rg-summit-dspm-ai-resources-app"
$ApiAppName = "api-customerchatbotasmzl"
$AiSearchName = "srch-customerchatbotasmzl"
# Cosmos: nombre conocido; validar que no sea salida de comando
$CosmosAccount = "cosmos-customerchatbotasmzl"
$AiFoundryAccount = "DSPM-AI-Project"

# IDs de roles conocidos
$RoleSearchServiceContributor = "7ca78c08-252a-4471-8644-bb5ff32d4ba0"
$RoleSearchIndexDataContributor = "8ebe5a00-799e-43f5-93ac-243d3dce84a7"
$RoleSearchIndexDataReader = "1407120a-92aa-4202-b7e9-c0e197c71c8f"
$RoleCognitiveServicesUser = "Cognitive Services User"
$RoleAzureAIUser = "Azure AI User"

Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  DIAGNOSTICO: Roles y Permisos" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

az account set --subscription $SubscriptionId 2>$null

# 1. Obtener principal IDs
Write-Host "[1] Identidades del API (App Service)" -ForegroundColor Yellow
$apiPrincipalId = az webapp identity show --name $ApiAppName --resource-group $ResourceGroup --query "principalId" -o tsv 2>$null
if ($apiPrincipalId) {
    Write-Host "    API Principal ID: $apiPrincipalId" -ForegroundColor Green
} else {
    Write-Host "    ERROR: No se pudo obtener identity del API. Verifica que Managed Identity este habilitada." -ForegroundColor Red
    Write-Host "    Comando: az webapp identity assign --name $ApiAppName --resource-group $ResourceGroup" -ForegroundColor Gray
}

# 2. AI Search - Resource ID
$aiSearchResourceId = az search service show --name $AiSearchName --resource-group $ResourceGroup --query "id" -o tsv 2>$null
if (-not $aiSearchResourceId) {
    $aiSearchResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.Search/searchServices/$AiSearchName"
}

Write-Host ""
Write-Host "[2] Roles en AI Search ($AiSearchName)" -ForegroundColor Yellow
$searchRoles = az role assignment list --scope $aiSearchResourceId --output json 2>$null | ConvertFrom-Json
if ($searchRoles) {
    foreach ($r in $searchRoles) {
        $roleName = $r.roleDefinitionName
        $principal = $r.principalId
        $type = $r.principalType
        $isApi = if ($principal -eq $apiPrincipalId) { " <-- API" } else { "" }
        Write-Host "    $roleName -> $principal ($type)$isApi" -ForegroundColor Gray
    }
    $apiOnSearch = $searchRoles | Where-Object { $_.principalId -eq $apiPrincipalId }
    if (-not $apiOnSearch) {
        Write-Host "    ADVERTENCIA: El API no tiene roles directos en AI Search." -ForegroundColor Yellow
        Write-Host "    (El Foundry project usa su propia conexion; el API no accede directamente a Search)" -ForegroundColor Gray
    }
} else {
    Write-Host "    No se pudieron listar roles." -ForegroundColor Red
}

# 3. Documentos en indices AI Search
Write-Host ""
Write-Host "[3] Documentos en indices AI Search" -ForegroundColor Yellow
$adminKey = az search admin-key show --resource-group $ResourceGroup --service-name $AiSearchName --query "primaryKey" -o tsv 2>$null
if ($adminKey) {
    $headers = @{
        "Content-Type" = "application/json"
        "api-key" = $adminKey
    }
    $anyEmpty = $false
    foreach ($idx in @("products_index", "policies_index")) {
        try {
            $uri = "https://$AiSearchName.search.windows.net/indexes/$idx/docs/`$count?api-version=2024-07-01"
            $count = Invoke-RestMethod -Uri $uri -Headers $headers -Method Get
            $anyEmpty = $anyEmpty -or ($count -eq 0)
            Write-Host "    $idx : $count documentos" -ForegroundColor $(if ($count -gt 0) { "Green" } else { "Red" })
        } catch {
            Write-Host "    $idx : ERROR o indice no existe" -ForegroundColor Red
            $anyEmpty = $true
        }
    }
    if ($anyEmpty) {
        Write-Host "    ACCION: Ejecutar run_upload_data_scripts.ps1 para cargar datos" -ForegroundColor Yellow
    }
} else {
    Write-Host "    No se pudo obtener admin key de AI Search." -ForegroundColor Red
}

# 4. Cosmos DB - roles del API
Write-Host ""
Write-Host "[4] Cosmos DB - Rol del API ($CosmosAccount)" -ForegroundColor Yellow
if ($apiPrincipalId) {
    $cosmosRoles = az cosmosdb sql role assignment list --resource-group $ResourceGroup --account-name $CosmosAccount --output json 2>$null | ConvertFrom-Json
    if ($cosmosRoles) {
        $apiCosmos = $cosmosRoles | Where-Object { $_.principalId -eq $apiPrincipalId }
        if ($apiCosmos) {
            Write-Host "    API tiene rol en Cosmos DB: OK" -ForegroundColor Green
        } else {
            Write-Host "    ADVERTENCIA: API no tiene rol Cosmos DB Data Contributor" -ForegroundColor Yellow
            Write-Host "    (Oportunidades usan JSONL; chat_sessions usan Cosmos)" -ForegroundColor Gray
        }
    } else {
        Write-Host "    No se pudieron listar roles Cosmos." -ForegroundColor Red
    }
} else {
    Write-Host "    Saltado (no hay API principal ID)" -ForegroundColor Gray
}

# 5. Cognitive Services / Azure AI - roles del API para Foundry
Write-Host ""
Write-Host "[5] Cognitive Services / Azure AI - API para Foundry" -ForegroundColor Yellow
# DSPM-AI-Project puede estar en otro RG; buscar en la subscription
$aiAccountJson = az cognitiveservices account list --subscription $SubscriptionId --query "[?name=='$AiFoundryAccount'] | [0]" -o json 2>$null
$aiAccount = $null
if ($aiAccountJson -and $aiAccountJson -ne "null") {
    $aiAccount = $aiAccountJson | ConvertFrom-Json
}
if ($aiAccount -and $aiAccount.id) {
    $aiResourceId = $aiAccount.id
    $aiRg = $aiAccount.resourceGroup
    Write-Host "    Cuenta encontrada en RG: $aiRg" -ForegroundColor Gray
} else {
    $aiResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts/$AiFoundryAccount"
}
$aiRoles = $null
if ($apiPrincipalId) {
    $aiRoles = az role assignment list --scope $aiResourceId --assignee $apiPrincipalId --output json 2>$null | ConvertFrom-Json
}
if ($aiRoles -and $aiRoles.Count -gt 0) {
    foreach ($r in $aiRoles) {
        Write-Host "    $($r.roleDefinitionName): OK" -ForegroundColor Green
    }
} else {
    Write-Host "    ADVERTENCIA: API no tiene rol en $AiFoundryAccount" -ForegroundColor Red
    Write-Host "    Asignar: az role assignment create --assignee $apiPrincipalId --role 'Cognitive Services User' --scope $aiResourceId" -ForegroundColor Yellow
    Write-Host "    Asignar: az role assignment create --assignee $apiPrincipalId --role 'Azure AI User' --scope $aiResourceId" -ForegroundColor Yellow
}

# 6. Variables de entorno del API
Write-Host ""
Write-Host "[6] Variables criticas del API" -ForegroundColor Yellow
$settings = az webapp config appsettings list --name $ApiAppName --resource-group $ResourceGroup --output json 2>$null | ConvertFrom-Json
$critical = @(
    "AZURE_FOUNDRY_ENDPOINT", "FOUNDRY_CHAT_AGENT", "FOUNDRY_PRODUCT_AGENT", "FOUNDRY_POLICY_AGENT",
    "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_RESOURCE", "AZURE_SEARCH_ENDPOINT",
    "COSMOS_DB_ENDPOINT", "OPPORTUNITIES_DATA_DIR"
)
foreach ($key in $critical) {
    $val = ($settings | Where-Object { $_.name -eq $key }).value
    $status = if ($val) { "OK" } else { "FALTA" }
    $color = if ($val) { "Green" } else { "Red" }
    $display = if ($val -and $val.Length -gt 50) { $val.Substring(0, 50) + "..." } else { $val }
    Write-Host "    $key : $status" -ForegroundColor $color
    if ($val) { Write-Host "        $display" -ForegroundColor Gray }
}

# 7. Probar endpoint de oportunidades
Write-Host ""
Write-Host "[7] Probar API - Oportunidades" -ForegroundColor Yellow
$apiUrl = "https://$ApiAppName.azurewebsites.net"
try {
    $oppSummary = Invoke-RestMethod -Uri "$apiUrl/api/opportunities/summary" -Method Get -TimeoutSec 10
    Write-Host "    Oportunidades registradas: $($oppSummary.total)" -ForegroundColor Green
} catch {
    Write-Host "    No se pudo conectar a $apiUrl/api/opportunities/summary" -ForegroundColor Red
    Write-Host "    Error: $($_.Exception.Message)" -ForegroundColor Gray
}

# 8. Comandos para asignar roles si faltan
Write-Host ""
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "  COMANDOS PARA ASIGNAR ROLES (si faltan)" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "# 1. Habilitar Managed Identity en API (si no existe):" -ForegroundColor Gray
Write-Host "az webapp identity assign --name $ApiAppName --resource-group $ResourceGroup" -ForegroundColor White
Write-Host ""
Write-Host "# 2. Cognitive Services User + Azure AI User (para Foundry):" -ForegroundColor Gray
Write-Host "az role assignment create --assignee `$apiPrincipalId --role 'Cognitive Services User' --scope `"$aiResourceId`"" -ForegroundColor White
Write-Host "az role assignment create --assignee `$apiPrincipalId --role 'Azure AI User' --scope `"$aiResourceId`"" -ForegroundColor White
Write-Host ""
Write-Host "# 3. Cargar datos en AI Search (indices vacios):" -ForegroundColor Gray
Write-Host ".\infra\scripts\data_scripts\run_upload_data_scripts.ps1 -resource_group `"$ResourceGroup`"" -ForegroundColor White
Write-Host ""
Write-Host "# 4. Reiniciar API despues de cambios:" -ForegroundColor Gray
Write-Host "az webapp restart --name $ApiAppName --resource-group $ResourceGroup" -ForegroundColor White
Write-Host ""
