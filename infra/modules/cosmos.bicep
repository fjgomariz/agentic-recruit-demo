@description('Globally unique Azure Cosmos DB account name.')
param accountName string

@description('Name of the Cosmos DB SQL database.')
param databaseName string

@description('Name of the id-partitioned jobs container.')
param jobsContainerName string = 'jobs'

@description('Azure region for Cosmos DB.')
param location string

@description('Common resource tags.')
param tags object

// Serverless Cosmos DB provides a low-cost SQL API data store for the demo.
resource account 'Microsoft.DocumentDB/databaseAccounts@2026-03-15' = {
  name: accountName
  location: location
  kind: 'GlobalDocumentDB'
  tags: tags
  properties: {
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    databaseAccountOfferType: 'Standard'
    disableLocalAuth: true
    locations: [
      {
        failoverPriority: 0
        isZoneRedundant: false
        locationName: location
      }
    ]
    minimalTlsVersion: 'Tls12'
    publicNetworkAccess: 'Disabled'
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2026-03-15' = {
  parent: account
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

// Containers are control-plane resources: Entra ID data-plane roles cannot create them at runtime.
resource jobsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2026-03-15' = {
  parent: database
  name: jobsContainerName
  properties: {
    resource: {
      id: jobsContainerName
      partitionKey: {
        paths: [
          '/id'
        ]
        kind: 'Hash'
      }
    }
  }
}

output accountName string = account.name
output accountId string = account.id
output databaseName string = database.name
output jobsContainerName string = jobsContainer.name
output endpoint string = account.properties.documentEndpoint
output endpointHostname string = '${account.name}.documents.azure.com'
