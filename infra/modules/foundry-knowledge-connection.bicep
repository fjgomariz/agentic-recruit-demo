@description('Name of the existing Foundry (AI Services) account.')
param accountName string

@description('Name of the existing Foundry project.')
param projectName string

@description('Name of the project connection. Agents reference it as "project_connection_id" on their MCP tool.')
param connectionName string

@description('Full MCP endpoint of the knowledge base, for example https://<service>.search.windows.net/knowledgebases/<kb>/mcp?api-version=...')
param mcpEndpoint string

resource account 'Microsoft.CognitiveServices/accounts@2026-07-01' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2026-07-01' existing = {
  parent: account
  name: projectName
}

// The agent reaches the knowledge base through this connection, signed in as the project managed identity
// (which holds Search Index Data Reader). No key or secret is stored.
// The ARM service accepts ProjectManagedIdentity; the published Bicep type definition does not list it yet.
resource knowledgeBaseConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-10-01-preview' = {
  parent: project
  name: connectionName
  properties: {
    category: 'RemoteTool'
    #disable-next-line BCP036
    authType: 'ProjectManagedIdentity'
    target: mcpEndpoint
    isSharedToAll: true
    audience: 'https://search.azure.com/'
    metadata: {
      ApiType: 'Azure'
    }
  }
}

output connectionName string = knowledgeBaseConnection.name
