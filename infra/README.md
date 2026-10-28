# Recruitment Foundry Demo infrastructure

This folder contains the Azure Developer CLI (`azd`) and modular Bicep foundation for the Recruitment Foundry Demo. The entry point deploys at subscription scope so it can create one resource group and place all application resources inside it.

## Architecture

A picture of the whole system, including the agents and the deployment path, is in [docs/diagrams/architecture.svg](../docs/diagrams/architecture.svg). The infrastructure alone:

```text
Internet
└── HTTPS ingress with Microsoft Entra sign-in: public portal (3000), recruiter portal (3000)
    └── External workload-profiles Container Apps environment
        ├── Internal-only ingress: API (8000), called by the portals' servers
        └── Dedicated VNet integration subnet (/23)
            ├── Blob private endpoint → Storage account (resumes, talent pool, hiring policies)
            └── Cosmos SQL private endpoint → Cosmos DB for NoSQL

Azure AI Search (Foundry IQ, dev only) → shared private link → Storage account
Microsoft Foundry account and project → model deployments and the prompt agents
```

The VNet also contains a separate private-endpoints subnet. Private DNS zones for Blob Storage and Cosmos DB are linked to the VNet, so workloads use the normal service hostnames while data traffic resolves to private endpoint IP addresses. The three Container Apps are deployed by the same template when the `apiImage`, `publicPortalImage`, and `recruiterPortalImage` parameters are set; see [docs/deployment.md](../docs/deployment.md).

The Container Apps environment remains externally accessible and has public network access enabled, but only the two portals have external ingress and both require Microsoft Entra sign-in (see [Access and sign-in](../docs/deployment.md#access-and-sign-in)). The API has internal ingress and cannot be reached from the internet.

## Resource purposes

| Resource | Purpose |
| --- | --- |
| Resource group | Lifecycle and access-control boundary for one demo environment. |
| Log Analytics workspace | Central destination for platform logs, diagnostics, and future agent observability. |
| Application Insights | Workspace-based application telemetry for requests, dependencies, exceptions, and traces. |
| Virtual network | Contains dedicated Container Apps and private-endpoints subnets without custom routes or network appliances. |
| Storage account | Standard LRS blob storage with the private `resumes` container for candidate resumes. Public network access, public blob access, and shared-key access are disabled. |
| Azure Cosmos DB | Private-only, serverless Cosmos DB for NoSQL account with local authentication disabled, the `recruitment` database, the id-partitioned `jobs` container, the `applications` container partitioned by `/jobId`, and the `agent-executions` container partitioned by `/agentName` for agent run records. |
| Private endpoints and DNS | Blob and Cosmos SQL private endpoints plus linked Private DNS zones and Azure-managed DNS records. |
| Container Apps environment | External workload-profiles environment integrated with the dedicated subnet. Environment logs flow to Log Analytics. |
| API identity | User-assigned managed identity used by the API, granted Cosmos DB Built-in Data Contributor on the account, Storage Blob Data Contributor on the `resumes` container, and Foundry User on the Foundry project. |
| Foundry account and project | AI Services account (`aif-…`, keys disabled) with the `proj-recruitment-<env>` project that hosts the prompt agents in `agents/`. The deployment identity gets Foundry User on the project to publish agent versions. |
| Model deployments | `gpt-5.4-mini` (version `2026-03-17`, GlobalStandard, 50K TPM) for the job description writer, the candidate evaluator and the recruiter copilot, and `gpt-5.4` (version `2026-03-05`, GlobalStandard, 200K TPM) for the evaluation reviewer. Declared in `agentModelDeployments`, created one at a time, and pinned with auto-upgrade disabled. In `dev` only, `gpt-5.6-sol` (10K) for model comparisons and `text-embedding-3-large` (50K) for Foundry IQ. |
| Azure AI Search (dev only) | Basic service in `searchLocation` (France Central by default), Entra-only, with a shared private link to Storage. The knowledge sources `talent-pool-ks` and `hiring-policies-ks` and the knowledge base `recruiting-iq` are created by `agents/knowledge/setup_knowledge.py` after provisioning. |
| Seed job (dev only) | A manual Container Apps job inside the virtual network that copies the synthetic talent pool and hiring policies from the pinned commit of the public repository into the private Storage containers. The deployment workflow starts it. |
| Application Insights connection | Project connection that enables Foundry server-side agent tracing into the shared Application Insights resource. |
| Container Apps | API and both portals, each with ingress, probes, and `PORT` derived from one target-port value. The API ingress is internal; the portals use built-in Microsoft Entra authentication (`authConfigs`) when `authClientId` is set. Deployed only when image parameters are supplied. |

## Layout

```text
infra/
├── main.bicep                       # subscription-scope entry point
├── main.parameters.json             # azd parameter mapping
├── modules/
│   ├── blob-container-access.bicep      # per-container Blob roles
│   ├── container-app.bicep              # one app: ingress, probes, optional Entra authentication
│   ├── container-apps-environment.bicep
│   ├── cosmos.bicep, cosmos-data-access.bicep
│   ├── foundry.bicep, foundry-existing.bicep   # create the account, or add to an existing one
│   ├── foundry-account-role.bicep, foundry-project-role.bicep, foundry-knowledge-connection.bicep
│   ├── monitoring.bicep                 # Log Analytics and Application Insights
│   ├── network.bicep, private-endpoint.bicep, private-dns-zone.bicep
│   ├── search.bicep, search-role.bicep, storage-blob-reader.bicep   # Foundry IQ (dev only)
│   ├── seed-job.bicep                   # copies the synthetic knowledge data (dev only)
│   ├── storage.bicep
│   └── user-assigned-identity.bicep
├── parameters/
│   └── dev.bicepparam
└── scripts/
    ├── bootstrap.ps1                    # prepares the subscription and the GitHub environment
    ├── setup-auth.ps1                   # creates the Entra app registration for sign-in
    ├── approve-search-private-link.sh   # approves the Search shared private link
    ├── seed-knowledge.py                # runs inside the seed job
    └── validate-networking.sh
```

Resource API versions are pinned to stable provider versions available as of September 2026. Preview API versions are not used.

## Deploy

For a full copy of the demo (images, Foundry agents, knowledge base, sign-in), follow [Deploy your own copy](../docs/deployment.md#deploy-your-own-copy): it uses `scripts/bootstrap.ps1` and the GitHub workflow. The commands below deploy only the Azure foundation by hand.

## Deploy with Azure Developer CLI

Prerequisites:

- Azure CLI
- Azure Developer CLI
- An Azure subscription where you can create a resource group and resources

Authenticate and provision a development environment from the repository root:

```powershell
azd auth login
azd env new dev
azd env set AZURE_LOCATION swedencentral
azd provision
```

`azd` supplies `environmentName`, `location`, and the optional image parameters to the Bicep entry point through `main.parameters.json` and stores its outputs in the selected azd environment. Review the generated resource names before using a shared subscription.

## Validate or deploy with Azure CLI

The development parameter file can also be compiled or deployed directly:

```powershell
az bicep build --file infra/main.bicep
az bicep build-params --file infra/parameters/dev.bicepparam
az deployment sub what-if --location swedencentral --parameters infra/parameters/dev.bicepparam
az deployment sub create --name recruitment-foundry-dev --location swedencentral --parameters infra/parameters/dev.bicepparam
```

Use another `.bicepparam` file for each environment. Keep environment names short because they are included in resource names.

## Replacement impact

Adding an infrastructure subnet to an existing Container Apps environment is not an in-place change. An already deployed non-VNet environment must be deleted and recreated with the same name as a workload-profiles environment, which also removes its Container Apps; the next deployment recreates them. Storage and Cosmos networking changes are applied in place.

Review `az deployment sub what-if` before provisioning an environment that already exists.

## Validate private networking

After deployment, run the read-only validation script from Bash or WSL:

```bash
./infra/scripts/validate-networking.sh \
    --resource-group rg-recruitment-dev \
    --environment-name dev
```

The script checks external Container Apps environment settings, subnet integration, data-service public access, private endpoint approval, Private DNS links and zone groups, and confirms that no private endpoint targets the Container Apps environment. It uses only Azure CLI read operations.

Private DNS resolution can only be proven from inside the VNet. Run `nslookup` or an equivalent resolver check from a Container App and confirm that the normal Blob and Cosmos hostnames resolve to private IP addresses. The validation script does not create temporary compute or relax public access.

## Outputs and authentication

The deployment outputs safe names, hostnames, resource IDs, and the three app URLs (`API_URL` is the internal API address, `PUBLIC_PORTAL_URL`, `RECRUITER_PORTAL_URL`). Account keys, Cosmos DB keys, credentials, and data-service connection strings are not exposed.

The API uses the user-assigned identity `id-recruitment-api-<env>` with Cosmos DB Built-in Data Contributor at the account scope. That role allows item operations only, which is why the `jobs`, `applications`, and `agent-executions` containers are provisioned in Bicep. The identity also has Storage Blob Data Contributor scoped to the `resumes` container only.

## Future expansion

- Add least-privilege monitoring role assignments when those features appear.
- Add explicit retention policies for resumes and other generated documents.
- Revisit the temporary `/id` jobs partition key when production access patterns are finalized.
- Add diagnostic settings, alerts, dashboards, and availability tests as workloads appear.
- Add deployment-stage parameters for retention, redundancy, scaling, and network controls when production environments are introduced.