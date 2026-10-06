@description('Globally unique storage account name.')
param storageAccountName string

@description('Azure region for the storage account.')
param location string

@description('Common resource tags.')
param tags object

@description('Name of the private container that stores uploaded resumes.')
param resumesContainerName string = 'resumes'

// General-purpose storage for resumes and generated artifacts.
resource storageAccount 'Microsoft.Storage/storageAccounts@2026-04-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  tags: tags
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    networkAcls: {
      bypass: 'None'
      defaultAction: 'Deny'
    }
    publicNetworkAccess: 'Disabled'
    supportsHttpsTrafficOnly: true
  }
}

// Explicit blob service settings enable recoverability of deleted blobs and containers.
resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2026-04-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    containerDeleteRetentionPolicy: {
      days: 7
      enabled: true
    }
    deleteRetentionPolicy: {
      days: 7
      enabled: true
    }
  }
}

// Candidate resumes uploaded through the public portal. Access is through Entra ID only.
resource resumesContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2026-04-01' = {
  parent: blobService
  name: resumesContainerName
  properties: {
    publicAccess: 'None'
  }
}

output storageAccountName string = storageAccount.name
output storageAccountId string = storageAccount.id
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob
output blobHostname string = '${storageAccount.name}.blob.${environment().suffixes.storage}'
output resumesContainerName string = resumesContainer.name
