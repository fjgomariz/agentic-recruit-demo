@description('Name of the Azure Private DNS zone.')
param privateDnsZoneName string

@description('Name of the Virtual Network link.')
param virtualNetworkLinkName string

@description('Resource ID of the Virtual Network linked to the zone.')
param virtualNetworkId string

@description('Common resource tags.')
param tags object

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: privateDnsZoneName
  location: 'global'
  tags: tags
}

resource virtualNetworkLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: privateDnsZone
  name: virtualNetworkLinkName
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: virtualNetworkId
    }
  }
}

output privateDnsZoneName string = privateDnsZone.name
output privateDnsZoneId string = privateDnsZone.id
output virtualNetworkLinkName string = virtualNetworkLink.name
