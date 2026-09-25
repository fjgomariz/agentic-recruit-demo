# Continuous deployment

Every pull request validates infrastructure and applications. Every push to `main` publishes commit-tagged container images to GitHub Container Registry and runs a single `azd provision` that deploys the Azure foundation **and** the three Container Apps with those images. Bicep is the only source of truth for the apps: there is no imperative `az containerapp update` step and nothing has to be created by hand.

## Workflows

| Workflow | Purpose |
| --- | --- |
| `validate-infra.yml` | Compiles Bicep and parameter files, parses `azure.yaml`, runs Azure what-if, and rejects resource deletions. |
| `validate-apps.yml` | Lints and builds both Next.js portals, tests and packages FastAPI, and builds all three container images. |
| `deploy-dev.yml` | Builds and pushes the three images in parallel (with layer cache), then runs `azd provision` with the new image tags and smoke-tests the endpoints. |

## How a deployment works

1. **images** job (matrix of three): `docker/build-push-action` builds `src/<service>/Dockerfile` and pushes `ghcr.io/<owner>/recruitment-foundry-<service>:<sha>`. BuildKit layer cache is stored in the GitHub Actions cache, so unchanged layers are not rebuilt.
2. **deploy** job: signs in with OIDC, sets `API_IMAGE`, `PUBLIC_PORTAL_IMAGE`, and `RECRUITER_PORTAL_IMAGE` in the azd environment, and runs `azd provision`. `infra/main.parameters.json` maps these values to the Bicep parameters. A new image tag always produces a new Container Apps revision; ARM waits until that revision is healthy (or fails with the platform error).
3. Smoke tests call `API /health`, `API /jobs`, and both portal home pages. The job summary lists the three URLs.
4. On failure, the job prints the revision list plus system and console logs of each Container App.

When the three image parameters are empty (for example a local `azd provision` without them), only the shared foundation is deployed and existing apps are left untouched.

## What Bicep deploys for the apps

| App | Port | Probes | Configuration |
| --- | --- | --- | --- |
| `ca-recruitment-api-<env>` | `8000` | HTTP `/health` | User-assigned identity `id-recruitment-api-<env>` with Cosmos DB Built-in Data Contributor; `AZURE_CLIENT_ID`, `AZURE_COSMOS_ENDPOINT`, `AZURE_COSMOS_DATABASE_NAME`, `AZURE_COSMOS_JOBS_CONTAINER_NAME`. |
| `ca-recruitment-public-<env>` | `3000` | TCP | `API_BASE_URL` set to the API HTTPS URL. |
| `ca-recruitment-recruiter-<env>` | `3000` | TCP | `API_BASE_URL` set to the API HTTPS URL. |

The ingress target port, the probe port, and the `PORT` environment variable always come from the same Bicep value, so they cannot drift apart. Each app runs with one minimum replica so revisions activate immediately and the demo stays warm.

The Cosmos DB `jobs` container is provisioned by Bicep. Entra ID data-plane roles cannot create databases or containers, so the API only binds to existing resources. The API connects to Cosmos DB in the background: `/health` answers immediately and job endpoints return `503` until the connection (including RBAC propagation on first deployment) succeeds.

## One-time GitHub configuration

Create a GitHub environment named `dev` with these environment variables (not secrets):

| Variable | Purpose |
| --- | --- |
| `AZURE_CLIENT_ID` | Client ID of the deployment identity. |
| `AZURE_TENANT_ID` | Microsoft Entra tenant ID. |
| `AZURE_SUBSCRIPTION_ID` | Development Azure subscription ID. |
| `AZURE_LOCATION` | Deployment region, for example `swedencentral`. |

Configure a federated identity credential on the deployment identity for the GitHub `dev` environment:

```text
repo:<owner>/<repository>:environment:dev
```

The deployment identity needs **Contributor** on the subscription (the template creates the resource group). Cosmos DB SQL role assignments are Cosmos resources, so no `Microsoft.Authorization` permissions are required. No client secret is used.

Images are published with the repository-scoped `GITHUB_TOKEN`. Keep the three GHCR packages public so Container Apps can pull them without registry credentials:

- `recruitment-foundry-public-portal`
- `recruitment-foundry-recruiter-portal`
- `recruitment-foundry-api`

## Run a deployment locally

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

## Branch protection

Protect `main` and require these checks before merge:

- `Compile Bicep and validate azd`
- `Detect infrastructure deletions`
- `Build Public Portal`
- `Build Recruiter Portal`
- `Test and build API`
- All three container build checks

Use GitHub environment reviewers if development deployments require approval. The deployment uses a concurrency lock so commits are deployed sequentially rather than racing.
