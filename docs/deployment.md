# Continuous deployment

Every pull request validates infrastructure and applications. Every push to `main` repeats those checks, provisions the existing Azure foundation with `azd`, publishes immutable container images to GitHub Container Registry, and updates the existing development Container Apps.

## Workflows

| Workflow | Purpose |
| --- | --- |
| `validate-infra.yml` | Compiles Bicep and parameter files, parses `azure.yaml`, runs Azure what-if, and rejects resource deletions. |
| `validate-apps.yml` | Lints and builds both Next.js portals, tests and packages FastAPI, and builds all three container images. |
| `deploy-dev.yml` | Uses OIDC, runs both validation workflows, provisions with `azd`, publishes commit-tagged images, and updates existing Container Apps. |

Validation jobs fail on the first command error and emit GitHub annotations for missing configuration, destructive infrastructure changes, or invalid deployment targets.

Azure what-if runs for branches in this repository and authenticated dispatches. Fork pull requests still compile Bicep but skip Azure authentication; run what-if after bringing an external contribution onto a trusted branch.

## One-time GitHub configuration

Create a GitHub environment named `dev`. Configure these environment variables, not secrets:

| Variable | Purpose |
| --- | --- |
| `AZURE_CLIENT_ID` | Application/client ID of the deployment identity. |
| `AZURE_TENANT_ID` | Microsoft Entra tenant ID. |
| `AZURE_SUBSCRIPTION_ID` | Development Azure subscription ID. |
| `AZURE_LOCATION` | Deployment region, for example `swedencentral`. |
| `PUBLIC_PORTAL_CONTAINER_APP_NAME` | Existing public portal Container App name. |
| `RECRUITER_PORTAL_CONTAINER_APP_NAME` | Existing recruiter portal Container App name. |
| `API_CONTAINER_APP_NAME` | Existing API Container App name. |

Configure a federated identity credential on the Entra application for the GitHub `dev` environment. Its subject is:

```text
repo:<owner>/<repository>:environment:dev
```

Grant the identity only the Azure control-plane permissions required to deploy the existing Bicep resources and update the three Container Apps. No Azure client secret is required.

The workflows publish to GHCR with the repository-scoped `GITHUB_TOKEN`. Make the three container packages public so Container Apps can pull them without registry credentials:

- `recruitment-foundry-public-portal`
- `recruitment-foundry-recruiter-portal`
- `recruitment-foundry-api`

## Existing-resource prerequisite

The current Bicep foundation does not define application Container Apps or a container registry. To preserve the requirement that this change introduce no Azure resources, deployment is update-only. Before enabling continuous deployment, the three named Container Apps must already exist in the provisioned `cae-recruitment-dev` environment with external ingress enabled. The portals must use target port `3000`; the API must use target port `8000`.

The API Container App must have a system-assigned managed identity. Grant it the narrowly scoped Cosmos DB for NoSQL data-plane role required to create/read the `jobs` container and manage items. The workflow verifies the identity exists but does not create identities or role assignments.

If a target app is absent, attached to another environment, lacks external ingress, or the API lacks managed identity, deployment stops before changing an app.

## Runtime configuration

The deployment workflow reads safe values from `azd` outputs. It configures:

- API: `AZURE_COSMOS_ENDPOINT`, `AZURE_COSMOS_DATABASE_NAME`, and `AZURE_COSMOS_JOBS_CONTAINER_NAME`.
- Portals: `API_BASE_URL`, set to the public HTTPS API endpoint.

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
