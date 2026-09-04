@description('Name of the Log Analytics workspace.')
param logAnalyticsName string

@description('Name of the Application Insights component.')
param applicationInsightsName string

@description('Azure region for monitoring resources.')
param location string

@description('Common resource tags.')
param tags object

// Central workspace for platform logs, traces, and future diagnostic settings.
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2025-07-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

// Workspace-based Application Insights collects application telemetry.
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: applicationInsightsName
  location: location
  kind: 'web'
  tags: tags
  properties: {
    Application_Type: 'web'
    IngestionMode: 'LogAnalytics'
    WorkspaceResourceId: logAnalytics.id
  }
}

output logAnalyticsWorkspaceName string = logAnalytics.name
output logAnalyticsWorkspaceId string = logAnalytics.id
output applicationInsightsName string = applicationInsights.name
output applicationInsightsId string = applicationInsights.id

@secure()
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
