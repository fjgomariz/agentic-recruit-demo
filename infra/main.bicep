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

@description('API container image. When any image is empty, only the shared foundation is deployed.')
param apiImage string = ''

@description('Public portal container image.')
param publicPortalImage string = ''

@description('Recruiter portal container image.')
param recruiterPortalImage string = ''

@description('Object ID of the identity running the deployment. It receives Foundry User on the project so it can publish agent versions. Empty skips the assignment.')
param deploymentPrincipalId string = ''

@description('Foundry model deployments. The first is the default for agents that do not choose a model. Deployment names must match the "modelDeployment" values in agents/*/agent.json.')
param agentModelDeployments array = [
  {
    name: 'gpt-5.4-mini'
    model: 'gpt-5.4-mini'
    version: '2026-03-17'
    skuName: 'GlobalStandard'
    capacity: 50
  }
  {
    name: 'gpt-5.4'
    model: 'gpt-5.4'
    version: '2026-03-05'
    skuName: 'GlobalStandard'
    capacity: 500
  }
]

@description('Name of the Foundry agent that drafts job descriptions.')
param jobDescriptionAgentName string = 'job-description-writer'

@description('Name of the Foundry agent that evaluates candidate resumes.')
param candidateEvaluationAgentName string = 'candidate-evaluator'

@description('Name of the Foundry agent that reviews candidate evaluations.')
param candidateReviewAgentName string = 'candidate-evaluation-reviewer'

var deployApps = !empty(apiImage) && !empty(publicPortalImage) && !empty(recruiterPortalImage)

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
var apiIdentityName = 'id-${workloadName}-api-${environmentName}'
var apiAppName = 'ca-${workloadName}-api-${environmentName}'
var publicPortalAppName = 'ca-${workloadName}-public-${environmentName}'
var recruiterPortalAppName = 'ca-${workloadName}-recruiter-${environmentName}'
var foundryAccountName = take('aif-${workloadName}-${environmentName}-${uniqueToken}', 64)
var foundryProjectName = 'proj-${workloadName}-${environmentName}'

// Built-in Foundry data-plane role.
var foundryUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'

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

module apiIdentity './modules/user-assigned-identity.bicep' = {
  scope: resourceGroup
  params: {
    location: location
    name: apiIdentityName
    tags: tags
  }
}

// Granted before the API starts so the first revision can reach Cosmos DB.
module apiCosmosAccess './modules/cosmos-data-access.bicep' = {
  scope: resourceGroup
  params: {
    accountName: cosmos.outputs.accountName
    principalId: apiIdentity.outputs.principalId
  }
}

// The API uploads and downloads resumes in the private resumes container only.
module apiResumesAccess './modules/blob-container-access.bicep' = {
  scope: resourceGroup
  params: {
    storageAccountName: storage.outputs.storageAccountName
    containerName: storage.outputs.resumesContainerName
    principalId: apiIdentity.outputs.principalId
  }
}

module foundry './modules/foundry.bicep' = {
  scope: resourceGroup
  params: {
    accountName: foundryAccountName
    projectName: foundryProjectName
    location: location
    tags: tags
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    modelDeployments: agentModelDeployments
  }
}

// Calling an agent by reference through the project endpoint reads the agent definition, which the
// narrower Foundry Project Runtime User role (responses/* only) does not allow.
module apiFoundryAccess './modules/foundry-project-role.bicep' = {
  scope: resourceGroup
  params: {
    accountName: foundry.outputs.accountName
    projectName: foundry.outputs.projectName
    principalId: apiIdentity.outputs.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: foundryUserRoleId
  }
}

// The deployment identity publishes agent versions after provisioning.
module deployerFoundryAccess './modules/foundry-project-role.bicep' = if (!empty(deploymentPrincipalId)) {
  scope: resourceGroup
  params: {
    accountName: foundry.outputs.accountName
    projectName: foundry.outputs.projectName
    principalId: deploymentPrincipalId
    roleDefinitionId: foundryUserRoleId
  }
}

module api './modules/container-app.bicep' = if (deployApps) {
  scope: resourceGroup
  dependsOn: [
    apiCosmosAccess
    apiFoundryAccess
    apiResumesAccess
    blobPrivateEndpoint
    cosmosPrivateEndpoint
  ]
  params: {
    name: apiAppName
    location: location
    tags: tags
    environmentId: containerApps.outputs.environmentId
    image: apiImage
    targetPort: 8000
    healthPath: '/health'
    userAssignedIdentityId: apiIdentity.outputs.id
    env: [
      { name: 'AZURE_CLIENT_ID', value: apiIdentity.outputs.clientId }
      { name: 'AZURE_COSMOS_ENDPOINT', value: cosmos.outputs.endpoint }
      { name: 'AZURE_COSMOS_DATABASE_NAME', value: cosmos.outputs.databaseName }
      { name: 'AZURE_COSMOS_JOBS_CONTAINER_NAME', value: cosmos.outputs.jobsContainerName }
      { name: 'AZURE_COSMOS_APPLICATIONS_CONTAINER_NAME', value: cosmos.outputs.applicationsContainerName }
      { name: 'AZURE_COSMOS_AGENT_EXECUTIONS_CONTAINER_NAME', value: cosmos.outputs.agentExecutionsContainerName }
      { name: 'AZURE_STORAGE_BLOB_ENDPOINT', value: storage.outputs.blobEndpoint }
      { name: 'AZURE_STORAGE_RESUMES_CONTAINER_NAME', value: storage.outputs.resumesContainerName }
      { name: 'AZURE_AI_PROJECT_ENDPOINT', value: foundry.outputs.projectEndpoint }
      { name: 'JOB_DESCRIPTION_AGENT_NAME', value: jobDescriptionAgentName }
      { name: 'CANDIDATE_EVALUATION_AGENT_NAME', value: candidateEvaluationAgentName }
      { name: 'CANDIDATE_REVIEW_AGENT_NAME', value: candidateReviewAgentName }
      { name: 'AZURE_AI_MODEL_DEPLOYMENT_NAME', value: foundry.outputs.modelDeploymentName }
      { name: 'OTEL_SERVICE_NAME', value: 'recruitment-api' }
    ]
    secretEnv: {
      APPLICATIONINSIGHTS_CONNECTION_STRING: monitoring.outputs.applicationInsightsConnectionString
    }
  }
}

module publicPortal './modules/container-app.bicep' = if (deployApps) {
  scope: resourceGroup
  params: {
    name: publicPortalAppName
    location: location
    tags: tags
    environmentId: containerApps.outputs.environmentId
    image: publicPortalImage
    targetPort: 3000
    env: [
      { name: 'API_BASE_URL', value: api!.outputs.url }
    ]
  }
}

module recruiterPortal './modules/container-app.bicep' = if (deployApps) {
  scope: resourceGroup
  params: {
    name: recruiterPortalAppName
    location: location
    tags: tags
    environmentId: containerApps.outputs.environmentId
    image: recruiterPortalImage
    targetPort: 3000
    env: [
      { name: 'API_BASE_URL', value: api!.outputs.url }
    ]
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
output AZURE_COSMOS_APPLICATIONS_CONTAINER_NAME string = cosmos.outputs.applicationsContainerName
output AZURE_STORAGE_RESUMES_CONTAINER_NAME string = storage.outputs.resumesContainerName
output AZURE_COSMOS_ENDPOINT string = cosmos.outputs.endpoint
output AZURE_COSMOS_ENDPOINT_HOSTNAME string = cosmos.outputs.endpointHostname
output AZURE_CONTAINER_APPS_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output AZURE_CONTAINER_APPS_ENVIRONMENT_ID string = containerApps.outputs.environmentId
output AZURE_CONTAINER_APPS_DEFAULT_DOMAIN string = containerApps.outputs.defaultDomain
output AZURE_BLOB_PRIVATE_DNS_ZONE_NAME string = blobPrivateDns.outputs.privateDnsZoneName
output AZURE_COSMOS_PRIVATE_DNS_ZONE_NAME string = cosmosPrivateDns.outputs.privateDnsZoneName
output AZURE_BLOB_PRIVATE_ENDPOINT_ID string = blobPrivateEndpoint.outputs.privateEndpointId
output AZURE_COSMOS_PRIVATE_ENDPOINT_ID string = cosmosPrivateEndpoint.outputs.privateEndpointId
output AZURE_API_IDENTITY_CLIENT_ID string = apiIdentity.outputs.clientId
output AZURE_AI_ACCOUNT_NAME string = foundry.outputs.accountName
output AZURE_AI_PROJECT_NAME string = foundry.outputs.projectName
output AZURE_AI_PROJECT_ENDPOINT string = foundry.outputs.projectEndpoint
output AZURE_AI_MODEL_DEPLOYMENT_NAME string = foundry.outputs.modelDeploymentName
output JOB_DESCRIPTION_AGENT_NAME string = jobDescriptionAgentName
output CANDIDATE_EVALUATION_AGENT_NAME string = candidateEvaluationAgentName
output CANDIDATE_REVIEW_AGENT_NAME string = candidateReviewAgentName
output AZURE_AI_MODEL_DEPLOYMENT_NAMES array = foundry.outputs.modelDeploymentNames
output API_URL string = deployApps ? api!.outputs.url : ''
output PUBLIC_PORTAL_URL string = deployApps ? publicPortal!.outputs.url : ''
output RECRUITER_PORTAL_URL string = deployApps ? recruiterPortal!.outputs.url : ''

@secure()
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.applicationInsightsConnectionString
