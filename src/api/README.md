# Recruitment Foundry Demo API

FastAPI backend for jobs, candidate applications, and AI-assisted job authoring. Jobs and applications are persisted in Azure Cosmos DB for NoSQL, and resumes in Azure Blob Storage.

## Architecture

- `app/api`: HTTP routers and error translation.
- `app/domain`: Pydantic v2 models matching `src/shared/domain`.
- `app/services`: application-level CRUD behavior, the candidate application workflow, and the Foundry job description agent client.
- `app/storage`: Blob Storage access for uploaded resumes.
- `app/repositories`: persistence contracts, Cosmos DB job and application storage, and an in-memory repository used by tests.
- `app/models`: transport models that are not domain entities.
- `app/dependencies`: FastAPI dependency providers that compose repositories and services.
- `app/main.py`: application metadata and router registration.
- `tests`: focused endpoint behavior checks.

The API depends inward from routes to services to repository contracts. FastAPI dependency providers select the Cosmos DB repositories for jobs and applications and the Blob Storage resume store. On startup, the API binds to the `recruitment` database and its `jobs` and `applications` containers provisioned by Bicep (Entra ID data-plane roles cannot create them). The Cosmos DB connection is established in the background with retries, so `/health` responds immediately and job endpoints return `503` until storage is reachable. A new, empty jobs container stays empty: jobs are created through the recruiter portal or `POST /jobs`. The sample jobs in `tests/job_fixtures.py` are test data only.

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

## Jobs

`/jobs` supports collection retrieval, retrieval by ID, creation, full replacement, and `DELETE /jobs/{job_id}`, which returns `204` when deleted and `404` when the job does not exist. POST returns `409` for a duplicate ID. PUT returns `400` when route and body IDs differ and `404` when the target does not exist.

## Candidate applications

| Method and path | Purpose |
| --- | --- |
| `POST /jobs/{job_id}/applications` | Multipart form with `candidateName`, `candidateEmail`, optional `message`, and `resume` (PDF, 5 MB max). Uploads the resume to the `resumes` blob container as `<applicationId>.pdf`, stores the application in the Cosmos DB `applications` container, and returns `201`. The applications container is the source of truth for application counts; the job's legacy `applicantCount` is not updated. Returns `404` for an unknown job and `400` when the job is not `Published` or the file is empty, too large, or not a PDF (checked by content, not extension). |
| `GET /jobs/{job_id}/applications` | Applications for a job, newest first. |
| `GET /applications` | Applications across all jobs, newest first. Used by the recruiter Candidates page and dashboard. |
| `GET /applications/{application_id}` | One application. |
| `GET /applications/{application_id}/resume` | The stored PDF as an attachment with the original file name. |

An application stores `id`, `jobId`, `candidateName`, `candidateEmail`, `message`, `resumeFileName`, `resumeBlobPath` (`resumes/<id>.pdf`), and `submittedAt`, plus the `evaluation` and `decision` described below. If the Cosmos DB write fails, the uploaded blob is deleted.

## Candidate assessment workflow and human approval

| Method and path | Purpose |
| --- | --- |
| `POST /applications/{application_id}/evaluation` | Starts or restarts the whole AI assessment (evaluator, then reviewer), clears the previous review, and returns `202` with the evaluation `In progress`. Returns `409` while an evaluation or review started less than three minutes ago is still running, and `503` when the agent is not configured. |
| `POST /applications/{application_id}/review` | Re-runs only the reviewer on the current evaluation and returns `202`. Returns `400` unless the evaluation is `Completed`. |
| `PUT /applications/{application_id}/decision` | Recruiter approval: `{ "status": "Advanced" \| "Rejected", "comment": "", "decidedBy": "", "aiRating": "Accurate" \| "Partially accurate" \| "Inaccurate" \| null, "agentFeedback": "" }`. |
| `DELETE /applications/{application_id}/decision` | Clears the decision. |
| `GET /agent-feedback` | One record per decision with the AI recommendation, scores, reviewer agreement, rating, feedback, and agent versions, newest first. No candidate personal data. |
| `GET /agent-executions?limit=50` | Recent runs of all Foundry agents, newest first, with the model reported by Foundry (AI Operations). |

Submitting an application also starts the workflow in the background:

1. **`evaluation`** (maker, `candidate-evaluator`): `status` (`In progress`, `Completed`, `Needs review`, `Failed`), `overallScore` (0–100), `recommendation`, `summary`, `strengths`, `considerations`, `scores` (one 0–5 score per requirement with its rationale), agent name, version, and model, the Foundry response ID, timestamps, and an `errorMessage` on failure. When Azure AI Content Safety blocks a resume as a prompt injection, or the model cannot read the PDF, the evaluation is stored as `Needs review` with the recommendation `Needs manual review`, the reason, and no score.
2. **`review`** (checker, `candidate-evaluation-reviewer`), only after a `Completed` evaluation: `status`, `originalScore`, `validatedScore`, `finalRecommendation`, `agreement` (`Agrees`, `Partially agrees`, `Disagrees`), `confidence`, `summary`, `comments`, `inconsistencies` (each with `type`, `severity`, `description`), the reviewed evaluation's response ID, agent name, version, and model. A failed review keeps the evaluation and can be retried.
3. **`decision`** (recruiter): the fields above plus a snapshot of the AI advice at decision time: `aiRecommendation` and `aiScore` (the reviewer's when available, otherwise the evaluator's), `followedAi` (true or false for `Strong match` and `Not a match`, null otherwise), and the evaluation and review response IDs, so every decision can be traced to the exact runs it was based on.

`evaluation`, `review`, and `decision` are written with Cosmos DB partial updates (`patch_item`), so the steps never overwrite each other and re-running the AI never changes the recruiter's decision. The steps run in the API process; if the API restarts mid-run, the recruiter can start again after three minutes.

## AI-assisted authoring

`POST /job-description-drafts` takes role facts (`title` required; `department`, `location`, `workplaceType`, `employmentType`, `experienceLevel`, `hiringManager` optional) and free-form `notes`, runs the Foundry `job-description-writer` agent, and returns `{ draft, executionId, agentName, agentVersion }`. Nothing is persisted. It returns `503` when the agent is not configured or unreachable and `502` when the agent output does not match the expected schema. See [agents/README.md](../../agents/README.md).

| Variable | Required | Default |
| --- | --- | --- |
| `AZURE_AI_PROJECT_ENDPOINT` | No; AI features return `503` without it, and new applications stay pending | None |
| `JOB_DESCRIPTION_AGENT_NAME` | No | `job-description-writer` |
| `CANDIDATE_EVALUATION_AGENT_NAME` | No | `candidate-evaluator` |
| `CANDIDATE_REVIEW_AGENT_NAME` | No | `candidate-evaluation-reviewer` |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | No; recorded on agent runs | `gpt-5.4-mini` |
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | No; enables Azure Monitor telemetry | None |

## Cosmos DB environment variables

| Variable | Required | Default |
| --- | --- | --- |
| `AZURE_COSMOS_ENDPOINT` | Yes | None |
| `AZURE_COSMOS_KEY` | No | `DefaultAzureCredential`; account keys may be disabled |
| `AZURE_COSMOS_DATABASE_NAME` | No | `recruitment` |
| `AZURE_COSMOS_JOBS_CONTAINER_NAME` | No | `jobs` |
| `AZURE_COSMOS_APPLICATIONS_CONTAINER_NAME` | No | `applications` |
| `AZURE_COSMOS_AGENT_EXECUTIONS_CONTAINER_NAME` | No | `agent-executions` |

## Blob Storage environment variables

| Variable | Required | Default |
| --- | --- | --- |
| `AZURE_STORAGE_BLOB_ENDPOINT` | No; application endpoints return `503` without it | None |
| `AZURE_STORAGE_RESUMES_CONTAINER_NAME` | No | `resumes` |

The storage account only accepts private-endpoint traffic with Entra ID, so resume upload and download work from the deployed API, not from a developer machine.