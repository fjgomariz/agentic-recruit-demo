# Recruitment Foundry Demo API

FastAPI backend for jobs, candidates, and candidate evaluations. Jobs are persisted in Azure Cosmos DB for NoSQL. Candidates and evaluations remain in memory and reset whenever the process restarts.

## Architecture

- `app/api`: HTTP routers and error translation.
- `app/domain`: Pydantic v2 models matching `src/shared/domain`.
- `app/services`: application-level CRUD behavior, the candidate application workflow, and the Foundry job description agent client.
- `app/storage`: Blob Storage access for uploaded resumes.
- `app/repositories`: persistence contracts, Cosmos DB Job storage, and in-memory storage with seed records for candidates and evaluations.
- `app/models`: transport models that are not domain entities.
- `app/dependencies`: FastAPI dependency providers that compose repositories and services.
- `app/main.py`: application metadata and router registration.
- `tests`: focused endpoint behavior checks.

The API depends inward from routes to services to repository contracts. FastAPI dependency providers select the Cosmos DB repository for jobs and in-memory repositories for candidates and evaluations. On startup, the API binds to the `recruitment` database and id-partitioned `jobs` container provisioned by Bicep (Entra ID data-plane roles cannot create them). The Cosmos DB connection is established in the background with retries, so `/health` responds immediately and job endpoints return `503` until storage is reachable. A new, empty jobs container stays empty: jobs are created through the recruiter portal or `POST /jobs`. The sample jobs in `tests/job_fixtures.py` are test data only.

## Start locally

Install Python 3.12, Azure CLI, and Azure Developer CLI. Provision the Azure foundation from the repository root if needed:

```powershell
azd auth login
azd env new dev
azd env set AZURE_LOCATION swedencentral
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

## Candidate applications

| Method and path | Purpose |
| --- | --- |
| `POST /jobs/{job_id}/applications` | Multipart form with `candidateName`, `candidateEmail`, optional `message`, and `resume` (PDF, 5 MB max). Uploads the resume to the `resumes` blob container as `<applicationId>.pdf`, stores the application in the Cosmos DB `applications` container, increments the job's `applicantCount`, and returns `201`. Returns `404` for an unknown job and `400` when the job is not `Published` or the file is empty, too large, or not a PDF (checked by content, not extension). |
| `GET /jobs/{job_id}/applications` | Applications for a job, newest first. |
| `GET /applications/{application_id}` | One application. |
| `GET /applications/{application_id}/resume` | The stored PDF as an attachment with the original file name. |

An application stores `id`, `jobId`, `candidateName`, `candidateEmail`, `message`, `resumeFileName`, `resumeBlobPath` (`resumes/<id>.pdf`), and `submittedAt`. If the Cosmos DB write fails, the uploaded blob is deleted.

## AI-assisted authoring

`POST /job-description-drafts` takes role facts (`title` required; `department`, `location`, `workplaceType`, `employmentType`, `experienceLevel`, `hiringManager` optional) and free-form `notes`, runs the Foundry `job-description-writer` agent, and returns `{ draft, executionId, agentName, agentVersion }`. Nothing is persisted. It returns `503` when the agent is not configured or unreachable and `502` when the agent output does not match the expected schema. See [agents/README.md](../../agents/README.md).

| Variable | Required | Default |
| --- | --- | --- |
| `AZURE_AI_PROJECT_ENDPOINT` | No; AI features return `503` without it | None |
| `JOB_DESCRIPTION_AGENT_NAME` | No | `job-description-writer` |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | No; enables Azure Monitor telemetry | None |

## Cosmos DB environment variables

| Variable | Required | Default |
| --- | --- | --- |
| `AZURE_COSMOS_ENDPOINT` | Yes | None |
| `AZURE_COSMOS_KEY` | No | `DefaultAzureCredential`; account keys may be disabled |
| `AZURE_COSMOS_DATABASE_NAME` | No | `recruitment` |
| `AZURE_COSMOS_JOBS_CONTAINER_NAME` | No | `jobs` |
| `AZURE_COSMOS_APPLICATIONS_CONTAINER_NAME` | No | `applications` |

## Blob Storage environment variables

| Variable | Required | Default |
| --- | --- | --- |
| `AZURE_STORAGE_BLOB_ENDPOINT` | No; application endpoints return `503` without it | None |
| `AZURE_STORAGE_RESUMES_CONTAINER_NAME` | No | `resumes` |

The storage account only accepts private-endpoint traffic with Entra ID, so resume upload and download work from the deployed API, not from a developer machine.