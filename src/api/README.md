# Recruitment Foundry Demo API

FastAPI backend for jobs, candidates, and candidate evaluations. Jobs are persisted in Azure Cosmos DB for NoSQL. Candidates and evaluations remain in memory and reset whenever the process restarts.

## Architecture

- `app/api`: HTTP routers and error translation.
- `app/domain`: Pydantic v2 models matching `src/shared/domain`.
- `app/services`: application-level CRUD behavior.
- `app/repositories`: persistence contracts, Cosmos DB Job storage, in-memory storage, and shared demo seed records.
- `app/models`: transport models that are not domain entities.
- `app/dependencies`: FastAPI dependency providers that compose repositories and services.
- `app/main.py`: application metadata and router registration.
- `tests`: focused endpoint behavior checks.

The API depends inward from routes to services to repository contracts. FastAPI dependency providers select the Cosmos DB repository for jobs and in-memory repositories for candidates and evaluations. On startup, the API creates the configured `recruitment` database and id-partitioned `jobs` container when they are missing. A new empty jobs container is populated with the demo seed jobs.

## Start locally

Install Python 3.12, Azure CLI, and Azure Developer CLI. Provision the Azure foundation from the repository root if needed:

```powershell
azd auth login
azd env new dev
azd env set AZURE_LOCATION eastus2
azd provision
```

For local demo development, load the Cosmos endpoint from the selected `azd` environment and grant the signed-in developer Cosmos DB data-plane access:

```powershell
$env:AZURE_COSMOS_ENDPOINT = azd env get-value AZURE_COSMOS_ENDPOINT
$env:AZURE_COSMOS_DATABASE_NAME = "recruitment"
$env:AZURE_COSMOS_JOBS_CONTAINER_NAME = "jobs"
$resourceGroup = azd env get-value AZURE_RESOURCE_GROUP
$accountName = azd env get-value AZURE_COSMOS_ACCOUNT_NAME
$principalId = az ad signed-in-user show --query id --output tsv
az cosmosdb sql role assignment create --resource-group $resourceGroup --account-name $accountName --scope / --principal-id $principalId --role-definition-id 00000000-0000-0000-0000-000000000002
```

Cosmos DB public network access is disabled. Running the API locally against Azure therefore also requires network connectivity to the application VNet, such as an existing VPN. Do not temporarily enable the public endpoint for local development.

The API uses `DefaultAzureCredential`. Locally this uses the signed-in Azure CLI identity; deployed workloads should use a managed identity with equivalent Cosmos DB data-plane permissions.

From `src/api`, create the environment and start the API:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Alternatively, create `.env` from `.env.example` and run `uvicorn app.main:app --reload --env-file .env`.

Open:

- API health: `http://127.0.0.1:8000/health`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI document: `http://127.0.0.1:8000/openapi.json`

Run tests with:

```powershell
pytest
```

## REST resources

Each resource supports collection retrieval, retrieval by ID, creation, and full replacement:

- `/jobs`
- `/candidates`
- `/evaluations`

Jobs also support `DELETE /jobs/{job_id}`, which returns `204` when deleted and `404` when the job does not exist. POST returns `409` for a duplicate ID. PUT returns `400` when route and body IDs differ and `404` when the target does not exist.

## Cosmos DB environment variables

| Variable | Required | Default |
| --- | --- | --- |
| `AZURE_COSMOS_ENDPOINT` | Yes | None |
| `AZURE_COSMOS_KEY` | No | `DefaultAzureCredential`; account keys may be disabled |
| `AZURE_COSMOS_DATABASE_NAME` | No | `recruitment` |
| `AZURE_COSMOS_JOBS_CONTAINER_NAME` | No | `jobs` |