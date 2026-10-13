@description('Name of the Container Apps job.')
param name string

@description('Azure region for the job.')
param location string

@description('Common resource tags.')
param tags object

@description('Resource ID of the Container Apps managed environment. The job runs inside its virtual network.')
param environmentId string

@description('Container image that provides Python, azure-identity and azure-storage-blob (the API image).')
param image string

@description('Resource ID of the user-assigned managed identity that uploads the blobs.')
param userAssignedIdentityId string

@description('Client ID of that managed identity.')
param userAssignedIdentityClientId string

@description('Blob endpoint of the storage account that holds the knowledge source containers.')
param blobEndpoint string

@description('Public raw URL of the samples folder at a pinned commit, without a trailing slash.')
param sourceBaseUrl string

// A manual job: it runs once per deployment, uploads the synthetic talent pool and the hiring policies
// through the storage private endpoint, then exits. The storage account is never opened to the internet.
resource seedJob 'Microsoft.App/jobs@2025-07-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityId}': {}
    }
  }
  properties: {
    environmentId: environmentId
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 900
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
    }
    template: {
      containers: [
        {
          name: 'seed'
          image: image
          command: [ 'python', '-c' ]
          args: [ loadTextContent('../scripts/seed-knowledge.py') ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'SEED_SOURCE_BASE_URL', value: sourceBaseUrl }
            { name: 'AZURE_STORAGE_BLOB_ENDPOINT', value: blobEndpoint }
            { name: 'AZURE_CLIENT_ID', value: userAssignedIdentityClientId }
          ]
        }
      ]
    }
  }
}

output name string = seedJob.name
