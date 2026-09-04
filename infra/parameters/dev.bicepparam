using '../main.bicep'

param environmentName = 'dev'
param location = 'eastus2'
param virtualNetworkAddressPrefix = '10.40.0.0/16'
param containerAppsSubnetAddressPrefix = '10.40.0.0/23'
param privateEndpointsSubnetAddressPrefix = '10.40.2.0/24'
