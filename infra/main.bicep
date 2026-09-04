targetScope = 'subscription'

metadata name = 'Recruitment Foundry Demo foundation'
metadata description = 'Deploys the shared Azure foundation for the Recruitment Foundry Demo.'

@description('Short environment name used in resource names, such as dev, test, or prod.')
@minLength(2)
@maxLength(12)
param environmentName string

@description('Azure region used for all regional resources.')
param location string = deployment().location

var workloadName = 'recruitment'
var uniqueToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = {
  application: 'Recruitment Foundry Demo'
  environment: environmentName
  managedBy: 'azd'
}

var resourceGroupName = 'rg-${workloadName}-${environmentName}'
var logAnalyticsName = 'log-${workloadName}-${environmentName}'
var applicationInsightsName = 'appi-${workloadName}-${environmentName}'
var storageAccountName = take('st${workloadName}${replace(environmentName, '-', '')}${uniqueToken}', 24)
var cosmosAccountName = take('cosmos-${workloadName}-${environmentName}-${uniqueToken}', 44)
var containerAppsEnvironmentName = 'cae-${workloadName}-${environmentName}'

// The resource group is the lifecycle boundary for the demo environment.
resource resourceGroup 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module monitoring './modules/monitoring.bicep' = {
  scope: resourceGroup
  params: {
    applicationInsightsName: applicationInsightsName
    location: location
    logAnalyticsName: logAnalyticsName
    tags: tags
  }
}

module storage './modules/storage.bicep' = {
  scope: resourceGroup
  params: {
    location: location
    storageAccountName: storageAccountName
    tags: tags
  }
}

module cosmos './modules/cosmos.bicep' = {
  scope: resourceGroup
  params: {
    accountName: cosmosAccountName
    databaseName: 'recruitment'
    location: location
    tags: tags
  }
}

module containerApps './modules/container-apps-environment.bicep' = {
  scope: resourceGroup
  dependsOn: [
    monitoring
  ]
  params: {
    environmentName: containerAppsEnvironmentName
    location: location
    logAnalyticsName: logAnalyticsName
    tags: tags
  }
}

output AZURE_RESOURCE_GROUP string = resourceGroup.name
output AZURE_LOCATION string = location
output AZURE_LOG_ANALYTICS_WORKSPACE_NAME string = monitoring.outputs.logAnalyticsWorkspaceName
output AZURE_APPLICATION_INSIGHTS_NAME string = monitoring.outputs.applicationInsightsName
output AZURE_STORAGE_ACCOUNT_NAME string = storage.outputs.storageAccountName
output AZURE_STORAGE_BLOB_ENDPOINT string = storage.outputs.blobEndpoint
output AZURE_COSMOS_ACCOUNT_NAME string = cosmos.outputs.accountName
output AZURE_COSMOS_DATABASE_NAME string = cosmos.outputs.databaseName
output AZURE_COSMOS_ENDPOINT string = cosmos.outputs.endpoint
output AZURE_CONTAINER_APPS_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output AZURE_CONTAINER_APPS_ENVIRONMENT_ID string = containerApps.outputs.environmentId
output AZURE_CONTAINER_APPS_DEFAULT_DOMAIN string = containerApps.outputs.defaultDomain

@secure()
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.applicationInsightsConnectionString
