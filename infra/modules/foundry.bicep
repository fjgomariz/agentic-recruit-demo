@description('Globally unique name of the Foundry (AI Services) account. Also used as its custom subdomain.')
param accountName string

@description('Name of the Foundry project that hosts the recruitment agents.')
param projectName string

@description('Azure region for the Foundry account and project.')
param location string

@description('Common resource tags.')
param tags object

@description('Name of the existing workspace-based Application Insights resource used for agent tracing.')
param applicationInsightsName string

@description('Model deployments used by the agents: name, model, version, skuName, capacity (thousands of tokens per minute). The first is the default model.')
param modelDeployments array

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: applicationInsightsName
}

// Entra ID only: keys are disabled, so every caller needs a Foundry data-plane role.
resource account 'Microsoft.CognitiveServices/accounts@2026-07-01' = {
  name: accountName
  location: location
  tags: tags
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: accountName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2026-07-01' = {
  parent: account
  name: projectName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: 'Recruitment Foundry'
    description: 'Agents for the Recruitment Foundry Demo.'
  }
}

// One at a time and after the project: concurrent writes on one account are rejected.
@batchSize(1)
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2026-07-01' = [for deployment in modelDeployments: {
  parent: account
  name: deployment.name
  dependsOn: [
    project
  ]
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
    // Pinned so agent behavior only changes through a reviewed version bump.
    versionUpgradeOption: 'NoAutoUpgrade'
  }
}]

// Connecting Application Insights enables server-side tracing for every agent in the project.
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

output accountName string = account.name
output projectName string = project.name
output projectId string = project.id
output projectEndpoint string = 'https://${account.properties.customSubDomainName}.services.ai.azure.com/api/projects/${project.name}'
output modelDeploymentName string = modelDeployment[0].name
output modelDeploymentNames array = [for (deployment, index) in modelDeployments: modelDeployment[index].name]
