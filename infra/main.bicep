targetScope = 'subscription'

metadata name = 'Recruitment Foundry Demo foundation'
metadata description = 'Deploys the shared Azure foundation for the Recruitment Foundry Demo.'

@description('Short environment name used in resource names, such as dev, test, or prod.')
@minLength(2)
@maxLength(12)
param environmentName string

@description('Azure region used for all regional resources.')
param location string = deployment().location

@description('Virtual network address space in CIDR notation.')
param virtualNetworkAddressPrefix string = '10.40.0.0/16'

@description('Dedicated Container Apps subnet address range. A /23 allows room for platform-managed infrastructure.')
param containerAppsSubnetAddressPrefix string = '10.40.0.0/23'

@description('Private endpoints subnet address range.')
param privateEndpointsSubnetAddressPrefix string = '10.40.2.0/24'

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
var virtualNetworkName = 'vnet-${workloadName}-${environmentName}'
var blobPrivateDnsZoneName = 'privatelink.blob.${environment().suffixes.storage}'
var cosmosPrivateDnsZoneName = 'privatelink.documents.azure.com'
var privateDnsVirtualNetworkLinkName = 'link-${virtualNetworkName}'
var blobPrivateEndpointName = 'pe-${storageAccountName}-blob'
var cosmosPrivateEndpointName = 'pe-${cosmosAccountName}-sql'

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

module network './modules/network.bicep' = {
  scope: resourceGroup
  params: {
    containerAppsSubnetAddressPrefix: containerAppsSubnetAddressPrefix
    location: location
    privateEndpointsSubnetAddressPrefix: privateEndpointsSubnetAddressPrefix
    tags: tags
    virtualNetworkAddressPrefix: virtualNetworkAddressPrefix
    virtualNetworkName: virtualNetworkName
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

module blobPrivateDns './modules/private-dns-zone.bicep' = {
  scope: resourceGroup
  params: {
    privateDnsZoneName: blobPrivateDnsZoneName
    tags: tags
    virtualNetworkId: network.outputs.virtualNetworkId
    virtualNetworkLinkName: privateDnsVirtualNetworkLinkName
  }
}

module cosmosPrivateDns './modules/private-dns-zone.bicep' = {
  scope: resourceGroup
  params: {
    privateDnsZoneName: cosmosPrivateDnsZoneName
    tags: tags
    virtualNetworkId: network.outputs.virtualNetworkId
    virtualNetworkLinkName: privateDnsVirtualNetworkLinkName
  }
}

module blobPrivateEndpoint './modules/private-endpoint.bicep' = {
  scope: resourceGroup
  params: {
    groupId: 'blob'
    location: location
    privateDnsZoneId: blobPrivateDns.outputs.privateDnsZoneId
    privateEndpointName: blobPrivateEndpointName
    privateLinkServiceId: storage.outputs.storageAccountId
    subnetId: network.outputs.privateEndpointsSubnetId
    tags: tags
  }
}

module cosmosPrivateEndpoint './modules/private-endpoint.bicep' = {
  scope: resourceGroup
  params: {
    groupId: 'Sql'
    location: location
    privateDnsZoneId: cosmosPrivateDns.outputs.privateDnsZoneId
    privateEndpointName: cosmosPrivateEndpointName
    privateLinkServiceId: cosmos.outputs.accountId
    subnetId: network.outputs.privateEndpointsSubnetId
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
    infrastructureSubnetId: network.outputs.containerAppsSubnetId
    location: location
    logAnalyticsName: logAnalyticsName
    tags: tags
  }
}

output AZURE_RESOURCE_GROUP string = resourceGroup.name
output AZURE_LOCATION string = location
output AZURE_VIRTUAL_NETWORK_NAME string = network.outputs.virtualNetworkName
output AZURE_VIRTUAL_NETWORK_ID string = network.outputs.virtualNetworkId
output AZURE_CONTAINER_APPS_SUBNET_ID string = network.outputs.containerAppsSubnetId
output AZURE_PRIVATE_ENDPOINTS_SUBNET_ID string = network.outputs.privateEndpointsSubnetId
output AZURE_LOG_ANALYTICS_WORKSPACE_NAME string = monitoring.outputs.logAnalyticsWorkspaceName
output AZURE_APPLICATION_INSIGHTS_NAME string = monitoring.outputs.applicationInsightsName
output AZURE_STORAGE_ACCOUNT_NAME string = storage.outputs.storageAccountName
output AZURE_STORAGE_BLOB_ENDPOINT string = storage.outputs.blobEndpoint
output AZURE_STORAGE_BLOB_HOSTNAME string = storage.outputs.blobHostname
output AZURE_COSMOS_ACCOUNT_NAME string = cosmos.outputs.accountName
output AZURE_COSMOS_DATABASE_NAME string = cosmos.outputs.databaseName
output AZURE_COSMOS_ENDPOINT string = cosmos.outputs.endpoint
output AZURE_COSMOS_ENDPOINT_HOSTNAME string = cosmos.outputs.endpointHostname
output AZURE_CONTAINER_APPS_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output AZURE_CONTAINER_APPS_ENVIRONMENT_ID string = containerApps.outputs.environmentId
output AZURE_CONTAINER_APPS_DEFAULT_DOMAIN string = containerApps.outputs.defaultDomain
output AZURE_BLOB_PRIVATE_DNS_ZONE_NAME string = blobPrivateDns.outputs.privateDnsZoneName
output AZURE_COSMOS_PRIVATE_DNS_ZONE_NAME string = cosmosPrivateDns.outputs.privateDnsZoneName
output AZURE_BLOB_PRIVATE_ENDPOINT_ID string = blobPrivateEndpoint.outputs.privateEndpointId
output AZURE_COSMOS_PRIVATE_ENDPOINT_ID string = cosmosPrivateEndpoint.outputs.privateEndpointId

@secure()
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.applicationInsightsConnectionString
