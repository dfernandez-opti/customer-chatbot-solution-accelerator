#!/usr/bin/env pwsh
#Requires -Version 7.0

param(
    [string]$resourceGroup,
    [Alias("resource_group")]
    [string]$ResourceGroupAlias,
    # Override para usar DSPM-AI-Project (East US) en lugar del proyecto del deployment
    [string]$ProjectEndpointOverride,
    [string]$AiFoundryResourceIdOverride,
    # Modelo más rápido para reducir latencia (gpt-4o-mini es ~2x más rápido que gpt-4o)
    [string]$GptModelOverride
)

# Handle both parameter naming conventions
if (-not $resourceGroup -and $ResourceGroupAlias) {
    $resourceGroup = $ResourceGroupAlias
}

# Variables
$projectEndpoint = ""
$solutionName = ""
$gptModelName = ""
$aiFoundryResourceId = ""
$apiAppName = ""
$searchEndpoint = ""
$azSubscriptionId = ""

$ErrorActionPreference = "Stop"
Write-Host "Started the agent creation script setup..."

function Test-AzdInstalled {
    try {
        $null = Get-Command azd -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Get-ValuesFromAzdEnv {
    if (-not (Test-AzdInstalled)) {
        Write-Host "Error: Azure Developer CLI is not installed."
        return $false
    }

    Write-Host "Getting values from azd environment..."
    
    try {
        $script:projectEndpoint = $(azd env get-value AZURE_AI_AGENT_ENDPOINT 2>$null)
        $script:solutionName = $(azd env get-value SOLUTION_NAME 2>$null)
        $script:gptModelName = $(azd env get-value AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME 2>$null)
        $script:aiFoundryResourceId = $(azd env get-value AI_FOUNDRY_RESOURCE_ID 2>$null)
        $script:apiAppName = $(azd env get-value API_APP_NAME 2>$null)
        $script:resourceGroup = $(azd env get-value AZURE_RESOURCE_GROUP 2>$null)
        $script:searchEndpoint = $(azd env get-value AZURE_AI_SEARCH_ENDPOINT 2>$null)
    } catch {
        Write-Host "Error: Failed to retrieve values from azd environment."
        return $false
    }
    
    # Validate that we got all required values (check for empty or error messages)
    if (-not $script:projectEndpoint -or $script:projectEndpoint -match "ERROR:" -or
        -not $script:solutionName -or $script:solutionName -match "ERROR:" -or
        -not $script:gptModelName -or $script:gptModelName -match "ERROR:" -or
        -not $script:aiFoundryResourceId -or $script:aiFoundryResourceId -match "ERROR:" -or
        -not $script:apiAppName -or $script:apiAppName -match "ERROR:" -or
        -not $script:resourceGroup -or $script:resourceGroup -match "ERROR:" -or
        -not $script:searchEndpoint -or $script:searchEndpoint -match "ERROR:") {
        Write-Host "Error: Could not retrieve all required values from azd environment."
        return $false
    }
    
    Write-Host "Successfully retrieved values from azd environment."
    return $true
}

function Get-DeploymentValue {
    param(
        [object]$DeploymentOutputs,
        [string]$PrimaryKey,
        [string]$FallbackKey
    )
    
    $getVal = {
        param($key)
        if (-not $key) { return $null }
        $o = $null
        if ($DeploymentOutputs -is [System.Collections.IDictionary]) {
            $matchKey = @($DeploymentOutputs.Keys) | Where-Object { [string]$_ -eq $key } | Select-Object -First 1
            if ($null -ne $matchKey) { $o = $DeploymentOutputs[$matchKey] }
        } else {
            $o = $DeploymentOutputs.$key
            if (-not $o) { $o = $DeploymentOutputs[$key] }
        }
        if ($o) {
            $v = $o.value; if ($null -eq $v) { $v = $o.Value }
            return $v
        }
        return $null
    }
    
    $value = & $getVal $PrimaryKey
    if (-not $value) { $value = & $getVal $FallbackKey }
    return $value
}

function Get-ValuesFromAzDeployment {
    Write-Host "Getting values from Azure deployment outputs..."
    
    $deploymentName = $null
    $deploymentOutputs = $null
    
    if ($script:UseAzPowerShell) {
        $rg = Get-AzResourceGroup -Name $resourceGroup -ErrorAction SilentlyContinue
        if (-not $rg) {
            Write-Host "Error: Resource group $resourceGroup not found."
            return $false
        }
        $deploymentName = $rg.Tags["DeploymentName"]
        $deploy = $null
        if ($deploymentName) {
            $deploy = Get-AzResourceGroupDeployment -ResourceGroupName $resourceGroup -Name $deploymentName -ErrorAction SilentlyContinue
        }
        if (-not $deploy) {
            Write-Host "Trying latest deployment in resource group..."
            $deploys = @(Get-AzResourceGroupDeployment -ResourceGroupName $resourceGroup | Sort-Object Timestamp -Descending)
            if ($deploys.Count -eq 0) {
                Write-Host "Error: No deployments found in resource group $resourceGroup."
                return $false
            }
            $deploy = $deploys[0]
        }
        if (-not $deploy) {
            Write-Host "Error: Could not fetch deployment."
            return $false
        }
        $deploymentOutputs = $deploy.Outputs
        if (-not $deploymentOutputs -and $deploy.Properties) {
            $deploymentOutputs = $deploy.Properties.Outputs
        }
        if (-not $deploymentOutputs) {
            Write-Host "Error: Deployment has no outputs."
            return $false
        }
    } else {
        Write-Host "Fetching deployment name..."
        $deploymentName = az group show --name $resourceGroup --query "tags.DeploymentName" -o tsv
        if (-not $deploymentName) {
            Write-Host "Error: Could not find deployment name in resource group tags."
            return $false
        }
        Write-Host "Fetching deployment outputs for deployment: $deploymentName"
        $deployJson = az deployment group show --resource-group $resourceGroup --name $deploymentName --query "properties.outputs" -o json
        $deploymentOutputs = $deployJson | ConvertFrom-Json
        if (-not $deploymentOutputs) {
            Write-Host "Error: Could not fetch deployment outputs."
            return $false
        }
    }
    
    # Extract all values using the helper function
    $script:projectEndpoint = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azureAiAgentEndpoint" -FallbackKey "AZURE_AI_AGENT_ENDPOINT"
    $script:solutionName = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "solutionName" -FallbackKey "SOLUTION_NAME"
    $script:gptModelName = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azureAiAgentModelDeploymentName" -FallbackKey "AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME"
    $script:aiFoundryResourceId = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "aiFoundryResourceId" -FallbackKey "AI_FOUNDRY_RESOURCE_ID"
    $script:apiAppName = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "apiAppName" -FallbackKey "API_APP_NAME"
    $script:searchEndpoint = Get-DeploymentValue -DeploymentOutputs $deploymentOutputs -PrimaryKey "azureAiSearchEndpoint" -FallbackKey "AZURE_AI_SEARCH_ENDPOINT"
    
    # Validate that we extracted all required values (trim whitespace; null/empty = failed)
    $script:projectEndpoint = ($script:projectEndpoint ?? '').ToString().Trim()
    $script:solutionName = ($script:solutionName ?? '').ToString().Trim()
    $script:gptModelName = ($script:gptModelName ?? '').ToString().Trim()
    $script:aiFoundryResourceId = ($script:aiFoundryResourceId ?? '').ToString().Trim()
    $script:apiAppName = ($script:apiAppName ?? '').ToString().Trim()
    $script:searchEndpoint = ($script:searchEndpoint ?? '').ToString().Trim()

    if (-not $script:projectEndpoint -or -not $script:solutionName -or -not $script:gptModelName -or -not $script:aiFoundryResourceId -or -not $script:apiAppName -or -not $script:searchEndpoint) {
        Write-Host "Error: Could not extract all required values from deployment outputs."
        Write-Host "Extracted: projectEndpoint=[$script:projectEndpoint], solutionName=[$script:solutionName], gptModelName=[$script:gptModelName], aiFoundryResourceId=[$script:aiFoundryResourceId], apiAppName=[$script:apiAppName], searchEndpoint=[$script:searchEndpoint]"
        if ($script:UseAzPowerShell -and $deploymentOutputs) {
            $keys = if ($deploymentOutputs -is [System.Collections.IDictionary]) { @($deploymentOutputs.Keys) } elseif ($deploymentOutputs -is [hashtable]) { @($deploymentOutputs.Keys) } else { @($deploymentOutputs.PSObject.Properties.Name) }
            Write-Host "Available output keys: $($keys -join ', ')"
        }
        return $false
    }
    
    Write-Host "Successfully retrieved values from deployment outputs."
    return $true
}

# Authenticate with Azure (Az PowerShell si az CLI falla por purview)
$azOk = $false
try {
    $null = az account show 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $azOk = $true }
} catch { }
if (-not $azOk) {
    Write-Host "az CLI no disponible (ej. purview). Usando Az PowerShell..." -ForegroundColor Yellow
    $azModules = @("Az.Accounts", "Az.Resources", "Az.CognitiveServices", "Az.Websites")
    foreach ($m in $azModules) {
        if (-not (Get-Module -ListAvailable -Name $m)) {
            Install-Module -Name $m -Scope CurrentUser -Force -AllowClobber
        }
    }
    Import-Module Az.Accounts, Az.Resources, Az.CognitiveServices, Az.Websites -ErrorAction Stop
    $ctx = Get-AzContext -ErrorAction SilentlyContinue
    if (-not $ctx) {
        Connect-AzAccount -ErrorAction Stop | Out-Null
    }
    $script:UseAzPowerShell = $true
} else {
    Write-Host "Already authenticated with Azure (az CLI)."
    $script:UseAzPowerShell = $false
}

# Get subscription ID from azd if available
if (Test-AzdInstalled) {
    try {
        $azSubscriptionId = $(azd env get-value AZURE_SUBSCRIPTION_ID 2>$null)
        if (-not $azSubscriptionId -or $azSubscriptionId -match "ERROR:") {
            $azSubscriptionId = $env:AZURE_SUBSCRIPTION_ID
        }
    } catch {
        $azSubscriptionId = $env:AZURE_SUBSCRIPTION_ID
    }
}

# Get current subscription (az o Az PowerShell)
if ($script:UseAzPowerShell) {
    $ctx = Get-AzContext -ErrorAction Stop
    $currentSubscriptionId = $ctx.Subscription.Id
    $currentSubscriptionName = $ctx.Subscription.Name
    if (-not $azSubscriptionId) { $azSubscriptionId = $currentSubscriptionId }
} else {
    if (-not $azSubscriptionId) {
        $azSubscriptionId = az account show --query id -o tsv
    }
    $currentSubscriptionId = az account show --query id -o tsv
    $currentSubscriptionName = az account show --query name -o tsv
}

if ($currentSubscriptionId -ne $azSubscriptionId -and $azSubscriptionId) {
    Write-Host "Current selected subscription is $currentSubscriptionName ( $currentSubscriptionId )."
    $confirmation = Read-Host "Do you want to continue with this subscription?(y/n)"
    if ($confirmation -notin @("y", "Y")) {
        Write-Host "Fetching available subscriptions..."
        if ($script:UseAzPowerShell) {
            $subs = Get-AzSubscription | Where-Object State -eq "Enabled"
            $availableSubscriptions = $subs | ForEach-Object { ,@($_.Name, $_.Id) }
        } else {
            $availableSubscriptions = az account list --query "[?state=='Enabled'].[name,id]" --output json | ConvertFrom-Json
        }
        do {
            Write-Host ""
            Write-Host "Available Subscriptions:"
            Write-Host "========================"
            for ($i = 0; $i -lt $availableSubscriptions.Count; $i++) {
                $index = $i + 1
                $n = $availableSubscriptions[$i][0]; $id = $availableSubscriptions[$i][1]
                Write-Host "$index. $n ( $id )"
            }
            Write-Host "========================"
            Write-Host ""
            $subscriptionIndex = Read-Host "Enter the number of the subscription (1-$($availableSubscriptions.Count)) to use"
            if ($subscriptionIndex -match '^\d+$' -and [int]$subscriptionIndex -ge 1 -and [int]$subscriptionIndex -le $availableSubscriptions.Count) {
                $selectedIndex = [int]$subscriptionIndex - 1
                $selectedSubscriptionName = $availableSubscriptions[$selectedIndex][0]
                $selectedSubscriptionId = $availableSubscriptions[$selectedIndex][1]
                if ($script:UseAzPowerShell) {
                    Set-AzContext -SubscriptionId $selectedSubscriptionId -ErrorAction Stop
                } else {
                    az account set --subscription $selectedSubscriptionId
                }
                Write-Host "Switched to subscription: $selectedSubscriptionName ( $selectedSubscriptionId )"
                $azSubscriptionId = $selectedSubscriptionId
                break
            } else {
                Write-Host "Invalid selection. Please try again."
            }
        } while ($true)
    } else {
        if ($script:UseAzPowerShell) { Set-AzContext -SubscriptionId $currentSubscriptionId | Out-Null }
        else { az account set --subscription $currentSubscriptionId }
        $azSubscriptionId = $currentSubscriptionId
    }
} else {
    Write-Host "Proceeding with the subscription: $currentSubscriptionName ( $currentSubscriptionId )"
    if ($script:UseAzPowerShell) { Set-AzContext -SubscriptionId $currentSubscriptionId | Out-Null }
    else { az account set --subscription $currentSubscriptionId }
    $azSubscriptionId = $currentSubscriptionId
}

# Get configuration values based on strategy
if (-not $resourceGroup) {
    # No resource group provided - use azd env
    if (-not (Get-ValuesFromAzdEnv)) {
        Write-Host "Failed to get values from azd environment."
        Write-Host "If you want to use deployment outputs instead, please provide the resource group name as an argument."
        Write-Host "Usage: .\run_create_agents_scripts.ps1 -resourceGroup <ResourceGroupName>"
        exit 1
    }
} else {
    # Resource group provided - use deployment outputs
    Write-Host "Resource group provided: $resourceGroup"
    
    if (-not (Get-ValuesFromAzDeployment)) {
        Write-Host "Failed to get values from deployment outputs."
        exit 1
    }
}

# Override con DSPM-AI-Project si se especificó
if ($ProjectEndpointOverride) {
    Write-Host "Using DSPM-AI-Project override for project endpoint."
    $script:projectEndpoint = $ProjectEndpointOverride
    if ($AiFoundryResourceIdOverride) {
        $script:aiFoundryResourceId = $AiFoundryResourceIdOverride
    } else {
        Write-Host "Warning: AiFoundryResourceIdOverride not set. Role check may fail. Use -AiFoundryResourceIdOverride for DSPM-AI-Project."
    }
}

# Override de modelo para reducir latencia (gpt-4o-mini es más rápido)
if ($GptModelOverride) {
    Write-Host "Using model override: $GptModelOverride (faster responses)"
    $script:gptModelName = $GptModelOverride
}

Write-Host ""
Write-Host "==============================================="
Write-Host "Values to be used:"
Write-Host "==============================================="
Write-Host "Resource Group: $resourceGroup"
Write-Host "Project Endpoint: $projectEndpoint"
Write-Host "Solution Name: $solutionName"
Write-Host "GPT Model Name: $gptModelName"
Write-Host "AI Foundry Resource ID: $aiFoundryResourceId"
Write-Host "API App Name: $apiAppName"
Write-Host "Search Endpoint: $searchEndpoint"
Write-Host "Subscription ID: $azSubscriptionId"
Write-Host "==============================================="
Write-Host ""

Write-Host "Getting signed in user id"
if ($script:UseAzPowerShell) {
    $ctx = Get-AzContext -ErrorAction Stop
    $currentUser = Get-AzADUser -UserPrincipalName $ctx.Account.Id -ErrorAction SilentlyContinue
    if (-not $currentUser) { $currentUser = Get-AzADUser -Mail $ctx.Account.Id -ErrorAction SilentlyContinue }
    $signed_user_id = $currentUser.Id
    if (-not $signed_user_id) {
        Write-Host "Warning: Could not get user object ID. Role assignment may fail."
        $signed_user_id = $ctx.Account.Id
    }
} else {
    $signed_user_id = az ad signed-in-user show --query id -o tsv
}

Write-Host "Checking if the user has Azure AI User role on the AI Foundry"
$roleDefinitionId = "53ca6127-db72-4b80-b1b0-d745d6d5456d"  # Cognitive Services User
if ($script:UseAzPowerShell) {
    $existing = Get-AzRoleAssignment -ObjectId $signed_user_id -Scope $aiFoundryResourceId -RoleDefinitionId $roleDefinitionId -ErrorAction SilentlyContinue
    if (-not $existing) {
        Write-Host "User does not have the Azure AI User role. Assigning the role..."
        New-AzRoleAssignment -ObjectId $signed_user_id -RoleDefinitionId $roleDefinitionId -Scope $aiFoundryResourceId -ErrorAction Stop
        Write-Host "Azure AI User role assigned successfully."
    } else {
        Write-Host "User already has the Azure AI User role."
    }
} else {
    $role_assignment = az role assignment list --role $roleDefinitionId --scope "$aiFoundryResourceId" --assignee "$signed_user_id" --query "[].roleDefinitionId" -o tsv
    if ([string]::IsNullOrEmpty($role_assignment)) {
        Write-Host "User does not have the Azure AI User role. Assigning the role..."
        az role assignment create --assignee "$signed_user_id" --role $roleDefinitionId --scope "$aiFoundryResourceId" --output none
        if ($LASTEXITCODE -eq 0) { Write-Host "Azure AI User role assigned successfully." }
        else { Write-Host "Failed to assign Azure AI User role."; exit 1 }
    } else {
        Write-Host "User already has the Azure AI User role."
    }
}

$requirementFile = "infra/scripts/agent_scripts/requirements.txt"

# Download and install Python requirements
Write-Host "Installing Python requirements..."
python -m pip install --upgrade pip
python -m pip install --quiet -r "$requirementFile"

# For WAF deployments, temporarily enable public network access on AI Foundry
Write-Host "Checking AI Foundry network settings..."

# Extract the AI Foundry account resource ID (remove /projects/... part if present)
$aifAccountResourceId = $aiFoundryResourceId -replace '/projects/.*', ''
$aifResourceName = Split-Path -Leaf $aifAccountResourceId
# Extract resource group from the AI Foundry account resource ID
if ($aifAccountResourceId -match '/resourceGroups/([^/]+)/') {
    $aifResourceGroup = $Matches[1]
}
# Extract subscription ID from the AI Foundry account resource ID
if ($aifAccountResourceId -match '/subscriptions/([^/]+)/') {
    $aifSubscriptionId = $Matches[1]
}

# Get current public network access setting
if ($script:UseAzPowerShell) {
    $aifAccount = Get-AzCognitiveServicesAccount -ResourceGroupName $aifResourceGroup -Name $aifResourceName -ErrorAction SilentlyContinue
    $originalFoundryPublicAccess = $aifAccount.PublicNetworkAccess
} else {
    $originalFoundryPublicAccess = az cognitiveservices account show --name $aifResourceName --resource-group $aifResourceGroup --subscription $aifSubscriptionId --query "properties.publicNetworkAccess" -o tsv 2>$null
}
$foundryAccessEnabled = $false

# Check if public network access is disabled (WAF deployment)
if ($originalFoundryPublicAccess -eq "Disabled") {
    Write-Host "AI Foundry public network access is disabled. Temporarily enabling for agent creation..."
    if ($script:UseAzPowerShell) {
        try {
            Update-AzCognitiveServicesAccount -ResourceGroupName $aifResourceGroup -Name $aifResourceName -PublicNetworkAccess Enabled -ErrorAction Stop
            Write-Host "Successfully enabled public network access on AI Foundry."
            $foundryAccessEnabled = $true
        } catch {
            Write-Host "Warning: Could not enable public network access. You may need to enable it manually in Azure Portal."
        }
    } else {
        az resource update --ids $aifAccountResourceId --api-version 2024-10-01 --set "properties.publicNetworkAccess=Enabled" "properties.apiProperties={}" --output none 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Successfully enabled public network access on AI Foundry."
            $foundryAccessEnabled = $true
        } else {
            Write-Host "Warning: Could not enable public network access. You may need to enable it manually in Azure Portal."
        }
    }
    
    # Wait for the update to propagate
    Write-Host "Waiting for network settings to propagate (60 seconds)..."
    Start-Sleep -Seconds 60
} else {
    Write-Host "AI Foundry public network access is already enabled."
}

# Execute the Python scripts within try/finally to ensure network settings are restored on error
try {
    Write-Host "Running Python agents creation script..."
    $python_output = python infra/scripts/agent_scripts/01_create_agents.py --ai_project_endpoint="$projectEndpoint" --solution_name="$solutionName" --gpt_model_name="$gptModelName" --ai_search_endpoint="$searchEndpoint"

    if ($LASTEXITCODE -ne 0) {
        throw "Python agent creation script failed with exit code $LASTEXITCODE"
    }

    # Parse the output to extract agent names
    $chatAgentName = ""
    $productAgentName = ""
    $policyAgentName = ""

    foreach ($line in $python_output) {
        if ($line -match "^chatAgentName=(.+)$") {
            $chatAgentName = $Matches[1]
        }
        elseif ($line -match "^productAgentName=(.+)$") {
            $productAgentName = $Matches[1]
        }
        elseif ($line -match "^policyAgentName=(.+)$") {
            $policyAgentName = $Matches[1]
        }
    }

    Write-Host "Agents creation completed."
    Write-Host "Chat Agent Name: $chatAgentName"
    Write-Host "Product Agent Name: $productAgentName"
    Write-Host "Policy Agent Name: $policyAgentName"

    # Update environment variables of API App
    Write-Host "Updating environment variables for App Service: $apiAppName"
    $settingsArgs = @{
        FOUNDRY_CHAT_AGENT = $chatAgentName
        FOUNDRY_PRODUCT_AGENT = $productAgentName
        FOUNDRY_POLICY_AGENT = $policyAgentName
    }
    if ($ProjectEndpointOverride) {
        $settingsArgs["AZURE_FOUNDRY_ENDPOINT"] = $projectEndpoint
        $settingsArgs["AZURE_AI_AGENT_ENDPOINT"] = $projectEndpoint
    }
    if ($script:UseAzPowerShell) {
        $webApp = Get-AzWebApp -ResourceGroupName $resourceGroup -Name $apiAppName
        $hash = @{}
        foreach ($s in $webApp.SiteConfig.AppSettings) { $hash[$s.Name] = $s.Value }
        foreach ($k in $settingsArgs.Keys) { $hash[$k] = $settingsArgs[$k] }
        Set-AzWebApp -ResourceGroupName $resourceGroup -Name $apiAppName -AppSettings $hash | Out-Null
    } else {
        $settingsList = $settingsArgs.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }
        az webapp config appsettings set --resource-group "$resourceGroup" --name "$apiAppName" --settings $settingsList -o none
        if ($LASTEXITCODE -ne 0) { throw "Failed to update App Service environment variables" }
    }

    Write-Host "Environment variables updated for App Service: $apiAppName"
    Write-Host "Agent creation script completed successfully."
}
catch {
    Write-Host "Error occurred during agent creation: $_"
    $script:agentCreationFailed = $true
}
finally {
    # Restore original settings - disable public network access if we enabled it
    if ($foundryAccessEnabled) {
        Write-Host "Restoring original AI Foundry settings (disabling public network access)..."
        if ($script:UseAzPowerShell) {
            try {
                Update-AzCognitiveServicesAccount -ResourceGroupName $aifResourceGroup -Name $aifResourceName -PublicNetworkAccess Disabled -ErrorAction Stop
                Write-Host "Successfully disabled public network access on AI Foundry."
            } catch {
                Write-Host "Warning: Could not disable public network access. Please disable it manually in Azure Portal."
            }
        } else {
            az resource update --ids $aifAccountResourceId --api-version 2024-10-01 --set "properties.publicNetworkAccess=Disabled" "properties.apiProperties.qnaAzureSearchEndpointKey=" "properties.networkAcls.bypass=AzureServices" --output none 2>$null
            if ($LASTEXITCODE -eq 0) { Write-Host "Successfully disabled public network access on AI Foundry." }
            else { Write-Host "Warning: Could not disable public network access. Please disable it manually in Azure Portal." }
        }
    }
}

# Exit with error if agent creation failed
if ($script:agentCreationFailed) {
    Write-Host "Agent creation script failed. Network settings have been restored."
    exit 1
}