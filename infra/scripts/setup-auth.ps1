<#
.SYNOPSIS
  Creates (or updates) the Microsoft Entra app registration that protects both portals.

.DESCRIPTION
  Run once per environment with an account that can create app registrations in the tenant
  that hosts the subscription. The script is idempotent:
    - registers a single-tenant web app with the portals' /.auth/login/aad/callback redirect URIs
      and ID token issuance (Container Apps authentication signs users in without a client secret);
    - exposes a user_impersonation scope pre-authorized for the Azure CLI, so you can call the
      portals from scripts with `az account get-access-token`;
    - requires user assignment and assigns the given users, so nobody else in the tenant can sign in.
  Put the printed client ID in infra/main.parameters.json (authClientId) or the AZURE_AUTH_CLIENT_ID azd variable.

.EXAMPLE
  ./infra/scripts/setup-auth.ps1 -EnvironmentName dev
  ./infra/scripts/setup-auth.ps1 -EnvironmentName dev -AllowedUsers alice@contoso.com,bob@contoso.com
#>
param(
  [string] $EnvironmentName = 'dev',
  [string[]] $AllowedUsers = @(),
  [string] $DisplayName = ''
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$azureCli = '04b07795-8ddb-461a-bbee-02f9e1bf7b46'
$graph = 'https://graph.microsoft.com/v1.0'
if (-not $DisplayName) { $DisplayName = "Recruitment Foundry Demo ($EnvironmentName)" }

function Invoke-Graph([string] $Method, [string] $Url, $Body) {
  $file = New-TemporaryFile
  try {
    if ($null -ne $Body) { $Body | ConvertTo-Json -Depth 10 -Compress | Set-Content -Path $file -Encoding utf8 }
    $arguments = @('rest', '--method', $Method, '--url', $Url, '--headers', 'Content-Type=application/json')
    if ($null -ne $Body) { $arguments += @('--body', "@$file") }
    $output = az @arguments
    if ($output) { return $output | ConvertFrom-Json }
  } finally { Remove-Item $file -ErrorAction SilentlyContinue }
}

$resourceGroup = "rg-recruitment-$EnvironmentName"
$redirectUris = foreach ($app in "ca-recruitment-public-$EnvironmentName", "ca-recruitment-recruiter-$EnvironmentName") {
  $fqdn = az containerapp show --resource-group $resourceGroup --name $app --query properties.configuration.ingress.fqdn --output tsv
  "https://$fqdn/.auth/login/aad/callback"
}

$appId = az ad app list --display-name $DisplayName --query '[0].appId' --output tsv
if (-not $appId) {
  Write-Host "Creating app registration '$DisplayName'"
  $appId = az ad app create --display-name $DisplayName --sign-in-audience AzureADMyOrg --query appId --output tsv
}
$application = az ad app show --id $appId --query '{id:id,api:api}' --output json | ConvertFrom-Json
$scope = $application.api.oauth2PermissionScopes | Where-Object value -eq 'user_impersonation' | Select-Object -First 1
$scopeId = if ($scope) { $scope.id } else { [guid]::NewGuid().ToString() }

Write-Host 'Configuring sign-in, redirect URIs and the user_impersonation scope'
Invoke-Graph PATCH "$graph/applications/$($application.id)" @{
  identifierUris = @("api://$appId")
  web = @{ redirectUris = @($redirectUris); implicitGrantSettings = @{ enableIdTokenIssuance = $true } }
  api = @{
    requestedAccessTokenVersion = 2
    oauth2PermissionScopes = @(@{
      id = $scopeId; value = 'user_impersonation'; type = 'User'; isEnabled = $true
      adminConsentDisplayName = 'Access the Recruitment Foundry Demo'; adminConsentDescription = 'Sign in to the Recruitment Foundry Demo portals.'
      userConsentDisplayName = 'Access the Recruitment Foundry Demo'; userConsentDescription = 'Sign in to the Recruitment Foundry Demo portals.'
    })
  }
} | Out-Null
# The scope must exist before an application can be pre-authorized for it.
Invoke-Graph PATCH "$graph/applications/$($application.id)" @{
  api = @{ preAuthorizedApplications = @(@{ appId = $azureCli; delegatedPermissionIds = @($scopeId) }) }
} | Out-Null

$servicePrincipalId = az ad sp list --filter "appId eq '$appId'" --query '[0].id' --output tsv
if (-not $servicePrincipalId) { $servicePrincipalId = az ad sp create --id $appId --query id --output tsv }
Invoke-Graph PATCH "$graph/servicePrincipals/$servicePrincipalId" @{ appRoleAssignmentRequired = $true } | Out-Null

$principals = if ($AllowedUsers.Count) { $AllowedUsers | ForEach-Object { az ad user show --id $_ --query id --output tsv } } else { @(az ad signed-in-user show --query id --output tsv) }
$assigned = (Invoke-Graph GET "$graph/servicePrincipals/$servicePrincipalId/appRoleAssignedTo").value.principalId
foreach ($principalId in $principals) {
  if ($assigned -contains $principalId) { continue }
  Write-Host "Allowing user $principalId"
  Invoke-Graph POST "$graph/servicePrincipals/$servicePrincipalId/appRoleAssignedTo" @{
    principalId = $principalId; resourceId = $servicePrincipalId; appRoleId = '00000000-0000-0000-0000-000000000000'
  } | Out-Null
}

Write-Host ''
Write-Host "Client ID: $appId"
Write-Host "Redirect URIs: $($redirectUris -join ', ')"
Write-Host "Allowed users: $((Invoke-Graph GET "$graph/servicePrincipals/$servicePrincipalId/appRoleAssignedTo").value.principalDisplayName -join ', ')"
