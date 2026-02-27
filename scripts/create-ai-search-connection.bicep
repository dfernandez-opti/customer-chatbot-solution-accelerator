// Crear conexión AI Search en proj-default
targetScope = 'resourceGroup'

param searchServiceName string = 'srch-customerchatbotasmzl'
param searchServiceResourceId string
param searchServiceLocation string = 'westus'
param aiFoundryName string = 'DSPM-AI-Project'
param aiFoundryProjectName string = 'proj-default'
param connectionName string = 'aifp-srch-connection-customerchatbotasmzl'

resource aiSearchConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  name: '${aiFoundryName}/${aiFoundryProjectName}/${connectionName}'
  properties: {
    category: 'CognitiveSearch'
    target: 'https://${searchServiceName}.search.windows.net'
    authType: 'AAD'
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: searchServiceResourceId
      location: searchServiceLocation
    }
  }
}
