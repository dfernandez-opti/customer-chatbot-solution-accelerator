# Configure Customer Chatbot para usar DSPM-AI-Project (East US, 250K TPM)
# Valores obtenidos con Azure CLI - subscription e52da50f-bfae-4cbf-9188-68d2e5833dd4
#
# IMPORTANTE: Este proyecto usa DSPM-AI-Project y optisummitacr.azurecr.io
# NO ejecutar run_create_agents_scripts.ps1 SIN -ProjectEndpointOverride (sobrescribiría con customerchatbotasmzl)
# NO usar build-and-push con ACR distinto a optisummitacr

$ErrorActionPreference = "Stop"

# === Valores descubiertos ===
$SubscriptionId = "e52da50f-bfae-4cbf-9188-68d2e5833dd4"
$ResourceGroup = "rg-summit-dspm-ai-resources-app"
$ApiAppName = "api-customerchatbotasmzl"
$AiFoundryAccount = "DSPM-AI-Project"
$AiSearchName = "srch-customerchatbotasmzl"
$SolutionSuffix = "customerchatbotasmzl"

# Endpoints
$AiFoundryEndpoint = "https://dspm-ai-project.services.ai.azure.com/api/projects/proj-default"
$AiSearchEndpoint = "https://$AiSearchName.search.windows.net"
$ResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts/$AiFoundryAccount/projects/proj-default"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Configurando API para DSPM-AI-Project" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

az account set --subscription $SubscriptionId

# Obtener API key de Azure (para auth por key si se necesita)
$ApiKey = az cognitiveservices account keys list --name $AiFoundryAccount --resource-group $ResourceGroup --query "key1" -o tsv 2>$null

# Variables para el backend (API) - TODO apuntar a DSPM-AI-Project (East US, 250K TPM)
$appSettings = @{
    "AZURE_FOUNDRY_ENDPOINT" = $AiFoundryEndpoint
    "AZURE_AI_AGENT_ENDPOINT" = $AiFoundryEndpoint
    "AZURE_OPENAI_ENDPOINT" = "https://$AiFoundryAccount.openai.azure.com/"
    "AZURE_OPENAI_RESOURCE" = $AiFoundryAccount
    "AZURE_SEARCH_ENDPOINT" = $AiSearchEndpoint
    "AZURE_AI_SEARCH_ENDPOINT" = $AiSearchEndpoint
    "SECURITY_EVENTS_DATA_DIR" = "/home/LogFiles/data/security-events"
    "OPPORTUNITIES_DATA_DIR" = "/home/LogFiles/data/opportunities"
}
# Opcional: si el backend usa API key en lugar de Managed Identity
# $appSettings["AZURE_AI_SERVICES_KEY"] = $ApiKey

Write-Host "`nAplicando variables en $ApiAppName..." -ForegroundColor Yellow
foreach ($key in $appSettings.Keys) {
    az webapp config appsettings set --name $ApiAppName --resource-group $ResourceGroup --settings "$key=$($appSettings[$key])" --output none
    Write-Host "  $key = $($appSettings[$key])"
}

Write-Host "`nReiniciando backend..." -ForegroundColor Yellow
az webapp restart --name $ApiAppName --resource-group $ResourceGroup

Write-Host "`n==============================================" -ForegroundColor Green
Write-Host "Configuracion completada" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host "`nSiguiente paso: Crear agentes en DSPM-AI-Project (usa override para no tomar customerchatbotasmzl):"
$AccountResourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup/providers/Microsoft.CognitiveServices/accounts/$AiFoundryAccount"
Write-Host "  .\infra\scripts\agent_scripts\run_create_agents_scripts.ps1 -resourceGroup `"$ResourceGroup`" -ProjectEndpointOverride `"$AiFoundryEndpoint`" -AiFoundryResourceIdOverride `"$AccountResourceId`""
Write-Host "`nPara respuestas más rápidas, añade: -GptModelOverride `"gpt-4o-mini`""
Write-Host "`nPara azd env (despliegue futuro):"
Write-Host "  azd env set AZURE_EXISTING_AI_PROJECT_RESOURCE_ID `"$ResourceId`""
Write-Host ""
