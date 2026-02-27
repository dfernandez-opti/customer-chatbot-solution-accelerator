# Crear agentes en proj-default (compatible con PowerShell 5.1)
# Valores para rg-summit-dspm-ai-resources-app

$ErrorActionPreference = "Stop"
$projectEndpoint = "https://dspm-ai-project.services.ai.azure.com/api/projects/proj-default"
$solutionName = "customerchatbotasmzl"
$gptModelName = "gpt-4o"
$searchEndpoint = "https://srch-customerchatbotasmzl.search.windows.net"
$resourceGroup = "rg-summit-dspm-ai-resources-app"
$apiAppName = "api-customerchatbotasmzl"

Write-Host "Instalando dependencias Python..." -ForegroundColor Yellow
python -m pip install --quiet -r infra/scripts/agent_scripts/requirements.txt

Write-Host "Creando agentes en proj-default..." -ForegroundColor Yellow
$output = python infra/scripts/agent_scripts/01_create_agents.py `
  --ai_project_endpoint=$projectEndpoint `
  --solution_name=$solutionName `
  --gpt_model_name=$gptModelName `
  --ai_search_endpoint=$searchEndpoint 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host $output
    throw "Error creando agentes"
}

$chatAgent = ($output | Select-String "^chatAgentName=(.+)$").Matches.Groups[1].Value
$productAgent = ($output | Select-String "^productAgentName=(.+)$").Matches.Groups[1].Value
$policyAgent = ($output | Select-String "^policyAgentName=(.+)$").Matches.Groups[1].Value

Write-Host "Agentes creados: $chatAgent, $productAgent, $policyAgent" -ForegroundColor Green

Write-Host "Actualizando variables en App Service..." -ForegroundColor Yellow
az webapp config appsettings set --resource-group $resourceGroup --name $apiAppName `
  --settings "FOUNDRY_CHAT_AGENT=$chatAgent" "FOUNDRY_PRODUCT_AGENT=$productAgent" "FOUNDRY_POLICY_AGENT=$policyAgent" -o none

az webapp restart --name $apiAppName --resource-group $resourceGroup -o none
Write-Host "Listo. Refresca la pagina de Agents en Foundry." -ForegroundColor Green
