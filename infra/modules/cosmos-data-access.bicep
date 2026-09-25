@description('Name of the existing Cosmos DB account.')
param accountName string

@description('Principal ID of the identity that needs Cosmos DB data-plane access.')
param principalId string

resource account 'Microsoft.DocumentDB/databaseAccounts@2026-03-15' existing = {
  name: accountName
}

// Cosmos DB Built-in Data Contributor: item read/write only, no account or container management.
var dataContributorRoleId = '${account.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'

resource dataContributor 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2026-03-15' = {
  parent: account
  name: guid(account.id, principalId, dataContributorRoleId)
  properties: {
    principalId: principalId
    roleDefinitionId: dataContributorRoleId
    scope: account.id
  }
}
