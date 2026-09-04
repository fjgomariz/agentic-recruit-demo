@description('Name of the Azure Container Apps managed environment.')
param environmentName string

@description('Name of the existing Log Analytics workspace.')
param logAnalyticsName string

@description('Azure region for the Container Apps environment.')
param location string

@description('Resource ID of the dedicated Container Apps infrastructure subnet.')
param infrastructureSubnetId string

@description('Common resource tags.')
param tags object

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2025-07-01' existing = {
  name: logAnalyticsName
}

// External workload-profiles environment with private access to backend data services.
resource environment 'Microsoft.App/managedEnvironments@2025-07-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
    publicNetworkAccess: 'Enabled'
    vnetConfiguration: {
      infrastructureSubnetId: infrastructureSubnetId
      internal: false
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

output environmentName string = environment.name
output environmentId string = environment.id
output defaultDomain string = environment.properties.defaultDomain
