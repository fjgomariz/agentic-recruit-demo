# Recruitment Foundry Demo infrastructure

This folder contains the Azure Developer CLI (`azd`) and modular Bicep foundation for the Recruitment Foundry Demo. The entry point deploys at subscription scope so it can create one resource group and place all application resources inside it.

## Architecture

```text
Internet
└── Future public Container Apps ingress
    └── External workload-profiles Container Apps environment
        └── Dedicated VNet integration subnet (/23)
            ├── Blob private endpoint → Storage account
            └── Cosmos SQL private endpoint → Cosmos DB for NoSQL
```

The VNet also contains a separate private-endpoints subnet. Private DNS zones for Blob Storage and Cosmos DB are linked to the VNet, so future workloads use the normal service hostnames while data traffic resolves to private endpoint IP addresses. The modules intentionally create only shared platform services; the public portal, recruiter portal, and API are not deployed yet.

The Container Apps environment remains externally accessible and has public network access enabled. Future apps can expose public HTTPS ingress. The environment itself has no private endpoint and is not internal-only.

## Resource purposes

| Resource | Purpose |
| --- | --- |
| Resource group | Lifecycle and access-control boundary for one demo environment. |
| Log Analytics workspace | Central destination for platform logs, diagnostics, and future agent observability. |
| Application Insights | Workspace-based application telemetry for requests, dependencies, exceptions, and traces. |
| Virtual network | Contains dedicated Container Apps and private-endpoints subnets without custom routes or network appliances. |
| Storage account | Standard LRS blob storage for future resumes and generated artifacts. Public network access, public blob access, and shared-key access are disabled. |
| Azure Cosmos DB | Private-only, serverless Cosmos DB for NoSQL account with local authentication disabled and the existing `recruitment` database preserved. The API creates the id-partitioned `jobs` container at startup. |
| Private endpoints and DNS | Blob and Cosmos SQL private endpoints plus linked Private DNS zones and Azure-managed DNS records. |
| Container Apps environment | External workload-profiles environment integrated with the dedicated subnet. Environment logs flow to Log Analytics. |

## Layout

```text
infra/
├── main.bicep
├── modules/
│   ├── container-apps-environment.bicep
│   ├── cosmos.bicep
│   ├── monitoring.bicep
│   ├── network.bicep
│   ├── private-dns-zone.bicep
│   ├── private-endpoint.bicep
│   └── storage.bicep
├── parameters/
│   └── dev.bicepparam
├── scripts/
│   └── validate-networking.sh
└── README.md
```

Resource API versions are pinned to stable provider versions available as of September 2026. Preview API versions are not used.

## Deploy with Azure Developer CLI

Prerequisites:

- Azure CLI
- Azure Developer CLI
- An Azure subscription where you can create a resource group and resources

Authenticate and provision a development environment from the repository root:

```powershell
azd auth login
azd env new dev
azd env set AZURE_LOCATION eastus2
azd provision
```

`azd` supplies `environmentName` and `location` to the Bicep entry point and stores its outputs in the selected azd environment. Review the generated resource names before using a shared subscription.

## Validate or deploy with Azure CLI

The development parameter file can also be compiled or deployed directly:

```powershell
az bicep build --file infra/main.bicep
az bicep build-params --file infra/parameters/dev.bicepparam
az deployment sub what-if --location eastus2 --parameters infra/parameters/dev.bicepparam
az deployment sub create --name recruitment-foundry-dev --location eastus2 --parameters infra/parameters/dev.bicepparam
```

Use another `.bicepparam` file for each environment. Keep environment names short because they are included in resource names.

## Replacement impact

Adding an infrastructure subnet to an existing Container Apps environment is not an in-place change. An already deployed non-VNet environment must be deleted and recreated with the same name as a workload-profiles environment. No Container Apps are currently deployed by this template, so the replacement does not remove application workloads. Storage and Cosmos networking changes are applied in place; the VNet, Private DNS zones, links, and private endpoints are new resources.

Review `az deployment sub what-if` before provisioning an environment that already exists.

## Validate private networking

After deployment, run the read-only validation script from Bash or WSL:

```bash
./infra/scripts/validate-networking.sh \
    --resource-group rg-recruitment-dev \
    --environment-name dev
```

The script checks external Container Apps environment settings, subnet integration, data-service public access, private endpoint approval, Private DNS links and zone groups, and confirms that no private endpoint targets the Container Apps environment. It uses only Azure CLI read operations.

Private DNS resolution can only be proven from inside the VNet. Run `nslookup` or an equivalent resolver check from a future Container App and confirm that the normal Blob and Cosmos hostnames resolve to private IP addresses. The validation script does not create temporary compute or relax public access.

## Outputs and authentication

The deployment outputs safe names, hostnames, and resource IDs needed by later modules, including the VNet, both subnets, private endpoints, Private DNS zones, data services, and Container Apps environment. Account keys, Cosmos DB keys, credentials, and data-service connection strings are not exposed.

Future Container Apps should use managed identities. The API identity will need narrowly scoped Cosmos DB data-plane permissions appropriate for its runtime container initialization and item operations. Workloads using Blob Storage will need the relevant Blob data role. Those identities and role assignments are intentionally deferred until the applications are deployed; no broad RBAC grants are created here.

## Future expansion

- Add one Container App module per portal and for the FastAPI service.
- Add managed identities and least-privilege Blob, Cosmos DB, and monitoring role assignments.
- Add Blob containers with explicit retention policies when document workflows are implemented.
- Revisit the temporary `/id` jobs partition key when production access patterns are finalized.
- Add diagnostic settings, alerts, dashboards, and availability tests as workloads appear.
- Add Azure AI Foundry resources, model deployments, and agent tracing after model and regional capacity requirements are known.
- Add deployment-stage parameters for retention, redundancy, scaling, and network controls when production environments are introduced.