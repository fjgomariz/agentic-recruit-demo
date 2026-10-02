@description('Name of the existing Foundry account.')
param accountName string

@description('Name of the existing Foundry project.')
param projectName string

@description('Principal that receives the role on the project.')
param principalId string

@description('Built-in role definition ID (GUID) to assign.')
param roleDefinitionId string

@description('Principal type. Leave empty to let Azure resolve it.')
@allowed([
  ''
  'ServicePrincipal'
  'User'
  'Group'
])
param principalType string = ''

resource account 'Microsoft.CognitiveServices/accounts@2026-07-01' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2026-07-01' existing = {
  parent: account
  name: projectName
}

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: project
  name: guid(project.id, principalId, roleDefinitionId)
  properties: {
    principalId: principalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleDefinitionId)
    principalType: empty(principalType) ? null : principalType
  }
}
