@description('Name of the private endpoint.')
param privateEndpointName string

@description('Azure region for the private endpoint.')
param location string

@description('Resource ID of the private endpoints subnet.')
param subnetId string

@description('Resource ID of the private link target.')
param privateLinkServiceId string

@description('Private link group ID exposed by the target resource.')
param groupId string

@description('Resource ID of the Private DNS zone associated with the endpoint.')
param privateDnsZoneId string

@description('Common resource tags.')
param tags object

resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-07-01' = {
  name: privateEndpointName
  location: location
  tags: tags
  properties: {
    privateLinkServiceConnections: [
      {
        name: '${privateEndpointName}-connection'
        properties: {
          groupIds: [
            groupId
          ]
          privateLinkServiceId: privateLinkServiceId
        }
      }
    ]
    subnet: {
      id: subnetId
    }
  }
}

resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-07-01' = {
  parent: privateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'configuration'
        properties: {
          privateDnsZoneId: privateDnsZoneId
        }
      }
    ]
  }
}

output privateEndpointId string = privateEndpoint.id
output privateDnsZoneGroupName string = privateDnsZoneGroup.name
