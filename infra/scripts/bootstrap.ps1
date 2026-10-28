<#
.SYNOPSIS
  Prepares an Azure subscription and a GitHub repository so the deployment workflow can run.

.DESCRIPTION
  Run once per environment, from a clone of your fork or copy of the repository, signed in to the tenant you want
  to deploy to (az login) and to GitHub (gh auth login, with admin rights on the repository). Nothing is read from
  or written to the repository. The script is idempotent and creates only what is missing:

    1. registers the Azure resource providers the template uses;
    2. checks the model quota of the target region (a warning, never a failure);
    3. creates the resource groups, the deployment managed identity `recruitment-deployment-mi`, and its
       federated credentials for the GitHub environment (both subject formats GitHub uses);
    4. grants the identity Contributor on the subscription and a conditioned Role Based Access Control
       Administrator on the environment resource group, limited to the roles the template assigns;
    5. creates the GitHub environment and its variables (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID,
       AZURE_LOCATION).

  Use -Check to see what exists and what would change without changing anything.

  After you delete the environment resource group, run the script again: the role assignment that lived on it is
  recreated. The identity itself lives in a separate resource group so it survives.

.EXAMPLE
  ./infra/scripts/bootstrap.ps1 -TenantId <tenant-id> -SubscriptionId <subscription-id>
  ./infra/scripts/bootstrap.ps1 -Check
  ./infra/scripts/bootstrap.ps1 -Repository contoso/agentic-recruit-demo -Location swedencentral
  ./infra/scripts/bootstrap.ps1 -SkipGitHub      # only Azure; prints the GitHub variables to set by hand
#>
#Requires -Version 7.3
[CmdletBinding()]
param(
  [string] $TenantId = '',
  [string] $SubscriptionId = '',
  [string] $Repository = '',
  [string] $EnvironmentName = 'dev',
  [string] $Location = 'swedencentral',
  [string] $IdentityResourceGroup = 'rg-recruitment-ci',
  [switch] $SkipGitHub,
  [switch] $Check
)

$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true

$IdentityName = 'recruitment-deployment-mi'
$Providers = @(
  'Microsoft.App', 'Microsoft.Authorization', 'Microsoft.CognitiveServices', 'Microsoft.DocumentDB', 'Microsoft.Insights',
  'Microsoft.ManagedIdentity', 'Microsoft.Network', 'Microsoft.OperationalInsights', 'Microsoft.Search', 'Microsoft.Storage'
)
# Roles the template assigns, so the deployment identity may assign exactly these and nothing else.
# Keep in sync with the *RoleId variables in infra/ (a test checks it).
$AssignableRoles = [ordered]@{
  'a97b65f3-24c7-4388-baec-2e87135dc908' = 'Cognitive Services User'
  '1407120a-92aa-4202-b7e9-c0e197c71c8f' = 'Search Index Data Reader'
  '7ca78c08-252a-4471-8644-bb5ff32d4ba0' = 'Search Service Contributor'
  '8ebe5a00-799e-43f5-93ac-243d3dce84a7' = 'Search Index Data Contributor'
  '53ca6127-db72-4b80-b1b0-d745d6d5456d' = 'Foundry User'
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe' = 'Storage Blob Data Contributor'
  '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1' = 'Storage Blob Data Reader'
}
# Capacity in thousands of tokens per minute that infra/main.bicep requests per deployment (a test checks it).
$ModelCapacity = @(
  @{ Usage = 'OpenAI.GlobalStandard.gpt-5.4-mini'; Capacity = 50 }
  @{ Usage = 'OpenAI.GlobalStandard.gpt-5.4'; Capacity = 200 }
  @{ Usage = 'OpenAI.GlobalStandard.gpt-5.6-sol'; Capacity = 10 }
  @{ Usage = 'OpenAI.GlobalStandard.text-embedding-3-large'; Capacity = 50 }
)

function Step([string] $Message) { Write-Host "`n==> $Message" -ForegroundColor Cyan }
function Info([string] $Message) { Write-Host "    $Message" }
function Change([string] $Message) {
  if ($Check) { Write-Host "    would: $Message" -ForegroundColor Yellow } else { Write-Host "    $Message" -ForegroundColor Green }
}
function Warn([string] $Message) { Write-Host "    WARNING: $Message" -ForegroundColor Yellow }
function Invoke-Quietly([scriptblock] $Command) {
  try { & $Command 2>$null } catch { $null }
}

foreach ($tool in 'az', 'git') {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "'$tool' is required but was not found in PATH." }
}
if (-not $SkipGitHub -and -not (Get-Command gh -ErrorAction SilentlyContinue)) {
  Warn "The GitHub CLI ('gh') was not found, so the GitHub environment is skipped. Install it or set the variables by hand."
  $SkipGitHub = $true
}

# --- Azure context -----------------------------------------------------------------------------------------------
Step 'Azure context'
if ($SubscriptionId) { az account set --subscription $SubscriptionId }
$context = $null
try { $context = az account show --output json | ConvertFrom-Json } catch { throw 'Not signed in to Azure. Run: az login --tenant <tenant-id>' }
if ($TenantId -and $context.tenantId -ne $TenantId) {
  throw "Signed in to tenant $($context.tenantId), expected $TenantId. Run: az login --tenant $TenantId"
}
$TenantId = $context.tenantId
$SubscriptionId = $context.id
Info "Tenant $TenantId, subscription $($context.name) ($SubscriptionId)"
if ($Check) { Info 'Check mode: nothing will be changed.' }

$resourceGroup = "rg-recruitment-$EnvironmentName"
$subscriptionScope = "/subscriptions/$SubscriptionId"
$resourceGroupScope = "$subscriptionScope/resourceGroups/$resourceGroup"

# --- GitHub repository -------------------------------------------------------------------------------------------
$repositoryIds = $null
if (-not $SkipGitHub) {
  Step 'GitHub repository'
  if (-not $Repository) {
    $remote = Invoke-Quietly { git remote get-url origin }
    if ($remote -match 'github\.com[:/](?<owner>[^/]+)/(?<name>[^/]+?)(\.git)?$') { $Repository = "$($Matches.owner)/$($Matches.name)" }
  }
  if (-not $Repository) { throw 'Could not work out the repository. Pass -Repository <owner>/<name>.' }
  try { gh auth status 2>$null | Out-Null } catch { throw 'Not signed in to GitHub. Run: gh auth login' }
  try {
    $repositoryIds = gh api "repos/$Repository" --jq '{id: .id, ownerId: .owner.id, admin: .permissions.admin}' | ConvertFrom-Json
  } catch { throw "Cannot read repository '$Repository'. Check the name and that you are signed in to the right GitHub account." }
  if (-not $repositoryIds.admin -and -not $Check) {
    throw "You need admin rights on '$Repository' to create its environment and variables. Use -SkipGitHub to only prepare Azure."
  }
  Info "Repository $Repository (environment '$EnvironmentName')"
}

# --- Providers ---------------------------------------------------------------------------------------------------
Step 'Resource providers'
$pending = @()
foreach ($provider in $Providers) {
  $state = az provider show --namespace $provider --query registrationState --output tsv
  if ($state -eq 'Registered') { continue }
  Change "register $provider (currently $state)"
  if (-not $Check) { az provider register --namespace $provider | Out-Null }
  $pending += $provider
}
if (-not $pending) { Info 'All providers are registered.' }
elseif (-not $Check) {
  $deadline = (Get-Date).AddMinutes(8)
  while ($pending -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 10
    $pending = @($pending | Where-Object { (az provider show --namespace $_ --query registrationState --output tsv) -ne 'Registered' })
  }
  if ($pending) { Warn "Still registering: $($pending -join ', '). The deployment waits for them, but may fail if they take longer." }
  else { Info 'Providers registered.' }
}

# --- Model quota -------------------------------------------------------------------------------------------------
Step "Model quota in $Location"
$hasFoundry = $false
if ((az group exists --name $resourceGroup) -eq 'true') {
  $hasFoundry = [bool](Invoke-Quietly { az cognitiveservices account list --resource-group $resourceGroup --query '[0].name' --output tsv })
}
if ($hasFoundry) {
  Info 'The environment already has a Foundry account, so its deployments count against the quota. Skipping the check.'
} else {
  $usage = @()
  try { $usage = @(az cognitiveservices usage list --location $Location --output json | ConvertFrom-Json) } catch { }
  foreach ($model in $ModelCapacity) {
    $entry = $usage | Where-Object { $_.name.value -eq $model.Usage } | Select-Object -First 1
    if (-not $entry) { Warn "$($model.Usage): not offered in $Location (or quota unknown). Pick another region or adjust infra/main.bicep."; continue }
    $free = [double]$entry.limit - [double]$entry.currentValue
    if ($free -lt $model.Capacity) { Warn "$($model.Usage): needs $($model.Capacity)K TPM, $free left. Request more quota or lower the capacity in infra/main.bicep." }
    else { Info "$($model.Usage): needs $($model.Capacity)K TPM, $free available." }
  }
  Info "Azure AI Search capacity in the search region (France Central by default) cannot be checked in advance; if provisioning reports 'InsufficientResourcesAvailable', set 'searchLocation' in infra/main.bicep to another region."
}

# --- Resource groups and identity --------------------------------------------------------------------------------
Step 'Resource groups and deployment identity'
foreach ($group in @($resourceGroup, $IdentityResourceGroup) | Select-Object -Unique) {
  if ((az group exists --name $group) -eq 'true') { Info "Resource group $group exists." }
  else {
    Change "create resource group $group in $Location"
    if (-not $Check) { az group create --name $group --location $Location --tags "azd-env-name=$EnvironmentName" --output none }
  }
}
$identity = $null
$identityJson = Invoke-Quietly { az identity show --resource-group $IdentityResourceGroup --name $IdentityName --output json }
if ($identityJson) { $identity = $identityJson | ConvertFrom-Json; Info "Identity $IdentityName exists (client ID $($identity.clientId))." }
else {
  Change "create managed identity $IdentityName in $IdentityResourceGroup"
  if (-not $Check) { $identity = az identity create --resource-group $IdentityResourceGroup --name $IdentityName --location $Location --output json | ConvertFrom-Json }
}

# --- Federated credentials ---------------------------------------------------------------------------------------
if ($identity -and -not $SkipGitHub) {
  Step 'Federated credentials for GitHub Actions'
  # GitHub issues either a name-based or an ID-based subject depending on the repository, so allow both.
  $owner, $name = $Repository.Split('/')
  $subjects = [ordered]@{
    "github-$EnvironmentName"      = "repo:${Repository}:environment:$EnvironmentName"
    "github-$EnvironmentName-ids"  = "repo:$owner@$($repositoryIds.ownerId)/$name@$($repositoryIds.id):environment:$EnvironmentName"
  }
  $existing = @(az identity federated-credential list --resource-group $IdentityResourceGroup --identity-name $IdentityName --output json | ConvertFrom-Json)
  foreach ($credentialName in $subjects.Keys) {
    $subject = $subjects[$credentialName]
    if ($existing | Where-Object { $_.subject -eq $subject }) { Info "Credential for $subject exists."; continue }
    Change "create federated credential for $subject"
    if (-not $Check) {
      az identity federated-credential create --resource-group $IdentityResourceGroup --identity-name $IdentityName --name $credentialName `
        --issuer 'https://token.actions.githubusercontent.com' --subject $subject --audiences 'api://AzureADTokenExchange' --output none
    }
  }
}

# --- Role assignments --------------------------------------------------------------------------------------------
if ($identity) {
  Step 'Role assignments for the deployment identity'
  $principalId = $identity.principalId
  $assignments = @(az role assignment list --assignee $principalId --all --output json | ConvertFrom-Json)

  if ($assignments | Where-Object { $_.roleDefinitionName -eq 'Contributor' -and $_.scope -ieq $subscriptionScope }) { Info 'Contributor on the subscription exists.' }
  else {
    Change 'grant Contributor on the subscription (the template creates the environment resource group and its resources)'
    if (-not $Check) { az role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal --role Contributor --scope $subscriptionScope --output none }
  }

  $ids = $AssignableRoles.Keys -join ', '
  $condition = "((!(ActionMatches{'Microsoft.Authorization/roleAssignments/write'})) OR (@Request[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {$ids})) AND ((!(ActionMatches{'Microsoft.Authorization/roleAssignments/delete'})) OR (@Resource[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {$ids}))"
  $admin = $assignments | Where-Object { $_.roleDefinitionName -eq 'Role Based Access Control Administrator' -and $_.scope -ieq $resourceGroupScope } | Select-Object -First 1
  $upToDate = $admin -and -not ($AssignableRoles.Keys | Where-Object { $admin.condition -notmatch $_ })
  if ($upToDate) { Info "Role Based Access Control Administrator on $resourceGroup exists and allows all $($AssignableRoles.Count) roles." }
  else {
    if ($admin) {
      Change "replace the Role Based Access Control Administrator assignment on ${resourceGroup} (its condition misses roles the template assigns)"
      if (-not $Check) { az role assignment delete --ids $admin.id }
    }
    Change "grant Role Based Access Control Administrator on ${resourceGroup}, limited to: $($AssignableRoles.Values -join ', ')"
    if (-not $Check) {
      az role assignment create --assignee-object-id $principalId --assignee-principal-type ServicePrincipal --role 'Role Based Access Control Administrator' `
        --scope $resourceGroupScope --condition $condition --condition-version 2.0 --output none
    }
  }
}

# --- GitHub environment ------------------------------------------------------------------------------------------
$variables = [ordered]@{
  AZURE_CLIENT_ID       = if ($identity) { $identity.clientId } else { '<client-id-of-the-deployment-identity>' }
  AZURE_TENANT_ID       = $TenantId
  AZURE_SUBSCRIPTION_ID = $SubscriptionId
  AZURE_LOCATION        = $Location
}
if ($SkipGitHub) {
  Step 'GitHub environment (skipped)'
  Info "Create an environment named '$EnvironmentName' and add these variables (not secrets):"
  $variables.GetEnumerator() | ForEach-Object { Info "  $($_.Key) = $($_.Value)" }
} else {
  Step "GitHub environment '$EnvironmentName'"
  if (-not $Check) { gh api --method PUT "repos/$Repository/environments/$EnvironmentName" --silent }
  $current = @{}
  try { gh variable list --repo $Repository --env $EnvironmentName --json name,value 2>$null | ConvertFrom-Json | ForEach-Object { $current[$_.name] = $_.value } } catch { }
  foreach ($key in $variables.Keys) {
    if ($current[$key] -eq $variables[$key]) { Info "$key is set."; continue }
    Change "set $key = $($variables[$key])"
    if (-not $Check -and $identity) { gh variable set $key --repo $Repository --env $EnvironmentName --body $variables[$key] }
  }
}

# --- Next steps --------------------------------------------------------------------------------------------------
Step 'Next steps'
if ($Check) { Info 'This was a check. Run the script again without -Check to apply the changes above.' }
$packageRoot = 'https://github.com/users/<owner>/packages/container'
$ownerLogin = '<owner>'
if ($Repository) {
  $ownerLogin = $Repository.Split('/')[0]
  $ownerType = Invoke-Quietly { gh api "users/$ownerLogin" --jq '.type' }
  $packageRoot = if ($ownerType -eq 'Organization') { "https://github.com/orgs/$ownerLogin/packages/container" } else { "https://github.com/users/$ownerLogin/packages/container" }
}
Info "1. Run the 'Deploy development' workflow (Actions tab, or: gh workflow run deploy-dev.yml --repo $Repository)."
Info "   GitHub creates the container packages as private, but Container Apps pulls them anonymously. As soon as the three 'Publish ... image'"
Info "   jobs finish (1 to 3 minutes) make each package public, while the deploy job is still provisioning (about 14 minutes; the apps come last):"
foreach ($package in 'recruitment-foundry-api', 'recruitment-foundry-public-portal', 'recruitment-foundry-recruiter-portal') {
  Info "     $packageRoot/$($package.ToLowerInvariant())/settings  ->  Change visibility  ->  Public"
}
Info "   If you miss the window, make them public and re-run the failed jobs."
Info "2. When the deployment passes, add Microsoft Entra sign-in (until then the portals have NO sign-in):"
Info "     ./infra/scripts/setup-auth.ps1 -TenantId $TenantId -SubscriptionId $SubscriptionId -EnvironmentName $EnvironmentName"
Info "   Store the client ID it prints as the AZURE_AUTH_CLIENT_ID variable of the '$EnvironmentName' environment and run the workflow again."
Info "3. The workflow summary lists the portal URLs. To delete everything later, see 'Tear down' in docs/deployment.md."
