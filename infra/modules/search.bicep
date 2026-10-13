@description('Globally unique name of the Azure AI Search service.')
param searchServiceName string

@description('Azure region. The service must be in a region that supports agentic retrieval and the semantic ranker.')
param location string

@description('Common resource tags.')
param tags object

@description('Resource ID of the storage account that holds the knowledge source containers.')
param storageAccountId string

@description('Message shown on the pending private endpoint connection of the storage account. The deployment approves only connections with this exact message.')
param privateLinkRequestMessage string

// Entra ID only: keys are disabled, so every caller needs a Search data-plane role.
// The endpoint stays public so the Foundry agent can reach the knowledge base over MCP.
resource searchService 'Microsoft.Search/searchServices@2025-05-01' = {
  name: searchServiceName
  location: location
  tags: tags
  sku: {
    name: 'basic'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    partitionCount: 1
    replicaCount: 1
    publicNetworkAccess: 'enabled'
    disableLocalAuth: true
    semanticSearch: 'standard'
    networkRuleSet: {
      bypass: 'None'
      ipRules: []
    }
  }
}

// Lets the indexers read the private storage account. The connection stays Pending until it is
// approved on the storage account (infra/scripts/approve-search-private-link.sh).
resource blobSharedPrivateLink 'Microsoft.Search/searchServices/sharedPrivateLinkResources@2025-05-01' = {
  parent: searchService
  name: 'spl-blob'
  properties: {
    groupId: 'blob'
    privateLinkResourceId: storageAccountId
    requestMessage: privateLinkRequestMessage
  }
}

output searchServiceName string = searchService.name
output searchServiceId string = searchService.id
output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
output principalId string = searchService.identity.principalId
