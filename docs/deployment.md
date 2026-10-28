# Continuous deployment

Every pull request validates infrastructure and applications. Every push to `main` publishes commit-tagged container images to GitHub Container Registry and runs a single `azd provision` that deploys the Azure foundation **and** the three Container Apps with those images. Bicep is the only source of truth for the apps: there is no imperative `az containerapp update` step and no app is created by hand. A one-time [bootstrap script](#deploy-your-own-copy) prepares the subscription and the GitHub environment.

## Deploy your own copy

This takes about 30 minutes including setup, most of it waiting for Azure. Everything is deployed from GitHub Actions into your own subscription; nothing in the repository is tied to the original author's tenant.

### What you need

| Need | Details |
| --- | --- |
| Azure subscription | Where you can create resource groups and **assign roles** (Owner, or Contributor plus User Access Administrator). A demo or lab subscription is best: see [Cost](#cost). |
| Microsoft Entra tenant | The one that hosts the subscription. You need permission to register applications (members can by default). Use a lab or demo tenant: in a Microsoft corporate tenant the app registration is flagged by the Secure Future Initiative MISE compliance check (see [Access](#access-and-sign-in)). |
| Model quota | In the region you deploy to (default `swedencentral`): GlobalStandard **gpt-5.4** 200K TPM, **gpt-5.4-mini** 50K, **gpt-5.6-sol** 10K and **text-embedding-3-large** 50K. The bootstrap script checks this. |
| Azure AI Search capacity | Basic tier in France Central by default (`searchLocation` in `infra/main.bicep`). New services can fail with `InsufficientResourcesAvailable` in busy regions; pick another region that supports agentic retrieval. |
| GitHub | Your own fork or copy of the repository, with **admin** rights, and Actions enabled (forks start with workflows disabled). |
| Tools | [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), [GitHub CLI](https://cli.github.com), [PowerShell 7](https://learn.microsoft.com/powershell/scripting/install/installing-powershell) (`pwsh`, also on macOS and Linux) and Git. The Azure Developer CLI (`azd`) is only needed for local deployments. |

### Steps

1. **Fork and clone.** `gh repo fork <owner>/agentic-recruit-demo --clone`, then open the **Actions** tab of your fork and enable workflows.
2. **Sign in** to the tenant you deploy to and to GitHub:

   ```powershell
   az login --tenant <tenant-id>
   gh auth login
   ```

3. **Prepare Azure and GitHub** with the bootstrap script. It registers resource providers, checks model quota, creates the deployment identity with its federated credentials and the least-privilege role assignments, and creates the GitHub `dev` environment with its variables. It is idempotent; add `-Check` to preview without changing anything.

   ```powershell
   ./infra/scripts/bootstrap.ps1 -TenantId <tenant-id> -SubscriptionId <subscription-id> -Location swedencentral
   ```

4. **Run the deployment** from the Actions tab (**Deploy development** → **Run workflow**) or with `gh workflow run deploy-dev.yml`. The three images are built first (about 2 minutes). **While the deploy job is still provisioning (about 14 minutes, and the apps are among the last resources it creates), make the three container packages public** (GitHub creates them as private, and Container Apps pulls them anonymously): open each package's settings, **Change visibility**, **Public**. The bootstrap script prints the links. If you miss the window, make them public and re-run the failed jobs. The whole run takes about 20 minutes.
5. **Add sign-in.** Until this step the portals have **no sign-in** and are reachable by anyone who knows the URL (the data is synthetic, but the portals call your models). Create the Entra app registration, store its client ID as the `AZURE_AUTH_CLIENT_ID` variable of the `dev` environment, and run the workflow again:

   ```powershell
   ./infra/scripts/setup-auth.ps1 -TenantId <tenant-id> -SubscriptionId <subscription-id> -EnvironmentName dev
   gh variable set AZURE_AUTH_CLIENT_ID --env dev --body <client-id>
   gh workflow run deploy-dev.yml
   ```

6. **Open the demo.** The workflow summary lists the URLs of the two portals. Sign in with the account you assigned in step 5, then follow [samples/applicants](../samples/applicants/README.md) to create jobs and apply with synthetic resumes.

When a deployment fails, see [Troubleshooting](#troubleshooting). To delete everything, see [Tear down](#tear-down).

## Workflows

| Workflow | Purpose |
| --- | --- |
| `validate-infra.yml` | Compiles Bicep and parameter files, parses `azure.yaml`, runs Azure what-if, and rejects resource deletions. |
| `validate-apps.yml` | Lints and builds both Next.js portals, tests and packages FastAPI, and builds all three container images. |
| `deploy-dev.yml` | Builds and pushes the three images in parallel (with layer cache), runs `azd provision` with the new image tags, publishes the Foundry agents, and smoke-tests the deployment, including that the portals require sign-in and the API is not reachable from the internet. |

## How a deployment works

1. **images** job (matrix of three): `docker/build-push-action` builds `src/<service>/Dockerfile` and pushes `ghcr.io/<owner>/recruitment-foundry-<service>:<sha>`. BuildKit layer cache is stored in the GitHub Actions cache, so unchanged layers are not rebuilt.
2. **deploy** job: signs in with OIDC, sets `API_IMAGE`, `PUBLIC_PORTAL_IMAGE`, `RECRUITER_PORTAL_IMAGE`, and `AZURE_PRINCIPAL_ID` (the OIDC identity's object ID) in the azd environment, and runs `azd provision`. `infra/main.parameters.json` maps these values to the Bicep parameters. A new image tag always produces a new Container Apps revision; ARM waits until that revision is healthy (or fails with the platform error).
3. `agents/deploy.py` publishes every agent in `agents/` to the Foundry project. A new agent version is created only when its model, instructions, schema, or reasoning settings change.
4. Smoke tests call each portal's unauthenticated `/api/health` (portal → internal API → Cosmos DB), check that every other portal path redirects to Microsoft Entra sign-in, and check that the API does not answer from the internet. The job summary lists the three URLs.
5. On failure, the job prints the revision list plus system and console logs of each Container App.

When the three image parameters are empty (for example a local `azd provision` without them), only the shared foundation is deployed and existing apps are left untouched.

## What Bicep deploys for the apps

| App | Port | Probes | Configuration |
| --- | --- | --- | --- |
| `ca-recruitment-api-<env>` | `8000` | HTTP `/health` | User-assigned identity `id-recruitment-api-<env>` with Cosmos DB Built-in Data Contributor, Storage Blob Data Contributor on the `resumes` container, and **Foundry User** on the Foundry project; Cosmos and Blob Storage settings, `AZURE_AI_PROJECT_ENDPOINT`, `AZURE_AI_MODEL_DEPLOYMENT_NAME`, `JOB_DESCRIPTION_AGENT_NAME`, `CANDIDATE_EVALUATION_AGENT_NAME`, `CANDIDATE_REVIEW_AGENT_NAME`, and `OTEL_SERVICE_NAME`. Agent runs are traced server-side by Foundry; the SDK's client-side GenAI instrumentor is not enabled (see [agents/README.md](../agents/README.md)). `APPLICATIONINSIGHTS_CONNECTION_STRING` is stored as a Container Apps secret. |
| `ca-recruitment-public-<env>` | `3000` | TCP | `API_BASE_URL` set to the internal API URL. Microsoft Entra sign-in required except for `/api/health`. |
| `ca-recruitment-recruiter-<env>` | `3000` | TCP | `API_BASE_URL` set to the internal API URL. Microsoft Entra sign-in required except for `/api/health`. |

The API has **internal ingress**: only apps in the same Container Apps environment can call it, and it has no route from the internet. Both portals call it from their servers, never from the browser.

The ingress target port, the probe port, and the `PORT` environment variable always come from the same Bicep value, so they cannot drift apart. Each app runs with one minimum replica so revisions activate immediately and the demo stays warm.

The Cosmos DB `jobs` container is provisioned by Bicep. Entra ID data-plane roles cannot create databases or containers, so the API only binds to existing resources. The API connects to Cosmos DB in the background: `/health` answers immediately and job endpoints return `503` until the connection (including RBAC propagation on first deployment) succeeds.

## Access and sign-in

> **Until `AZURE_AUTH_CLIENT_ID` is set, the portals have no sign-in.** The deployment prints a warning instead of failing, so the first deployment can complete before the app registration exists. Do not leave a deployment in that state.
>
> **Microsoft corporate tenants:** Container Apps built-in authentication does not report a supported MISE version, so the Entra app registration it needs is flagged by the S360 MISE compliance KPI and scheduled for deletion. Deploy in a lab or demo tenant instead.

The demo is meant to be private. Both portals use Container Apps built-in authentication with a single-tenant Microsoft Entra app registration (`Recruitment Foundry Demo (<env>)`) in the subscription's tenant:

- **User assignment is required**, so only users assigned to the app can sign in; everyone else in the tenant is refused by Microsoft Entra ID.
- There is **no client secret**: the platform signs users in with the OpenID Connect ID token flow, so nothing has to be stored or rotated.
- The recruiter portal shows the signed-in user and records recruiter decisions under their name. Local development has no sign-in and uses the demo recruiter Jordan Lee.

The app registration is created once with an account that can register applications (any member or guest of the tenant by default), after the portals exist:

```powershell
./infra/scripts/setup-auth.ps1 -EnvironmentName dev                                       # allows the signed-in user
./infra/scripts/setup-auth.ps1 -EnvironmentName dev -AllowedUsers alice@contoso.com        # allows more users
```

The script is idempotent. It sets the portals' `/.auth/login/aad/callback` redirect URIs, enables ID tokens, requires assignment, and assigns the users. It also exposes a `user_impersonation` scope that is pre-authorized for the Azure CLI (and the portals accept Azure CLI tokens), so an allowed user can call a portal from a script:

```powershell
$token = az account get-access-token --scope "api://<client-id>/user_impersonation" --query accessToken -o tsv
Invoke-WebRequest "$portalUrl/candidates" -Headers @{ Authorization = "Bearer $token" }
```

The client ID is not a secret, but it is specific to a tenant, so it is not committed: store it as the `AZURE_AUTH_CLIENT_ID` variable of the GitHub `dev` environment and deploy again (locally: `azd env set AZURE_AUTH_CLIENT_ID <id>`). Until it is set the portals have no sign-in and the deployment prints a warning. To target a specific tenant run `./infra/scripts/setup-auth.ps1 -TenantId <tenant-id> -SubscriptionId <subscription-id>`; the script stops if you are signed in to another tenant. To give someone access later, add them with `-AllowedUsers` or under **Enterprise applications → Users and groups** in the Entra admin center. To open the careers portal to anonymous candidates, remove `authClientId` from the `publicPortal` module in `infra/main.bicep`.

## GitHub environment and deployment identity

[`infra/scripts/bootstrap.ps1`](../infra/scripts/bootstrap.ps1) creates all of this for you; this section documents what it sets up, for review or for doing it by hand.

The GitHub environment `dev` has these variables (not secrets; no client secret is used anywhere):

| Variable | Purpose |
| --- | --- |
| `AZURE_CLIENT_ID` | Client ID of the deployment identity (`recruitment-deployment-mi`). |
| `AZURE_TENANT_ID` | Microsoft Entra tenant ID. |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID. |
| `AZURE_LOCATION` | Deployment region, for example `swedencentral` (defaults to that). |
| `AZURE_AUTH_CLIENT_ID` | Client ID of the Entra app registration that protects the portals, printed by `infra/scripts/setup-auth.ps1`. Set it after the first deployment. |
| `AZURE_FOUNDRY_ACCOUNT_EXISTS` | Optional. `true` deploys only the project, model deployments and connections into an existing Foundry account, for tenants whose policy blocks creating or updating the account itself (see [Troubleshooting](#troubleshooting)). |

The deployment identity is a user-assigned managed identity with a federated credential per GitHub subject. GitHub issues either a name-based subject (`repo:<owner>/<repo>:environment:dev`) or an ID-based one (`repo:<owner>@<owner-id>/<repo>@<repo-id>:environment:dev`) depending on the repository, so the script creates both.

It needs:

- **Contributor** on the subscription (the template creates the environment resource group).
- **Role Based Access Control Administrator** on the environment resource group (`rg-recruitment-<env>`), with a condition that only allows assigning or removing the seven roles the template grants:

  | Role | Granted by Bicep to |
  | --- | --- |
  | Foundry User (`53ca6127-db72-4b80-b1b0-d745d6d5456d`) | the API identity and the deployment identity, on the Foundry project |
  | Storage Blob Data Contributor (`ba92f5b4-2d11-453d-a403-e96b0029c9fe`) | the API identity (the seed job runs as it), on the resumes, talent pool and hiring policies containers |
  | Storage Blob Data Reader (`2a2b9908-6ea1-4ae2-8e65-a410df84e7d1`) | the Search service, on the knowledge source containers |
  | Cognitive Services User (`a97b65f3-24c7-4388-baec-2e87135dc908`) | the Search service, on the Foundry account (embeddings and query planning) |
  | Search Service Contributor (`7ca78c08-252a-4471-8644-bb5ff32d4ba0`) | the deployment identity, to create the knowledge sources and knowledge base |
  | Search Index Data Contributor (`8ebe5a00-799e-43f5-93ac-243d3dce84a7`) | the deployment identity |
  | Search Index Data Reader (`1407120a-92aa-4202-b7e9-c0e197c71c8f`) | the API identity (retrieval activity log) and the Foundry project identity (calls the knowledge base from the agent) |

Cosmos DB SQL role assignments are Cosmos resources and need no `Microsoft.Authorization` permission. To create the role assignment by hand, build the condition from the seven role IDs:

```powershell
$roles = '53ca6127-db72-4b80-b1b0-d745d6d5456d, ba92f5b4-2d11-453d-a403-e96b0029c9fe, 2a2b9908-6ea1-4ae2-8e65-a410df84e7d1, a97b65f3-24c7-4388-baec-2e87135dc908, 7ca78c08-252a-4471-8644-bb5ff32d4ba0, 8ebe5a00-799e-43f5-93ac-243d3dce84a7, 1407120a-92aa-4202-b7e9-c0e197c71c8f'
$condition = "((!(ActionMatches{'Microsoft.Authorization/roleAssignments/write'})) OR (@Request[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {$roles})) AND ((!(ActionMatches{'Microsoft.Authorization/roleAssignments/delete'})) OR (@Resource[Microsoft.Authorization/roleAssignments:RoleDefinitionId] ForAnyOfAnyValues:GuidEquals {$roles}))"
az role assignment create --assignee-object-id <deployment-identity-object-id> --assignee-principal-type ServicePrincipal `
  --role "Role Based Access Control Administrator" --scope /subscriptions/<id>/resourceGroups/rg-recruitment-dev `
  --condition $condition --condition-version 2.0
```

Images are published with the repository-scoped `GITHUB_TOKEN`. The three GHCR packages must be **public** so Container Apps can pull them without registry credentials:

- `recruitment-foundry-public-portal`
- `recruitment-foundry-recruiter-portal`
- `recruitment-foundry-api`

## Run a deployment locally

This needs the container images from your fork's workflow (they are published to `ghcr.io/<owner>/`). Without image tags, `azd provision` deploys only the shared foundation. Run `bootstrap.ps1` first if you also want the workflow to work.

```powershell
azd env new dev --subscription <subscription-id> --location swedencentral
azd env set API_IMAGE ghcr.io/<owner>/recruitment-foundry-api:<sha>
azd env set PUBLIC_PORTAL_IMAGE ghcr.io/<owner>/recruitment-foundry-public-portal:<sha>
azd env set RECRUITER_PORTAL_IMAGE ghcr.io/<owner>/recruitment-foundry-recruiter-portal:<sha>
azd provision
azd env get-values | Select-String _URL
```

Inspect an app:

```powershell
az containerapp revision list -g rg-recruitment-dev -n ca-recruitment-api-dev --all -o table
az containerapp logs show -g rg-recruitment-dev -n ca-recruitment-api-dev --type system --tail 50
az containerapp logs show -g rg-recruitment-dev -n ca-recruitment-api-dev --type console --tail 50
```

Local templates are committed beside each application as `.env.example` or `.env.local.example`. Keep real `.env` files untracked.

## Cost

The environment is built to run all the time, so it costs money while it exists, whether or not anyone uses it. Rough monthly list prices in USD (October 2026, no discounts); use the [Azure pricing calculator](https://azure.microsoft.com/pricing/calculator/) for your region and agreement:

| Item | Estimate |
| --- | --- |
| Azure AI Search, Basic tier (fixed, billed per hour) | about $74 (0.101 USD per hour) |
| Three Container Apps, 0.5 vCPU and 1 GiB each, one replica always on | about $12 each when idle and up to about $39 each when busy, before the monthly free grant |
| Two private endpoints, private DNS, Log Analytics and Application Insights, Storage, serverless Cosmos DB | about $15 to $30 in total with light use |
| Model usage (gpt-5.4, gpt-5.4-mini, embeddings) | pay per token: cents for a demo session, more if you run the evaluations repeatedly |

Expect roughly **$125 to $200 a month** while it is left running. If you do not need it for a while, [tear it down](#tear-down) and deploy again later: a deployment takes about 20 minutes.

## Tear down

The deployment runs in GitHub Actions, so there is no local `azd` state and `azd down` does not apply. Delete the resource group, purge the soft-deleted Foundry account (its name is deterministic, so a redeployment would otherwise collide), and remove the app registration:

```powershell
$account = az cognitiveservices account list -g rg-recruitment-dev --query "[0].name" -o tsv
az group delete -n rg-recruitment-dev --yes
az cognitiveservices account purge --location swedencentral --resource-group rg-recruitment-dev --name $account
az ad app delete --id <AZURE_AUTH_CLIENT_ID>
```

To deploy again, run `./infra/scripts/bootstrap.ps1` once more: it recreates the resource group and the role assignment that lived on it (the deployment identity is in `rg-recruitment-ci` and survives). To remove the identity too, delete `rg-recruitment-ci` and the GitHub `dev` environment.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `AADSTS700213: No matching federated identity record` when signing in to Azure | The workflow's GitHub subject does not match a federated credential (for example after renaming or transferring the repository). Run `bootstrap.ps1` again: it creates both subject formats. |
| `AuthorizationFailed` on `Microsoft.Authorization/roleAssignments/write` | The deployment identity's role condition does not list every role the template assigns. Run `bootstrap.ps1` again: it replaces a stale condition. |
| `MissingSubscriptionRegistration` or `NoRegisteredProviderFound` | A resource provider is not registered. Run `bootstrap.ps1` again; it registers them and waits. |
| Container app stuck provisioning, then failing with an image pull error (`UNAUTHORIZED`, `manifest unknown`) | The container packages are still private. Make the three packages public (see [GitHub environment](#github-environment-and-deployment-identity)) and re-run the failed jobs. |
| `InsufficientQuota` or a model deployment that stays in `Creating` | Not enough GlobalStandard quota in the region. Request quota, pick another region, or lower the `capacity` values in `agentModelDeployments` in `infra/main.bicep`. |
| `InsufficientResourcesAvailable` creating the Search service | No Basic Search capacity in the region. Set `searchLocation` in `infra/main.bicep` to another region that supports agentic retrieval and semantic ranker. |
| `RequestDisallowedByPolicy` creating or updating the Foundry account | A tenant policy blocks the account. Create the account yourself with the expected name (`aif-recruitment-<env>-<suffix>`, see the `AZURE_AI_ACCOUNT_NAME` output) and set `AZURE_FOUNDRY_ACCOUNT_EXISTS` to `true`: the template then adds only the project, model deployments and connections. |
| Storage or Cosmos reports public network access disabled when you try it from your machine | By design: both are private-endpoint only. Use the deployed apps, or a VPN into the virtual network. |
| The smoke test warns `AZURE_AUTH_CLIENT_ID is not set` | The portals have no sign-in yet. Do step 5 of [Deploy your own copy](#deploy-your-own-copy). |
| Search or knowledge base calls fail in the first minutes | Role assignments can take several minutes to apply. The workflow retries; re-run it if it still fails. |

## Branch protection

Protect `main` and require these checks before merge:

- `Compile Bicep and validate azd`
- `Detect infrastructure deletions`
- `Build Public Portal`
- `Build Recruiter Portal`
- `Test and build API`
- All three container build checks

Use GitHub environment reviewers if development deployments require approval. The deployment uses a concurrency lock so commits are deployed sequentially rather than racing.
