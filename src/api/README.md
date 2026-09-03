# Recruitment Foundry Demo API

FastAPI foundation for jobs, candidates, and candidate evaluations. Data is held in memory and resets whenever the process restarts.

## Architecture

- `app/api`: HTTP routers and error translation.
- `app/domain`: Pydantic v2 models matching `src/shared/domain`.
- `app/services`: application-level CRUD behavior.
- `app/repositories`: persistence contracts, in-memory storage, and shared mock seed records.
- `app/models`: transport models that are not domain entities.
- `app/dependencies`: FastAPI dependency providers that compose repositories and services.
- `app/main.py`: application metadata and router registration.
- `tests`: focused endpoint behavior checks.

The API depends inward from routes to services to repository contracts. The in-memory repository can later be replaced without changing route behavior. This phase intentionally contains no Cosmos DB, Blob Storage, Azure authentication, or AI service integration.

## Start locally

Install Python 3.12, then run from this directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

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

POST returns `409` for a duplicate ID. PUT returns `400` when route and body IDs differ and `404` when the target does not exist.