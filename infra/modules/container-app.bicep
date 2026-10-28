@description('Name of the Container App.')
param name string

@description('Azure region for the Container App.')
param location string

@description('Common resource tags.')
param tags object

@description('Resource ID of the Container Apps managed environment.')
param environmentId string

@description('Fully qualified container image reference.')
param image string

@description('Port the container listens on. Ingress, probes, and the PORT variable all use it.')
param targetPort int

@description('Additional environment variables as name/value pairs.')
param env array = []

@description('Sensitive environment variables, as a map of variable name to value, stored as Container Apps secrets.')
@secure()
param secretEnv object = {}

var secretItems = items(secretEnv)
var secrets = [for item in secretItems: { name: toLower(replace(item.key, '_', '-')), value: item.value }]
var secretEnvVars = [for item in secretItems: { name: item.key, secretRef: toLower(replace(item.key, '_', '-')) }]

@description('HTTP path used for readiness and liveness probes. Empty uses TCP probes.')
param healthPath string = ''

@description('Optional user-assigned managed identity resource ID.')
param userAssignedIdentityId string = ''

@description('Minimum replica count. One keeps the demo warm and makes deployments report health quickly.')
param minReplicas int = 1

@description('Maximum replica count.')
param maxReplicas int = 3

@description('Expose the app to the internet. False keeps it reachable only from apps in the same Container Apps environment.')
param external bool = true

@description('Client ID of the Microsoft Entra app registration that users must sign in with. Empty leaves the app without authentication.')
param authClientId string = ''

@description('Paths that skip authentication, such as a health check that returns no data.')
param authExcludedPaths array = []

var probeTarget = empty(healthPath)
  ? { tcpSocket: { port: targetPort } }
  : { httpGet: { path: healthPath, port: targetPort } }

var azureCliClientId = '04b07795-8ddb-461a-bbee-02f9e1bf7b46'

resource app 'Microsoft.App/containerApps@2025-07-01' = {
  name: name
  location: location
  tags: tags
  identity: empty(userAssignedIdentityId)
    ? { type: 'None' }
    : {
        type: 'UserAssigned'
        userAssignedIdentities: {
          '${userAssignedIdentityId}': {}
        }
      }
  properties: {
    environmentId: environmentId
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: secrets
      ingress: {
        external: external
        targetPort: targetPort
        transport: 'auto'
        allowInsecure: false
      }
    }
    template: {
      containers: [
        {
          name: name
          image: image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat([{ name: 'PORT', value: string(targetPort) }], env, secretEnvVars)
          probes: [
            union(probeTarget, {
              type: 'Startup'
              initialDelaySeconds: 2
              periodSeconds: 5
              failureThreshold: 10
              timeoutSeconds: 3
            })
            union(probeTarget, {
              type: 'Readiness'
              periodSeconds: 5
              failureThreshold: 3
              timeoutSeconds: 3
            })
            union(probeTarget, {
              type: 'Liveness'
              periodSeconds: 15
              failureThreshold: 3
              timeoutSeconds: 3
            })
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

// Built-in authentication: every request must carry a Microsoft Entra session for an assigned user.
// Without a client secret the platform uses the OpenID Connect ID token flow, so there is no secret to rotate.
resource auth 'Microsoft.App/containerApps/authConfigs@2025-07-01' = if (!empty(authClientId)) {
  parent: app
  name: 'current'
  properties: {
    platform: {
      enabled: true
    }
    globalValidation: {
      unauthenticatedClientAction: 'RedirectToLoginPage'
      redirectToProvider: 'azureactivedirectory'
      excludedPaths: authExcludedPaths
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          clientId: authClientId
          openIdIssuer: '${environment().authentication.loginEndpoint}${tenant().tenantId}/v2.0'
        }
        validation: {
          defaultAuthorizationPolicy: {
            // Interactive sign-ins, plus Azure CLI tokens for scripted access by the same assigned users.
            allowedApplications: [ authClientId, azureCliClientId ]
          }
        }
      }
    }
  }
}

output name string = app.name
output fqdn string = app.properties.configuration.ingress.fqdn
output url string = 'https://${app.properties.configuration.ingress.fqdn}'
