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

@description('Public IP ranges (CIDR) allowed to reach an external app. An empty list blocks all internet traffic instead of opening the app to everyone.')
param allowedIpRanges array = []

@description('Make sure no built-in authentication stays enabled from earlier deployments. Incremental deployments do not delete a removed authConfigs resource.')
param disableBuiltInAuth bool = false
var probeTarget = empty(healthPath)
  ? { tcpSocket: { port: targetPort } }
  : { httpGet: { path: healthPath, port: targetPort } }

// Container Apps treats an empty restriction list as open to the internet, so fail closed with a range nobody can use.
var effectiveIpRanges = empty(allowedIpRanges) ? [ '192.0.2.1/32' ] : allowedIpRanges
var ipSecurityRestrictions = [for (range, i) in effectiveIpRanges: {
  name: 'allow-'
  description: 'Allowed client range'
  ipAddressRange: range
  action: 'Allow'
}]
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
        ipSecurityRestrictions: external ? ipSecurityRestrictions : null
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

// Earlier versions signed users in with Microsoft Entra. Access is now limited by network rules, so keep the
// built-in authentication switched off.
resource auth 'Microsoft.App/containerApps/authConfigs@2025-07-01' = if (disableBuiltInAuth) {
  parent: app
  name: 'current'
  properties: {
    platform: {
      enabled: false
    }
  }
}

output name string = app.name
output fqdn string = app.properties.configuration.ingress.fqdn
output url string = 'https://${app.properties.configuration.ingress.fqdn}'
