@description('Name of the user-assigned managed identity.')
param name string

@description('Azure region for the identity.')
param location string

@description('Common resource tags.')
param tags object

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: name
  location: location
  tags: tags
}

output id string = identity.id
output clientId string = identity.properties.clientId
output principalId string = identity.properties.principalId
