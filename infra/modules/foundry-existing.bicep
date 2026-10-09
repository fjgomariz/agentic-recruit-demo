@description('Name of the existing Foundry (AI Services) account.')
param accountName string

@description('Name of the existing Foundry project.')
param projectName string

@description('Name of the existing workspace-based Application Insights resource used for agent tracing.')
param applicationInsightsName string

@description('Model deployments used by the agents: name, model, version, skuName, capacity (thousands of tokens per minute). The first is the default model.')
param modelDeployments array

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: applicationInsightsName
}

resource account 'Microsoft.CognitiveServices/accounts@2026-07-01' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2026-07-01' existing = {
  parent: account
  name: projectName
}

// Deploy only child resources so updates do not rewrite the existing account.
@batchSize(1)
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2026-07-01' = [for deployment in modelDeployments: {
  parent: account
  name: deployment.name
  sku: {
    name: deployment.skuName
    capacity: deployment.capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: deployment.model
      version: deployment.version
    }
    versionUpgradeOption: 'NoAutoUpgrade'
  }
}]

resource applicationInsightsConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2026-07-01' = {
  parent: project
  name: applicationInsights.name
  properties: {
    category: 'AppInsights'
    target: applicationInsights.id
    authType: 'ApiKey'
    isSharedToAll: false
    credentials: {
      key: applicationInsights.properties.ConnectionString
    }
    metadata: {
      ApiType: 'Azure'
      ResourceId: applicationInsights.id
    }
  }
}
