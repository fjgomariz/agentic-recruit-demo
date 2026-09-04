# Recruitment Foundry Demo infrastructure

This folder contains the Azure Developer CLI (`azd`) and modular Bicep foundation for the Recruitment Foundry Demo. The entry point deploys at subscription scope so it can create one resource group and place all application resources inside it.

## Architecture

```text
Azure subscription
└── Resource group
    ├── Log Analytics workspace
    ├── Workspace-based Application Insights
    ├── Storage account
    │   └── Blob service (no containers yet)
    ├── Azure Cosmos DB for NoSQL account (serverless)
    │   └── recruitment database
    │       └── jobs container (created by the API at startup)
    └── Azure Container Apps environment (consumption)
```

The modules intentionally create only shared platform services. The public portal, recruiter portal, and API will be added as separate Container Apps when their deployment packaging is ready.

## Resource purposes

| Resource | Purpose |
| --- | --- |
| Resource group | Lifecycle and access-control boundary for one demo environment. |
| Log Analytics workspace | Central destination for platform logs, diagnostics, and future agent observability. |
| Application Insights | Workspace-based application telemetry for requests, dependencies, exceptions, and traces. |
| Storage account | Standard LRS blob storage for future resumes and generated artifacts. Public blob access and shared-key access are disabled. |
| Azure Cosmos DB | Serverless Azure Cosmos DB for NoSQL account with a `recruitment` database. The API creates the id-partitioned `jobs` container at startup. |
| Container Apps environment | Shared consumption environment for the two portals and FastAPI service. Environment logs flow to Log Analytics. |

## Layout

```text
infra/
├── main.bicep
├── modules/
│   ├── container-apps-environment.bicep
│   ├── cosmos.bicep
│   ├── monitoring.bicep
│   └── storage.bicep
├── parameters/
│   └── dev.bicepparam
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

## Outputs and authentication

The deployment outputs the resource names, resource IDs needed by later modules, Blob and Cosmos DB endpoints, the Container Apps default domain, and a secure Application Insights connection string. Account keys and Cosmos DB connection strings are not exposed. Future workloads should use managed identities and Azure role assignments instead of secrets.

## Future expansion

- Add one Container App module per portal and for the FastAPI service.
- Add managed identities and least-privilege Blob, Cosmos DB, and monitoring role assignments.
- Add private endpoints and network restrictions when the demo requires private networking.
- Add Blob containers with explicit retention policies when document workflows are implemented.
- Revisit the temporary `/id` jobs partition key when production access patterns are finalized.
- Add diagnostic settings, alerts, dashboards, and availability tests as workloads appear.
- Add Azure AI Foundry resources, model deployments, and agent tracing after model and regional capacity requirements are known.
- Add deployment-stage parameters for retention, redundancy, scaling, and network controls when production environments are introduced.