@description('Name of the existing Foundry (AI Services) account.')
param accountName string

@description('Principal that receives the role on the account.')
param principalId string

@description('Built-in role definition ID (GUID) to assign.')
param roleDefinitionId string

@description('Principal type of the assignee.')
@allowed([
  'ServicePrincipal'
  'User'
  'Group'
])
param principalType string = 'ServicePrincipal'

resource account 'Microsoft.CognitiveServices/accounts@2026-07-01' existing = {
  name: accountName
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, principalId, roleDefinitionId)
  properties: {
    principalId: principalId
    principalType: principalType
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionId)
  }
}
